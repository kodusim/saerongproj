"""bl_series / bl_episode / bl_report — BL 소설 플랫폼 1차

Revision ID: 0006
Revises: 0005
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bl_series',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        # 계정이 없는 1차에서 작가를 가르는 값 (localStorage 토큰)
        sa.Column('author_key', sa.String(length=64), nullable=False),
        sa.Column('author_name', sa.String(length=32), server_default='익명', nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('summary', sa.Text(), server_default='', nullable=False),
        sa.Column('tags', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('rating', sa.String(length=8), server_default='all', nullable=False),
        sa.Column('status', sa.String(length=16), server_default='ongoing', nullable=False),
        sa.Column('views', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        # 2차(계정)용 자리 — 지금은 항상 NULL
        sa.Column('author_user_id', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_bl_series_author_key', 'bl_series', ['author_key'])

    op.create_table(
        'bl_episode',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('series_id', sa.BigInteger(), nullable=False),
        sa.Column('no', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('body', sa.Text(), server_default='', nullable=False),
        # NULL = 임시저장 (작가만 볼 수 있다)
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('views', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        # 3차(유료화)용 자리
        sa.Column('is_free', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('price', sa.Integer(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['series_id'], ['bl_series.id'], ondelete='CASCADE',
        ),
        # 작품 안에서 회차 번호는 유일하다
        sa.UniqueConstraint('series_id', 'no', name='uq_bl_episode_series_no'),
    )
    op.create_index('ix_bl_episode_series_id', 'bl_episode', ['series_id'])

    op.create_table(
        'bl_report',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('target_type', sa.String(length=16), nullable=False),
        sa.Column('target_id', sa.BigInteger(), nullable=False),
        sa.Column('reason', sa.String(length=32), server_default='etc', nullable=False),
        sa.Column('detail', sa.Text(), server_default='', nullable=False),
        sa.Column('reporter_ip', postgresql.INET(), nullable=True),
        sa.Column('status', sa.String(length=16), server_default='open', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_bl_report_status', 'bl_report', ['status'])


def downgrade() -> None:
    op.drop_table('bl_report')
    op.drop_table('bl_episode')
    op.drop_table('bl_series')
