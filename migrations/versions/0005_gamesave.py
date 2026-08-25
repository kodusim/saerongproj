"""work_gamesave — 게임 공용 저장 슬롯

Revision ID: 0005
Revises: 0004
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'work_gamesave',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('owner_ip', postgresql.INET(), nullable=False),
        sa.Column('game', sa.String(length=32), nullable=False),
        sa.Column('data', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        # 사람 × 게임 당 슬롯 하나
        sa.UniqueConstraint('owner_ip', 'game', name='uq_work_gamesave_owner_game'),
    )


def downgrade() -> None:
    op.drop_table('work_gamesave')
