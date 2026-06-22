"""schema improvements: indexes, JSONB, TIMESTAMPTZ

Revision ID: 5b9c3e1a2d7f
Revises: 3a1f9b2c0d4e
Create Date: 2026-06-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '5b9c3e1a2d7f'
down_revision = '3a1f9b2c0d4e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # FK indexes — PostgreSQL does not create these automatically
    op.create_index('ix_articles_stock_id', 'articles', ['stock_id'])
    op.create_index('ix_evaluations_report_id', 'evaluations', ['report_id'])
    op.create_index('ix_articles_published_at', 'articles', ['published_at'])

    # JSON → JSONB for bull_points and bear_points
    op.alter_column(
        'reports', 'bull_points',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(),
        postgresql_using='bull_points::jsonb',
    )
    op.alter_column(
        'reports', 'bear_points',
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(),
        postgresql_using='bear_points::jsonb',
    )

    # TIMESTAMP → TIMESTAMPTZ (interpret existing values as UTC)
    for table, column in [
        ('stocks', 'created_at'),
        ('stocks', 'updated_at'),
        ('articles', 'published_at'),
        ('articles', 'created_at'),
        ('reports', 'created_at'),
        ('evaluations', 'created_at'),
    ]:
        op.alter_column(
            table, column,
            existing_type=sa.TIMESTAMP(),
            type_=sa.TIMESTAMP(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    # TIMESTAMPTZ → TIMESTAMP
    for table, column in [
        ('evaluations', 'created_at'),
        ('reports', 'created_at'),
        ('articles', 'created_at'),
        ('articles', 'published_at'),
        ('stocks', 'updated_at'),
        ('stocks', 'created_at'),
    ]:
        op.alter_column(
            table, column,
            existing_type=sa.TIMESTAMP(timezone=True),
            type_=sa.TIMESTAMP(),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )

    # JSONB → JSON
    op.alter_column(
        'reports', 'bear_points',
        existing_type=postgresql.JSONB(),
        type_=postgresql.JSON(astext_type=sa.Text()),
        postgresql_using='bear_points::json',
    )
    op.alter_column(
        'reports', 'bull_points',
        existing_type=postgresql.JSONB(),
        type_=postgresql.JSON(astext_type=sa.Text()),
        postgresql_using='bull_points::json',
    )

    op.drop_index('ix_articles_published_at', 'articles')
    op.drop_index('ix_evaluations_report_id', 'evaluations')
    op.drop_index('ix_articles_stock_id', 'articles')
