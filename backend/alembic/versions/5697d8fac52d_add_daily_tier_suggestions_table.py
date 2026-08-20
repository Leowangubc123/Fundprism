"""add daily_tier_suggestions table

Revision ID: 5697d8fac52d
Revises: 0dae38741b94
Create Date: 2026-08-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '5697d8fac52d'
down_revision: Union[str, None] = '0dae38741b94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'daily_tier_suggestions' not in tables:
        op.create_table(
            'daily_tier_suggestions',
            sa.Column('id', UUID(as_uuid=True), nullable=False),
            sa.Column('fund_id', UUID(as_uuid=True), nullable=False),
            sa.Column('date', sa.Date(), nullable=False),
            sa.Column('suggested_tier', sa.String(length=16), nullable=False),
            sa.Column('reason', sa.String(length=50), nullable=True),
            sa.Column('score', sa.Numeric(precision=6, scale=2), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['fund_id'], ['funds.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('fund_id', 'date', name='uq_daily_tier_suggestion_fund_date')
        )
        op.create_index(op.f('ix_daily_tier_suggestions_fund_id'), 'daily_tier_suggestions', ['fund_id'], unique=False)
        op.create_index(op.f('ix_daily_tier_suggestions_date'), 'daily_tier_suggestions', ['date'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'daily_tier_suggestions' in tables:
        op.drop_index(op.f('ix_daily_tier_suggestions_date'), table_name='daily_tier_suggestions')
        op.drop_index(op.f('ix_daily_tier_suggestions_fund_id'), table_name='daily_tier_suggestions')
        op.drop_table('daily_tier_suggestions')
