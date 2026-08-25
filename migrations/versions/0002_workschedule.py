"""work_workschedule — 만남 일정 (그룹웨어 '설비예약' 탭)

FastAPI 로 넘어온 뒤 처음 새로 만드는 테이블이라, 운영에서도 이 리비전은
stamp 가 아니라 실제로 실행한다.

Revision ID: 0002
Revises: 0001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'work_workschedule',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('meet_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('meet_time', sa.String(length=16), server_default='', nullable=False),
        sa.Column('place', sa.String(length=120), server_default='', nullable=False),
        sa.Column('attendees', sa.String(length=200), server_default='', nullable=False),
        sa.Column('memo', sa.Text(), server_default='', nullable=False),
        sa.Column('author_name', sa.String(length=32), server_default='익명', nullable=False),
        sa.Column('author_ip', postgresql.INET(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    # 목록은 항상 날짜순으로 뽑는다
    op.create_index('ix_work_workschedule_meet_date', 'work_workschedule', ['meet_date'])


def downgrade() -> None:
    op.drop_index('ix_work_workschedule_meet_date', table_name='work_workschedule')
    op.drop_table('work_workschedule')
