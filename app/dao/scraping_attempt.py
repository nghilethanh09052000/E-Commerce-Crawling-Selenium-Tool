from datetime import datetime, timezone

from app.models import ScrapingAttempt, Session
from app.models.enums import RequestResult


class ScrapingAttemptDAO:
    def create(
        self,
        url: str,
        page_title: str,
        screenshot: str,
        website_id: int,
        proxy_provider: str,
        proxy_country: str,
        proxy_ip: str,
        request_result: RequestResult,
        error_message: str,
    ) -> ScrapingAttempt:
        with Session() as session:
            scraping_attempt = ScrapingAttempt(
                url=url,
                time=datetime.now(timezone.utc),
                page_title=page_title,
                screenshot=screenshot,
                website_id=website_id,
                proxy_provider=proxy_provider,
                proxy_country=proxy_country,
                proxy_ip=proxy_ip,
                request_result=request_result,
                error_message=error_message,
            )
            session.add(scraping_attempt)
            session.commit()

        return scraping_attempt

    def update_result(self, scraping_attempt_id: int, result: RequestResult, error_message: str):
        with Session() as session:
            scraping_attempt = session.query(ScrapingAttempt).get(scraping_attempt_id)
            scraping_attempt.request_result = result
            scraping_attempt.error_message = error_message
            session.commit()
