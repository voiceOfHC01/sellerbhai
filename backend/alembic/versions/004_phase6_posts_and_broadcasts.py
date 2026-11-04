"""Phase 6: Posts, Scheduler, Calendar, and WhatsApp Broadcasts

Revision ID: 004_phase6_posts_and_broadcasts
Revises: 003_phase5_whatsapp_and_templates
Create Date: 2026-11-04 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_phase6_posts_and_broadcasts'
down_revision = '003_phase5_whatsapp_and_templates'
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. posts table
    if 'posts' not in tables:
        op.create_table(
            'posts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=True),
            sa.Column('caption', sa.Text(), nullable=False),
            sa.Column('hashtags', sa.Text(), nullable=True),
            sa.Column('media_urls', sa.JSON(), nullable=True),
            sa.Column('language', sa.String(length=50), server_default='Bangla', nullable=True),
            sa.Column('tone', sa.String(length=50), server_default='Friendly', nullable=True),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
            sa.Column('target_platforms', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(length=50), server_default='draft', nullable=True),
            sa.Column('scheduled_at', sa.DateTime(), nullable=True),
            sa.Column('published_at', sa.DateTime(), nullable=True),
            sa.Column('facebook_post_id', sa.String(length=100), nullable=True),
            sa.Column('instagram_media_id', sa.String(length=100), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('retry_count', sa.Integer(), server_default='0', nullable=True),
            sa.Column('max_retries', sa.Integer(), server_default='3', nullable=True),
            sa.Column('idempotency_key', sa.String(length=100), nullable=True),
            sa.Column('variants_json', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_posts_id'), 'posts', ['id'], unique=False)
        op.create_index(op.f('ix_posts_status'), 'posts', ['status'], unique=False)
        op.create_index(op.f('ix_posts_idempotency_key'), 'posts', ['idempotency_key'], unique=True)

    # 2. whatsapp_broadcasts table
    if 'whatsapp_broadcasts' not in tables:
        op.create_table(
            'whatsapp_broadcasts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('template_id', sa.Integer(), sa.ForeignKey('whatsapp_templates.id', ondelete='CASCADE'), nullable=False),
            sa.Column('template_name', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=50), server_default='completed', nullable=True),
            sa.Column('total_recipients', sa.Integer(), server_default='0', nullable=True),
            sa.Column('successful_sends', sa.Integer(), server_default='0', nullable=True),
            sa.Column('failed_sends', sa.Integer(), server_default='0', nullable=True),
            sa.Column('estimated_cost', sa.Float(), server_default='0.0', nullable=True),
            sa.Column('actual_cost', sa.Float(), server_default='0.0', nullable=True),
            sa.Column('currency', sa.String(length=10), server_default='BDT', nullable=True),
            sa.Column('parameters_json', sa.JSON(), nullable=True),
            sa.Column('error_summary', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_whatsapp_broadcasts_id'), 'whatsapp_broadcasts', ['id'], unique=False)

    # 3. Add is_opted_in column to customers if missing
    customer_cols = [c['name'] for c in inspector.get_columns('customers')]
    if 'is_opted_in' not in customer_cols:
        op.add_column('customers', sa.Column('is_opted_in', sa.Boolean(), server_default=sa.true(), nullable=True))

def downgrade() -> None:
    op.drop_table('whatsapp_broadcasts')
    op.drop_table('posts')
    op.drop_column('customers', 'is_opted_in')
