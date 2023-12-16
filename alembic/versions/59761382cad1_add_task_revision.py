"""Add task revision

Revision ID: 59761382cad1
Revises: 5186b35d2a53
Create Date: 2023-08-17 14:12:18.643870

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "59761382cad1"
down_revision = "5186b35d2a53"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("tasks", sa.Column("task_revision", sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("tasks", "task_revision")
    # ### end Alembic commands ###