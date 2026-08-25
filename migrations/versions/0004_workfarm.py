"""work_workfarm — 농장 게임 저장

Revision ID: 0004
Revises: 0003
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'work_workfarm',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('owner_ip', postgresql.INET(), nullable=False),
        sa.Column('owner_name', sa.String(length=32), server_default='익명 농부', nullable=False),
        sa.Column('money', sa.BigInteger(), server_default='50', nullable=False),
        sa.Column('plots', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('buildings', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        # 한 IP 당 농장 하나 — 동시에 두 번 열어도 중복 생성되지 않게 DB 로 막는다
        sa.UniqueConstraint('owner_ip', name='uq_work_workfarm_owner_ip'),
    )


def downgrade() -> None:
    op.drop_table('work_workfarm')
