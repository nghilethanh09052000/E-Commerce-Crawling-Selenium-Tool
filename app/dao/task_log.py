from app.models import Session, TaskLog


class TaskLogDAO:
    def create(self, name=None, task_id=None, payload=None, website_id=None):
        with Session() as session:
            task_log = TaskLog(name=name, task_id=task_id, payload=payload, website_id=website_id)
            session.add(task_log)
            session.commit()
            return task_log

    def update(self, task_log_id, body):
        with Session() as session:
            (session.query(TaskLog).filter(TaskLog.id == task_log_id).update(body, synchronize_session=False))
            session.commit()
