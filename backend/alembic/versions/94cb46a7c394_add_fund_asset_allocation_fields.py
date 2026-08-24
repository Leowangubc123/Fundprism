"""add fund asset allocation fields

Revision ID: 94cb46a7c394
Revises: da96ab278cbb
Create Date: 2026-08-24 10:19:38.382470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94cb46a7c394'
down_revision: Union[str, None] = 'da96ab278cbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('funds')}

    fields = [
        ('asset_stock_pct', sa.Numeric(5, 2)),
        ('asset_bond_pct', sa.Numeric(5, 2)),
        ('asset_cash_pct', sa.Numeric(5, 2)),
        ('asset_other_pct', sa.Numeric(5, 2)),
    ]

    for name, col_type in fields:
        if name not in columns:
            op.add_column(
                'funds',
                sa.Column(name, col_type, nullable=True),
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('funds')}

    for name in (
        'asset_other_pct',
        'asset_cash_pct',
        'asset_bond_pct',
        'asset_stock_pct',
    ):
        if name in columns:
            op.drop_column('funds', name)
