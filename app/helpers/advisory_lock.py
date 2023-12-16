import hashlib

from app.models import Session
from sqlalchemy import func, select

"""
Query to check the current advisoy locks:

SELECT * FROM pg_locks pl LEFT JOIN pg_stat_activity psa
ON pl.pid = psa.pid
WHERE locktype = 'advisory'
ORDER BY backend_start DESC;
"""


def execute(session, lock_fn, lock_id):
    """Execute the lock function

    Parameters
    ==========
    lock_fn: PostgreSQL function
        either pg_try_advisory_lock or pg_advisory_unlock
    lock_id: int or str
    """

    # We hash the lock_id to convert a string to an integer in an injective way
    key_bytes = str(lock_id).encode("utf-8")
    full_hash = hashlib.sha256()
    full_hash.update(key_bytes)

    # pg_try_advisory_xact_lock is limited to an 8-byte signed integer
    int_lock_id = int.from_bytes(full_hash.digest()[:8], byteorder="big", signed=True)

    return session.execute(select([lock_fn(int_lock_id)])).scalar()


def obtain_lock(session, lock_id):
    """Obtain the advisory lock

    Parameters
    ==========
    lock_id: int or str
    """

    lock_fn = func.pg_try_advisory_lock
    return execute(session, lock_fn, lock_id)


def release_lock(session, lock_id):
    """Release the advisory lock

    Parameters
    ==========
    lock_id: int or str
    """

    lock_fn = func.pg_advisory_unlock
    return execute(session, lock_fn, lock_id)


def with_lock(my_func, lock_id, args=[]):
    """Executes my_func with the arguments args if the lock can be obtained then release the lock"

    Parameters
    ==========
    my_func: Python function
    lock_id: int or str
    args (optional): list of arguments to be passed to the function
    """

    obtained_lock = False
    try:
        obtained_lock = obtain_lock(Session, lock_id)
        if obtained_lock:
            print("lock obtained")
            my_func(*args)

        from time import sleep

        sleep(5)

    finally:
        if obtained_lock:
            release_lock(Session, lock_id)
            print("released lock")


def run(who="Nobody", how="at all"):
    print(f"{who} runs {how}")


if __name__ == "__main__":
    with_lock(run, "resource_42", ["Antoine", "fast"])
    with_lock(run, 42)
