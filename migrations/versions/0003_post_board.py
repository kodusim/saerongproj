"""work_workpost.board — 자료실 / 공지사항 구분

기존 글은 전부 자료실('archive')이다. 그래서 server_default 를 주고
NOT NULL 로 추가한다 (기존 행이 자동으로 채워진다).

Revision ID: 0003
Revises: 0002
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'work_workpost',
        sa.Column('board', sa.String(length=16), server_default='archive', nullable=False),
    )
    # 목록은 항상 board 로 걸러 뽑는다
    op.create_index('ix_work_workpost_board', 'work_workpost', ['board'])


def downgrade() -> None:
    op.drop_index('ix_work_workpost_board', table_name='work_workpost')
    op.drop_column('work_workpost', 'board')
