"""First

Revision ID: 440e8d7ed37b
Revises:
Create Date: 2020-02-12 17:09:41.322068

"""
from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = "440e8d7ed37b"
down_revision = None
branch_labels = None
depends_on = None


article_status = ENUM("NEW", "READ", name="article_status")


def upgrade():
    op.create_table(
        "telegram_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            unique=False,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("first_name", sa.String(50), unique=False, nullable=False),
        sa.Column("telegram_id", sa.types.BigInteger(), unique=True, nullable=False, index=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "article",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            unique=False,
            nullable=False,
            index=True,
            server_default=sa.text("now()"),
        ),
        sa.Column("text", sa.types.Text(), unique=False, nullable=False),
        sa.Column("status", article_status, unique=False, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_article_m2m",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("telegram_user.id")),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("article.id")),
    )

    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("telegram_user.id")),
        sa.Column("reading_list_size", sa.Integer(), nullable=False),
        sa.Column("article_ttl_in_days", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("telegram_user")
    op.drop_table("article")
    op.drop_table("user_article_m2m")
    op.drop_table("user_settings")
    article_status.drop(op.get_bind())
