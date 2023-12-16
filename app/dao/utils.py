from copy import deepcopy
from random import random

from sqlalchemy import bindparam, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DataError, SQLAlchemyError
from sqlalchemy.orm.exc import ObjectDeletedError, StaleDataError

from app import logger
from app.models import Session
from app.settings import sentry_sdk


def safe_bulk_insert_mappings(mapper, mappings):
    """Make a bulk update and if it fails, perform all updates in the mappings one by one

    Typical error is the following:
    - Key does not exist anymore ('expected to update 6 row(s); 1 were matched')

    Parameters:
    ===========
    mapper: a SQLAlchemy class object
    mappings: a list of dictionaries, each one containing the state of the mapped row to be updated
    """
    with Session() as session:
        try:
            stmt = insert(mapper).values(mappings)
            orm_stmt = stmt.on_conflict_do_nothing()  # this is for case of update

            # execute statement
            session.execute(orm_stmt)
            session.commit()

        except Exception as ex:
            logger.warn(
                f"Bulk inserting rows V2 in the table {mapper.__tablename__} failed, fallback to one by one, Exception {str(ex)}"
            )
            session.rollback()

            for mapping in mappings:
                try:
                    session.execute(insert(mapper).values(**mapping))
                    session.commit()
                except SQLAlchemyError as e:
                    logger.warn(f"Error inserting item {mapping} in the table {mapper.__tablename__}:\n{e}\n\n")
                    session.rollback()
                    with sentry_sdk.push_scope() as scope:
                        scope.set_extra("mappings", mappings)
                        sentry_sdk.capture_exception()


def safe_bulk_update_mappings(mapper, mappings, mapper_pk="id", enable_sentry_logging=True):
    """Make a bulk update and if it fails, perform all updates in the mappings one by one

    Typical error is the following:
    - Key does not exist anymore ('expected to update 6 row(s); 1 were matched')

    Parameters:
    ===========
    mapper: The SQLAlchemy class of the object we want to update
    mappings: a list of dictionaries, each one containing the state of the mapped row to be updated
    mapper_pk: the name of the primary key of the mapper, default is "id"
    """
    # work on a copy of mappings to not modify the given object
    mappings_copy = deepcopy(mappings)

    mapping_without_pk = deepcopy(mappings_copy[0])
    mapping_without_pk.pop(mapper_pk, None)

    # Rename the mapper primary key in mappings to _id as 'id' is reserved by sqlalchemy
    for mapping in mappings_copy:
        mapping["_id"] = mapping.pop(mapper_pk)

    # https://docs.sqlalchemy.org/en/14/tutorial/data_update.html#updating-and-deleting-rows-with-core
    update_statement = (
        update(mapper)
        .filter(getattr(mapper, mapper_pk) == bindparam("_id"))
        .values({key: bindparam(key) for key in mapping_without_pk.keys()})
    )

    with Session() as session:
        try:
            session.execute(update_statement, mappings_copy)
            session.commit()
        except StaleDataError:
            logger.warn(f"Bulk updating rows in the table {mapper.__tablename__} failed, fallback to one by one")

            # we send this warning to sentry only 1 time every 1OOO to avoid having to much messages on sentry.
            if random() > 0.999:
                logger.warn(f"Bulk updating rows in the table {mapper.__tablename__} failed, fallback to one by one")

            session.rollback()

            if enable_sentry_logging:
                with sentry_sdk.push_scope() as scope:
                    scope.set_extra("mappings", mappings_copy)
                    sentry_sdk.capture_exception()

            for mapping in mappings_copy:
                try:
                    session.query(mapper).filter(getattr(mapper, mapper_pk) == mapping["_id"]).update(mapping)
                    session.commit()
                except (DataError, ObjectDeletedError) as e:
                    logger.warn(f"Error updating item {mapping} in the table {mapper.__tablename__}:\n{e}\n\n")
                    session.rollback()
                    if enable_sentry_logging:
                        with sentry_sdk.push_scope() as scope:
                            scope.set_extra("mappings", mappings_copy)
                            sentry_sdk.capture_exception()
