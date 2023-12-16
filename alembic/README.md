## Generate a new database version

To automatically generate a revision of the database, run:
```
alembic revision --autogenerate -m "[Describe your change here]"
```

:warning: Auto-generation has some limitations, especially for renaming table or others database objects. It can destroy and recreate them instead of updating them. Always review the generated revision in the folder ./alembic/versions before applying or pushing it.

If that command fails ("can't locate revision"), run:
```
alembic history
```

Retrieve the latest revision ID associated with head and update it in the table alembic_version in database.

Then rerun the alembic revision command.

## Apply a database revision

To update the database to the last revision made, run:
```

```

If there are multiple heads:
```
alembic upgrade heads
```

Merge multiple heads
```
alembic merge revision_1 revision_2
```

## Working with multiple branches

https://alembic.sqlalchemy.org/en/latest/branches.html

:warning: Be careful with the environment you're using


## Locks: How to detect them ?

Postgresql 9.6 introduced a function pg_blocking_pids to find the sessions that are blocking each other.


You can use the following query to find them:
```
select pid,
       usename,
       pg_blocking_pids(pid) as blocked_by,
       query as blocked_query
from pg_stat_activity
where cardinality(pg_blocking_pids(pid)) > 0;
```


## Locks: How to remove them

```
SELECT pg_terminate_backend(PID);
```
