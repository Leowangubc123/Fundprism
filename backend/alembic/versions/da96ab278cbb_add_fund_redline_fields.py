"""add fund redline fields

Revision ID: da96ab278cbb
Revises: 5697d8fac52d
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'da96ab278cbb'
down_revision: Union[str, None] = '5697d8fac52d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('funds')}

    if 'manager_start_date' not in columns:
        op.add_column(
            'funds',
            sa.Column('manager_start_date', sa.Date(), nullable=True),
        )

    if 'is_abnormal' not in columns:
        op.add_column(
            'funds',
            sa.Column(
                'is_abnormal',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('false'),
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('funds')}

    if 'is_abnormal' in columns:
        op.drop_column('funds', 'is_abnormal')

    if 'manager_start_date' in columns:
        op.drop_column('funds', 'manager_start_date')
