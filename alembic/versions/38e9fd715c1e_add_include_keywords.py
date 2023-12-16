"""Add include keywords

Revision ID: 38e9fd715c1e
Revises: 3a2f2f590a33
Create Date: 2023-04-26 10:47:32.949543

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "38e9fd715c1e"
down_revision = "3a2f2f590a33"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("organisations", sa.Column("must_have_keywords", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("organisations", "must_have_keywords")
    # ### end Alembic commands ###