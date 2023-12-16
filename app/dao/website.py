from app.models import Session, Website


class WebsiteDAO:
    def get(self, domain_name: str) -> Website:
        with Session() as session:
            return session.query(Website).filter_by(name=domain_name).one()
