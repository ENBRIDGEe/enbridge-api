"""drop refresh token columns from users

Revision ID: 7f9d3a6e4b21
Revises: 1ccd002a7a90
Create Date: 2026-05-17 20:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f9d3a6e4b21"
down_revision: Union[str, Sequence[str], None] = "1ccd002a7a90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    """Drop legacy refresh-token columns and indexes from users."""
    if _has_index("users", "ix_users_refresh_token_revoked_at"):
        op.drop_index("ix_users_refresh_token_revoked_at", table_name="users")

    if _has_index("users", "ix_users_refresh_token_expires_at"):
        op.drop_index("ix_users_refresh_token_expires_at", table_name="users")

    if _has_index("users", "ix_users_refresh_token_hash"):
        op.drop_index("ix_users_refresh_token_hash", table_name="users")

    if _has_column("users", "refresh_token_revoked_at"):
        op.drop_column("users", "refresh_token_revoked_at")

    if _has_column("users", "refresh_token_expires_at"):
        op.drop_column("users", "refresh_token_expires_at")

    if _has_column("users", "refresh_token_hash"):
        op.drop_column("users", "refresh_token_hash")


def downgrade() -> None:
    """Restore legacy refresh-token columns and indexes on users."""
    if not _has_column("users", "refresh_token_hash"):
        op.add_column("users", sa.Column("refresh_token_hash", sa.String(), nullable=True))

    if not _has_column("users", "refresh_token_expires_at"):
        op.add_column("users", sa.Column("refresh_token_expires_at", sa.DateTime(), nullable=True))

    if not _has_column("users", "refresh_token_revoked_at"):
        op.add_column("users", sa.Column("refresh_token_revoked_at", sa.DateTime(), nullable=True))

    if not _has_index("users", "ix_users_refresh_token_hash"):
        op.create_index("ix_users_refresh_token_hash", "users", ["refresh_token_hash"], unique=True)

    if not _has_index("users", "ix_users_refresh_token_expires_at"):
        op.create_index(
            "ix_users_refresh_token_expires_at",
            "users",
            ["refresh_token_expires_at"],
            unique=False,
        )

    if not _has_index("users", "ix_users_refresh_token_revoked_at"):
        op.create_index(
            "ix_users_refresh_token_revoked_at",
            "users",
            ["refresh_token_revoked_at"],
            unique=False,
        )