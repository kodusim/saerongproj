"""baseline — Django 가 만들어 둔 기존 3개 테이블

운영 DB 에는 이 테이블들이 이미 있다. 그래서 운영에서는 실행하지 않고
`alembic stamp 0001` 로 리비전만 기록한다. 이 파일은 빈 DB(로컬/테스트)에서
같은 스키마를 만들기 위한 것이다.

Revision ID: 0001
Revises:
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tdm_predictionlog',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('login_id', sa.String(length=64), nullable=False),
        sa.Column('input_json', postgresql.JSONB(), nullable=False),
        sa.Column('result_json', postgresql.JSONB(), nullable=False),
        sa.Column('ml_model', sa.String(length=32), nullable=False),
        sa.Column('dl_model', sa.String(length=32), nullable=False),
    )

    op.create_table(
        'work_workchatmessage',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('sender_name', sa.String(length=32), nullable=False),
        sa.Column('sender_ip', postgresql.INET(), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('image', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'work_workpost',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('category', sa.String(length=16), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('author_name', sa.String(length=32), nullable=False),
        sa.Column('author_ip', postgresql.INET(), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('views', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('views >= 0', name='work_workpost_views_check'),
    )


def downgrade() -> None:
    op.drop_table('work_workpost')
    op.drop_table('work_workchatmessage')
    op.drop_table('tdm_predictionlog')
