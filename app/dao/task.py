from datetime import datetime, timezone
from typing import List
import re

from sqlalchemy import or_, func, nullsfirst
from sqlalchemy.orm import joinedload
from rich.progress import track

from app import logger
from app.models import Session, Task, Organisation, Website
from app.models.enums import ScrapingType
from app.dao.organisation import OrganisationDAO

organisation_DAO = OrganisationDAO()


class TaskDAO:
    def get(self, id):
        with Session() as session:
            return session.query(Task).filter(Task.id == id).first()

    def get_all(self, organisation_name):
        with Session() as session:
            organisation = session.query(Organisation).filter_by(name=organisation_name).first()
            return session.query(Task).filter(Task.organisation_id == organisation.id).all()

    def update(self, id, body):
        with Session() as session:
            (session.query(Task).filter(Task.id == id).update(body, synchronize_session=False))
            session.commit()

    def filter_active_tasks(self, query):
        query = (
            query.outerjoin(Organisation, Organisation.id == Task.organisation_id)
            .join(Website, Website.id == Task.website_id)
            .filter(
                Task.scraping_interval.isnot(None),
                Task.scraping_interval > 0,
                or_(Organisation.active.is_(None), Organisation.active.is_(True)),
                Website.is_active.is_(True),
                Task.is_active.is_(True),
            )
        )
        return query

    def get_tasks_to_run(self, ignore_interval: bool = False) -> List[Task]:
        now = datetime.now(timezone.utc)

        with Session() as session:
            query = self.filter_active_tasks(session.query(Task))
            # use ignore_interval to test the throttling
            if not ignore_interval:
                # Deterministic noise to avoid daily cadence and load peaks. It should remain the same between adjacent runs of the scheduler,
                # otherwise the more times you run the scheduler the higher chances a task has to pass the randomized filter.
                # Therefore it's based on last_run_time seconds: re-randomized after each successful run, stable between unsuccessful runs.
                # Up to 5% of random increase to Task.scraping_interval.
                noise_factor = (100.0 + (func.extract("microseconds", Task.last_run_time) % 6)) / 100.0

                query = query.filter(
                    or_(
                        Task.last_run_time.is_(None),
                        (func.extract("epoch", now - Task.last_run_time) > (Task.scraping_interval * noise_factor)),
                    )
                )

            query = query.order_by(
                nullsfirst(Task.last_run_time)
            )  # when throttled, prioritize tasks with older last run

            # print(query.statement.compile(compile_kwargs={"literal_binds": True}))
            return query.all()

    def avg_task_count_per_interval(self, scheduling_interval: int):
        # how many task we would launch each {scheduling_interval} seconds if they were evenly distrubuted
        with Session() as session:
            query = self.filter_active_tasks(
                session.query(func.sum(float(scheduling_interval) / Task.scraping_interval))
            )
            result = query.one()[0]

        return result

    def add(
        self,
        organisation_name: str,
        website_names: List,
        search_queries: List,
        scraping_interval: int,
        max_posts_to_browse: int = None,
        max_posts_to_discover: int = None,
        use_localized_queries: bool = False,
        config_file: str = None,
        search_image_urls: List = None,
        scraping_type: ScrapingType = None,
    ):
        with Session() as session:
            website_list = session.query(Website).filter(Website.name.in_(website_names)).all()
            logger.info(f"{len(website_list)} found out of {len(website_names)}")

            logger.info(f"{len(website_list)} found")
            for website in website_list:
                logger.info(f"{website.name=}, {website.id=}")

            organisation = session.query(Organisation).filter_by(name=organisation_name).first()
            logger.info(f"We are working with organisation {organisation.name}")

            for website in website_list:
                task = (
                    session.query(Task)
                    .filter(Task.website_id == website.id)
                    .filter(Task.organisation_id == organisation.id)
                )
                if scraping_type:
                    task = task.filter(Task.scraping_type == scraping_type)

                task = task.first()
                if task is None:
                    ## if domain has specific country
                    if use_localized_queries or search_queries == []:
                        localized_queries = organisation_DAO.get_organisation_localized_keywords(
                            organisation_id=organisation.id,
                            country_code=website.country_code,
                            include_main_queries=True,
                        )

                        if localized_queries:
                            search_queries.extend(localized_queries)

                    # TODO: handle config file at website level
                    if website.domain_name == "facebook.com/marketplace":
                        _config = "facebook-marketplace.com"
                    elif website.domain_name == "instagram.com":
                        _config = "instagram_hashtag_search"
                    else:
                        _config = config_file

                    task = Task(
                        organisation_id=organisation.id,
                        website_id=website.id,
                        search_queries=None if search_queries is None else list(set(search_queries)),
                        scraping_interval=scraping_interval,
                        send_posts_to_counterfeit_platform=True,
                        max_posts_to_browse=max_posts_to_browse,
                        max_posts_to_discover=max_posts_to_discover,
                        config_file=_config,
                        search_image_urls=search_image_urls,
                        scraping_type=scraping_type,
                    )
                    session.add(task)
                    logger.info(f"task created {website.name}")
                else:
                    if task.is_active is False:
                        logger.info(
                            f"task exists for domain {website.name} but is not active , reactivating and updating values"
                        )
                        task.is_active = True
                        task.scraping_interval = scraping_interval
                        task.send_posts_to_counterfeit_platform = True
                        task.max_posts_to_browse = max_posts_to_browse
                        task.max_posts_to_discover = max_posts_to_discover
                        task.config_file = (config_file,)
                    else:
                        logger.info(f"task exists for domain {website.name}")

            session.commit()

    def check_search_queries(
        self,
        task_ids: List,
        organisation_name: str,
    ):
        with Session() as session:
            organisation: Organisation = session.query(Organisation).filter_by(name=organisation_name).first()
            logger.info(f"We are working with organisation {organisation.name}")

            tasks_list = (
                session.query(Task)
                .options(joinedload(Task.website))
                .filter(Task.id.in_(task_ids), Task.organisation_id == organisation.id, Task.is_active == True)
                .all()
            )
            for task in track(tasks_list):
                logger.info(f"Inspecting search queries for task {task.id} on {task.website.name}")

                localized_queries = organisation_DAO.get_organisation_localized_keywords(
                    organisation_id=organisation.id,
                    country_code=task.website.country_code,
                    include_main_queries=True,
                )

                org_queries = list(re.sub(" +", " ", q).strip().lower() for q in localized_queries)
                if not org_queries:
                    logger.warn(f"Cannot find queries for task={task.id} on website={task.website.name}")
                    exit()

                if not task.search_queries:
                    logger.warn(f"Cannot find queries for task={task.id} on website={task.website.name}")
                    continue

                task_queries = list(re.sub(" +", " ", q).strip().lower() for q in task.search_queries)
                for query in task_queries:
                    if query not in org_queries:
                        logger.warn(
                            f"Search query {query} for task {task.id} on {task.website.name} is not in the list of organisation queries"
                        )
