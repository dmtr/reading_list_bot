"""Remove m2m, add email

Revision ID: f9a010384b53
Revises: 06ce7016ca41
Create Date: 2020-02-18 20:20:16.369674

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f9a010384b53"
down_revision = "06ce7016ca41"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("user_article_m2m")
    op.add_column(
        "article", sa.Column("user_id", sa.Integer(), sa.ForeignKey("telegram_user.id", ondelete="CASCADE"), nullable=False)
    )

    op.add_column("user_settings", sa.Column("email", sa.String(80), nullable=True))


def downgrade():
    op.create_table(
        "user_article_m2m",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("telegram_user.id")),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("article.id")),
    )

    op.drop_column("article", "user_id")
    op.drop_column("user_settings", "email")
