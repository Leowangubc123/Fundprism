"""add fund_id to sync_logs

Revision ID: 0dae38741b94
Revises: 0d429adfa678
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '0dae38741b94'
down_revision: Union[str, None] = '0d429adfa678'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('sync_logs')]

    if 'fund_id' not in columns:
        op.add_column(
            'sync_logs',
            sa.Column('fund_id', UUID(as_uuid=True), sa.ForeignKey('funds.id', ondelete='SET NULL'), nullable=True)
        )
        op.create_index(op.f('ix_sync_logs_fund_id'), 'sync_logs', ['fund_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes('sync_logs')]
    columns = [c['name'] for c in inspector.get_columns('sync_logs')]

    if 'ix_sync_logs_fund_id' in indexes:
        op.drop_index(op.f('ix_sync_logs_fund_id'), table_name='sync_logs')
    if 'fund_id' in columns:
        op.drop_column('sync_logs', 'fund_id')
