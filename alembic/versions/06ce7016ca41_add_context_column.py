"""Add context column

Revision ID: 06ce7016ca41
Revises: 440e8d7ed37b
Create Date: 2020-02-13 17:44:49.960247

"""
from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = '06ce7016ca41'
down_revision = '440e8d7ed37b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('telegram_user', sa.Column('context', JSONB))


def downgrade():
    op.drop_column('telegram_user', 'context')
