"""Add scraping attempt table

Revision ID: 2bf694e7fceb
Revises: e023b3a4cc46
Create Date: 2023-05-10 16:16:44.650644

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2bf694e7fceb"
down_revision = "e023b3a4cc46"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "scraping_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("page_title", sa.String(), nullable=True),
        sa.Column("screenshot", sa.String(), nullable=True),
        sa.Column("website_id", sa.Integer(), nullable=False),
        sa.Column("proxy_provider", sa.String(), nullable=True),
        sa.Column("proxy_country", sa.String(), nullable=True),
        sa.Column("proxy_ip", sa.String(), nullable=True),
        sa.Column(
            "request_result",
            sa.Enum("SUCCESS", "TIMEOUT", "PROXY_FAILURE", "SCRAPING_FAILURE", "DRIVER_FAILURE", name="requestresult"),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["website_id"],
            ["websites.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proxy", "scraping_attempts", ["proxy_provider", "proxy_country"], unique=False)
    op.create_index(op.f("ix_scraping_attempts_proxy_provider"), "scraping_attempts", ["proxy_provider"], unique=False)
    op.create_index(op.f("ix_scraping_attempts_website_id"), "scraping_attempts", ["website_id"], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_scraping_attempts_website_id"), table_name="scraping_attempts")
    op.drop_index(op.f("ix_scraping_attempts_proxy_provider"), table_name="scraping_attempts")
    op.drop_index("ix_proxy", table_name="scraping_attempts")
    op.drop_table("scraping_attempts")
    # ### end Alembic commands ###
