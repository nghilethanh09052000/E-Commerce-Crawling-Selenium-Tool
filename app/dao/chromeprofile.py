from app.models import Session, Chromeprofile, Website
from sqlalchemy import func
import sentry_sdk
from app.helpers.advisory_lock import obtain_lock


class ChromeprofileDAO:
    def get_available_chromeprofile(self, domain_name):
        """Try to grab a lock on a Chromeprofile available for domain_name"""
        with Session() as session:
            candidate_profiles = (
                session.query(Chromeprofile.id, Chromeprofile.name)
                .join(Website, Website.id == Chromeprofile.website_id)
                .filter(Website.domain_name == domain_name)
                .order_by(func.random())
            )

            obtained_lock = False
            for profile_id, profile_name in candidate_profiles:
                obtained_lock = obtain_lock(session, f"chromeprofile_{profile_id}")

                if obtained_lock:
                    break

            if not obtained_lock:
                message = f"No available Chromprofile for the website {domain_name}"
                sentry_sdk.capture_message(message)
                raise AssertionError(message)

            return profile_name
