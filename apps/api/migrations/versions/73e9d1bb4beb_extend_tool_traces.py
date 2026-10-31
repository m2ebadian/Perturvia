"""extend tool traces

Revision ID: 73e9d1bb4beb
Revises: 2659ef488cc8
Create Date: 2026-10-31 18:35:34.188606

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "73e9d1bb4beb"
down_revision: str | Sequence[str] | None = "2659ef488cc8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Required columns start nullable so existing rows can be backfilled first.
    op.add_column("tool_traces", sa.Column("run_id", sa.Uuid(), nullable=True))
    op.add_column("tool_traces", sa.Column("agent_id", sa.Uuid(), nullable=True))
    op.add_column("tool_traces", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("tool_traces", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))

    # Each pre-existing trace becomes its own run; created_at approximates its start time.
    op.execute("UPDATE tool_traces SET run_id = uuidv7(), started_at = created_at")

    op.alter_column("tool_traces", "run_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column(
        "tool_traces",
        "started_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )

    op.create_index("ix_tool_traces_run_id", "tool_traces", ["run_id"])
    op.create_index("ix_tool_traces_agent_id", "tool_traces", ["agent_id"])
    op.create_foreign_key(
        "fk_tool_traces_agent_id_agents",
        "tool_traces",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_tool_traces_status",
        "tool_traces",
        "status IN ('success', 'tool_error', 'client_exception')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_tool_traces_status", "tool_traces", type_="check")
    op.drop_constraint("fk_tool_traces_agent_id_agents", "tool_traces", type_="foreignkey")
    op.drop_index("ix_tool_traces_run_id", table_name="tool_traces")
    op.drop_index("ix_tool_traces_agent_id", table_name="tool_traces")
    op.drop_column("tool_traces", "started_at")
    op.drop_column("tool_traces", "error_message")
    op.drop_column("tool_traces", "agent_id")
    op.drop_column("tool_traces", "run_id")
