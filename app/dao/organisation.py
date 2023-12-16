from typing import List

from app import logger
from app.models import Session, Organisation, country_code_locale


class OrganisationDAO:
    def get(self, organisation_name) -> Organisation:
        with Session() as session:
            return session.query(Organisation).filter(Organisation.name == organisation_name).one()

    def get_all(self) -> List[Organisation]:
        with Session() as session:
            return session.query(Organisation).all()

    def get_organisation_keywords(self):
        """returns list of keywords with the organisation associated with them"""

        with Session() as session:
            active_organisations = session.query(Organisation).filter(Organisation.localized_keywords.isnot(None)).all()
            keyword_list = {}
            for entry in active_organisations:
                for locale, values in entry.localized_keywords.items():
                    for keyword in values:
                        keyword_list[keyword.lower()] = entry.name
            return keyword_list

    def get_organisation_localized_keywords(self, organisation_id, country_code=None, include_main_queries=True):
        """
        Return available language per country
        Retrieve the organisations keywords based on locale
        """

        keywords = []
        with Session() as session:
            organisation = session.query(Organisation).filter_by(id=organisation_id).first()

        if organisation is None or organisation.localized_keywords is None:
            return []

        # retrieve localized keywords
        organisation_keywords = organisation.localized_keywords

        # add main organisation keywords
        if include_main_queries and "en" in organisation_keywords:
            keywords.extend(organisation_keywords.get("en"))

        if country_code:
            # retrieve locales for country codes
            country_code_locales = country_code_locale.get(country_code, None)
            if country_code_locales is None:
                logger.error(f"Cannot find country code {country_code} in country_code_locale")
                return keywords

            ## get all local keywords if available
            for entry in country_code_locales:
                if entry in organisation_keywords:
                    keywords.extend(organisation_keywords.get(entry))

        return list(set(keywords))
