"""Add Google subject for User Service accounts.

Revision ID: 0002_add_google_sub
Revises: 0001_create_users
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_add_google_sub"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])


def downgrade() -> None:
    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    op.drop_column("users", "google_sub")
