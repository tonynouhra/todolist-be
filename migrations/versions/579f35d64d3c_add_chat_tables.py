"""Add chat tables

Revision ID: 579f35d64d3c
Revises: a3577f0d1eb7
Create Date: 2025-10-04 21:17:24.224382

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '579f35d64d3c'
down_revision: Union[str, None] = 'a3577f0d1eb7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create chat_conversations table
    op.create_table(
        'chat_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_conversations_user_updated', 'chat_conversations', ['user_id', 'updated_at'])

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', 'system', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('has_actions', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_messages_conversation_created', 'chat_messages', ['conversation_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('idx_chat_messages_conversation_created', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index('idx_chat_conversations_user_updated', table_name='chat_conversations')
    op.drop_table('chat_conversations')
    op.execute('DROP TYPE messagerole')
