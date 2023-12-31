"""Add light post saving

Revision ID: 3c957406938a
Revises: 9ae3f5f59c3e
Create Date: 2023-01-13 17:41:52.924403

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3c957406938a"
down_revision = "9ae3f5f59c3e"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("posts", sa.Column("light_post_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("posts", "light_post_payload")
    # ### end Alembic commands ###
