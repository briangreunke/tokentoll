"""initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-03-05 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("site_key", sa.String(), nullable=False),
        sa.Column("secret_key_hash", sa.String(), nullable=False),
        sa.Column("token_ttl_seconds", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("challenge_rate_limit", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_key"),
    )
    op.create_index(op.f("ix_sites_site_key"), "sites", ["site_key"], unique=True)

    op.create_table(
        "challenges",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("site_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("answer_key", sa.Text(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("pass_threshold", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("solved", sa.Boolean(), nullable=False),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "used_nonces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("challenge_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("nonce", sa.String(), nullable=False),
        sa.Column(
            "used_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("challenge_id", "nonce", name="uq_challenge_nonce"),
    )
    op.create_index(
        op.f("ix_used_nonces_challenge_id"),
        "used_nonces",
        ["challenge_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_used_nonces_challenge_id"), table_name="used_nonces")
    op.drop_table("used_nonces")
    op.drop_table("challenges")
    op.drop_index(op.f("ix_sites_site_key"), table_name="sites")
    op.drop_table("sites")
