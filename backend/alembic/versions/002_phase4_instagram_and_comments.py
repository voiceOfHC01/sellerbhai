"""Phase 4: Instagram connections and Comments automation

Revision ID: 002_phase4_instagram_and_comments
Revises: 001_initial_schema
Create Date: 2026-11-04 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_phase4_instagram_and_comments'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. facebook_connections (if not created by 001)
    # Check if table already exists to avoid duplication
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'facebook_connections' not in tables:
        op.create_table(
            'facebook_connections',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('page_id', sa.String(length=100), nullable=False),
            sa.Column('page_name', sa.String(length=255), nullable=False),
            sa.Column('encrypted_access_token', sa.Text(), nullable=False),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('auto_send', sa.Boolean(), default=False),
            sa.Column('connected_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_facebook_connections_id'), 'facebook_connections', ['id'], unique=False)
        op.create_index(op.f('ix_facebook_connections_page_id'), 'facebook_connections', ['page_id'], unique=True)

    # 2. instagram_connections
    if 'instagram_connections' not in tables:
        op.create_table(
            'instagram_connections',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('ig_user_id', sa.String(length=100), nullable=False),
            sa.Column('username', sa.String(length=100), nullable=True),
            sa.Column('page_id', sa.String(length=100), nullable=True),
            sa.Column('encrypted_access_token', sa.Text(), nullable=False),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('auto_send', sa.Boolean(), default=False),
            sa.Column('connected_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_instagram_connections_id'), 'instagram_connections', ['id'], unique=False)
        op.create_index(op.f('ix_instagram_connections_ig_user_id'), 'instagram_connections', ['ig_user_id'], unique=True)

    # 3. comments
    if 'comments' not in tables:
        op.create_table(
            'comments',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('platform', sa.String(length=50), nullable=False),
            sa.Column('platform_comment_id', sa.String(length=150), nullable=False),
            sa.Column('post_id', sa.String(length=150), nullable=True),
            sa.Column('author_id', sa.String(length=150), nullable=False),
            sa.Column('author_name', sa.String(length=255), nullable=True),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('status', sa.String(length=50), default='pending'),
            sa.Column('actions_taken', sa.JSON(), nullable=True),
            sa.Column('public_reply_text', sa.Text(), nullable=True),
            sa.Column('private_reply_text', sa.Text(), nullable=True),
            sa.Column('is_hidden', sa.Boolean(), default=False),
            sa.Column('is_private_reply_sent', sa.Boolean(), default=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_comments_id'), 'comments', ['id'], unique=False)
        op.create_index(op.f('ix_comments_platform_comment_id'), 'comments', ['platform_comment_id'], unique=True)
        op.create_index(op.f('ix_comments_post_id'), 'comments', ['post_id'], unique=False)

def downgrade() -> None:
    op.drop_table('comments')
    op.drop_table('instagram_connections')
    op.drop_table('facebook_connections')
