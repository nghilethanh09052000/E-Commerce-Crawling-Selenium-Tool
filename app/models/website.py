from sqlalchemy import Boolean, Column, Integer, String, UniqueConstraint
from .base_model import Base


class Website(Base):
    __tablename__ = "websites"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    domain_name = Column(String, nullable=False)
    country_code = Column(String, nullable=True)

    # post_require_fields = Column(JSONB, default=lambda: {})
    title_required = Column(Boolean, default=True)
    description_required = Column(Boolean, default=False)
    price_required = Column(Boolean, default=True)
    vendor_required = Column(Boolean, default=True)
    pictures_required = Column(Boolean, default=True)

    # poster_require_fields = Column(JSONB, default=lambda: {})

    # monitor active websites
    is_active = Column(Boolean, default=True)

    # keep track of websites we want to add by default to all
    is_default = Column(Boolean, default=False)

    # Set a unicity contraint over organisation_id + website_id + platform_id
    __table_args__ = (UniqueConstraint("domain_name", "name"),)

    @property
    def serialize(self):
        return {
            "id": self.id,
            "domain_name": self.domain_name,
            "country_code": self.country_code,
        }
