"""Add refresh token fields to users table

Revision ID: add_refresh_token_to_users
Revises: 587ecad0657e_initial_sqlite_migration
Create Date: 2026-05-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_refresh_token_to_users'
down_revision = '587ecad0657e_initial_sqlite_migration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add refresh token fields to users table
    op.add_column('users', sa.Column('refresh_token_hash', sa.String(), nullable=True))
    op.add_column('users', sa.Column('refresh_token_expires_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_users_refresh_token_hash'), 'users', ['refresh_token_hash'], unique=False)
    op.create_index(op.f('ix_users_refresh_token_expires_at'), 'users', ['refresh_token_expires_at'], unique=False)


def downgrade() -> None:
    # Remove refresh token fields from users table
    op.drop_index(op.f('ix_users_refresh_token_expires_at'), table_name='users')
    op.drop_index(op.f('ix_users_refresh_token_hash'), table_name='users')
    op.drop_column('users', 'refresh_token_expires_at')
    op.drop_column('users', 'refresh_token_hash')
