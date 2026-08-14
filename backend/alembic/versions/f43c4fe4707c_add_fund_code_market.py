"""add fund_code market

Revision ID: f43c4fe4707c
Revises: 4b48d9ff3e03
Create Date: 2026-08-14 15:43:10.537112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f43c4fe4707c'
down_revision: Union[str, None] = '4b48d9ff3e03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'fund_codes',
        sa.Column('market', sa.String(length=8), server_default='OF', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('fund_codes', 'market')
