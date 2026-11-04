"""Phase 5: WhatsApp Cloud API, Templates, Usage Logs, and Voice Notes

Revision ID: 003_phase5_whatsapp_and_templates
Revises: 002_phase4_instagram_and_comments
Create Date: 2026-11-04 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_phase5_whatsapp_and_templates'
down_revision = '002_phase4_instagram_and_comments'
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. whatsapp_connections
    if 'whatsapp_connections' not in tables:
        op.create_table(
            'whatsapp_connections',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('phone_number_id', sa.String(length=100), nullable=False),
            sa.Column('waba_id', sa.String(length=100), nullable=True),
            sa.Column('phone_number', sa.String(length=50), nullable=True),
            sa.Column('encrypted_access_token', sa.Text(), nullable=False),
            sa.Column('is_test_number', sa.Boolean(), default=True),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('auto_send', sa.Boolean(), default=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_whatsapp_connections_id'), 'whatsapp_connections', ['id'], unique=False)
        op.create_index(op.f('ix_whatsapp_connections_phone_number_id'), 'whatsapp_connections', ['phone_number_id'], unique=True)

    # 2. whatsapp_templates
    if 'whatsapp_templates' not in tables:
        op.create_table(
            'whatsapp_templates',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('waba_id', sa.String(length=100), nullable=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=False),
            sa.Column('language', sa.String(length=20), default='bn'),
            sa.Column('status', sa.String(length=50), default='APPROVED'),
            sa.Column('header_text', sa.String(length=255), nullable=True),
            sa.Column('body_text', sa.Text(), nullable=False),
            sa.Column('footer_text', sa.String(length=255), nullable=True),
            sa.Column('buttons_json', sa.JSON(), nullable=True),
            sa.Column('meta_template_id', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_whatsapp_templates_id'), 'whatsapp_templates', ['id'], unique=False)
        op.create_index(op.f('ix_whatsapp_templates_name'), 'whatsapp_templates', ['name'], unique=False)

    # 3. whatsapp_usage_logs
    if 'whatsapp_usage_logs' not in tables:
        op.create_table(
            'whatsapp_usage_logs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('message_id', sa.String(length=150), nullable=True),
            sa.Column('thread_id', sa.Integer(), nullable=True),
            sa.Column('customer_id', sa.Integer(), nullable=True),
            sa.Column('recipient_phone', sa.String(length=50), nullable=False),
            sa.Column('category', sa.String(length=50), nullable=False),
            sa.Column('direction', sa.String(length=20), default='outbound'),
            sa.Column('template_name', sa.String(length=100), nullable=True),
            sa.Column('status', sa.String(length=50), default='sent'),
            sa.Column('timestamp', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_whatsapp_usage_logs_id'), 'whatsapp_usage_logs', ['id'], unique=False)
        op.create_index(op.f('ix_whatsapp_usage_logs_category'), 'whatsapp_usage_logs', ['category'], unique=False)

    # 4. Add voice note columns to messages table if not present
    if 'messages' in tables:
        message_cols = [c['name'] for c in inspector.get_columns('messages')]
        if 'audio_url' not in message_cols:
            op.add_column('messages', sa.Column('audio_url', sa.String(length=500), nullable=True))
        if 'voice_transcript' not in message_cols:
            op.add_column('messages', sa.Column('voice_transcript', sa.Text(), nullable=True))
        if 'voice_confidence' not in message_cols:
            op.add_column('messages', sa.Column('voice_confidence', sa.Float(), nullable=True))
        if 'is_voice_message' not in message_cols:
            op.add_column('messages', sa.Column('is_voice_message', sa.Boolean(), default=False))

def downgrade() -> None:
    op.drop_table('whatsapp_usage_logs')
    op.drop_table('whatsapp_templates')
    op.drop_table('whatsapp_connections')
