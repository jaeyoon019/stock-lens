"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
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
        sa.Column('sector', sa.String(100), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker'),
    )

    # articles
    op.create_table(
        'articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stock_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('url', sa.String(2000), nullable=False),
        sa.Column('url_hash', sa.String(64), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('sentiment', sa.String(20), nullable=True),
        sa.Column('published_at', sa.TIMESTAMP(), nullable=True),
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
        sa.Column('article_count', sa.Integer(), nullable=True),
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
    op.drop_table('stocks')
