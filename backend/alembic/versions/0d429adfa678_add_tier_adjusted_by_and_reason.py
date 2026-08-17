"""add tier adjusted_by and reason

Revision ID: 0d429adfa678
Revises: 3cfabecc9c3a
Create Date: 2026-08-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d429adfa678'
down_revision: Union[str, None] = '3cfabecc9c3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect != 'postgresql':
        return

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS fund_current_tiers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            fund_id UUID NOT NULL UNIQUE REFERENCES funds(id),
            current_tier VARCHAR(16) NOT NULL DEFAULT '观察',
            suggested_tier VARCHAR(16),
            suggested_at TIMESTAMP,
            adjusted_at TIMESTAMP,
            manual_lock_until DATE,
            adjusted_by_id UUID REFERENCES users(id),
            adjusted_reason TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """))

    op.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS ix_fund_current_tiers_fund_id ON fund_current_tiers(fund_id);
    """))

    op.execute(sa.text("""
        ALTER TABLE fund_current_tiers
        ADD COLUMN IF NOT EXISTS adjusted_by_id UUID REFERENCES users(id),
        ADD COLUMN IF NOT EXISTS adjusted_reason TEXT;
    """))


def downgrade() -> None:
    pass
