"""bl_draft — 연성(쓰다 만 회차) 서버 보관함

작가가 다른 기기에서 이어 쓸 수 있어야 해서 브라우저가 아니라 서버에 둔다.
회차 테이블과 분리한 이유는 app/models.py 의 BlDraft docstring 참고.

Revision ID: 0007
Revises: 0006
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bl_draft',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        # 계정의 고정 키 (BL_USERS)
        sa.Column('author_key', sa.String(length=64), nullable=False),
        sa.Column('series_id', sa.BigInteger(), nullable=False),
        # 0 = 아직 만들지 않은 새 회차. NULL 로 두면 PG14 가 NULL 끼리
        # 서로 다르다고 봐서 아래 유니크 제약이 걸리지 않는다.
        sa.Column('episode_no', sa.Integer(), server_default='0', nullable=False),
        sa.Column('title', sa.String(length=200), server_default='', nullable=False),
        sa.Column('body', sa.Text(), server_default='', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['series_id'], ['bl_series.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # 작가 × 작품 × 회차 당 연성 하나
        sa.UniqueConstraint(
            'author_key', 'series_id', 'episode_no', name='uq_bl_draft_author_series_ep'
        ),
    )
    op.create_index('ix_bl_draft_author_key', 'bl_draft', ['author_key'])
    op.create_index('ix_bl_draft_series_id', 'bl_draft', ['series_id'])


def downgrade() -> None:
    op.drop_table('bl_draft')
