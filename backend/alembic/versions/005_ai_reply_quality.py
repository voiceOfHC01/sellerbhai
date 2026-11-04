"""Phase 8: AI Reply Quality, Self-Check Guardrails, and Eval Tracking

Revision ID: 005_ai_reply_quality
Revises: 004_phase6_posts_and_broadcasts
Create Date: 2026-11-04 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_ai_reply_quality'
down_revision = '004_phase6_posts_and_broadcasts'
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. Add aliases to products if missing
    product_cols = [c['name'] for c in inspector.get_columns('products')]
    if 'aliases' not in product_cols:
        op.add_column('products', sa.Column('aliases', sa.Text(), nullable=True))

    # 2. Add eval & guardrail columns to ai_runs if missing
    ai_run_cols = [c['name'] for c in inspector.get_columns('ai_runs')]
    if 'model_name' not in ai_run_cols:
        op.add_column('ai_runs', sa.Column('model_name', sa.String(length=100), server_default='gemini-1.5-flash', nullable=True))
    if 'token_cost_usd' not in ai_run_cols:
        op.add_column('ai_runs', sa.Column('token_cost_usd', sa.Float(), server_default='0.0', nullable=True))
    if 'is_blocked' not in ai_run_cols:
        op.add_column('ai_runs', sa.Column('is_blocked', sa.Boolean(), server_default='0', nullable=True))
    if 'blocked_reason' not in ai_run_cols:
        op.add_column('ai_runs', sa.Column('blocked_reason', sa.Text(), nullable=True))
    if 'prompt_version' not in ai_run_cols:
        op.add_column('ai_runs', sa.Column('prompt_version', sa.String(length=50), server_default='v1.1', nullable=True))
    if 'corrected_reply' not in ai_run_cols:
        op.add_column('ai_runs', sa.Column('corrected_reply', sa.Text(), nullable=True))

def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    ai_run_cols = [c['name'] for c in inspector.get_columns('ai_runs')]
    for col in ['corrected_reply', 'prompt_version', 'blocked_reason', 'is_blocked', 'token_cost_usd', 'model_name']:
        if col in ai_run_cols:
            op.drop_column('ai_runs', col)

    product_cols = [c['name'] for c in inspector.get_columns('products')]
    if 'aliases' in product_cols:
        op.drop_column('products', 'aliases')
