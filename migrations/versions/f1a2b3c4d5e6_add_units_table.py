"""add units table

Revision ID: f1a2b3c4d5e6
Revises: 69cb9583f7c6
Create Date: 2026-04-07 15:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "69cb9583f7c6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "units",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("secret_key_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id"),
    )
    with op.batch_alter_table("units", schema=None) as batch_op:
        batch_op.create_index("idx_units_tenant_last_seen", ["tenant_id", "last_seen_at"], unique=False)
        batch_op.create_index("idx_units_status", ["status"], unique=False)


def downgrade():
    with op.batch_alter_table("units", schema=None) as batch_op:
        batch_op.drop_index("idx_units_status")
        batch_op.drop_index("idx_units_tenant_last_seen")
    op.drop_table("units")
