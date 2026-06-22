"""initial schema

Revision ID: 3a1f9b2c0d4e
Revises:
Create Date: 2026-06-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '3a1f9b2c0d4e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # stocks
    op.create_table(
        'stocks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticker', sa.String(20), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('market', sa.String(20), nullable=False),
        sa.Column('sector', sa.String(100)),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker', name='uq_stocks_ticker'),
    )

    # DB-level trigger so updated_at stays accurate even on bulk/raw SQL updates
    op.execute("""
        CREATE OR REPLACE FUNCTION trigger_set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER set_updated_at
        BEFORE UPDATE ON stocks
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at()
    """)

    # articles
    op.create_table(
        'articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stock_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('url', sa.String(2000), nullable=False),
        sa.Column('url_hash', sa.String(64), nullable=False),
        sa.Column('content', sa.Text()),
        sa.Column('summary', sa.Text()),
        sa.Column('sentiment', sa.String(20)),
        sa.Column('published_at', sa.TIMESTAMP()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url_hash', name='uq_articles_url_hash'),
    )

    # reports
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stock_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('bull_points', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('bear_points', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('overall_summary', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('article_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['stock_id'], ['stocks.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stock_id', 'report_date', name='uq_reports_stock_date'),
    )

    # evaluations
    op.create_table(
        'evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('judge_score', sa.Float(), nullable=False),
        sa.Column('judge_feedback', sa.Text(), nullable=False),
        sa.Column('model_used', sa.String(100), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('evaluations')
    op.drop_table('reports')
    op.drop_table('articles')
    op.execute('DROP TRIGGER IF EXISTS set_updated_at ON stocks')
    op.execute('DROP FUNCTION IF EXISTS trigger_set_updated_at')
    op.drop_table('stocks')
