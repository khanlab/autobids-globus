"""create initial tables

Revision ID: 87575c790c2d
Revises: 
Create Date: 2022-06-01 15:58:21.533793

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "87575c790c2d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "guest_collection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("globus_uuid", postgresql.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("globus_uuid"),
        sa.UniqueConstraint("study_id"),
    )
    op.create_table(
        "globus_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("guest_collection_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["guest_collection_id"],
            ["guest_collection.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "association",
        sa.Column("guest_collection_id", sa.Integer(), nullable=False),
        sa.Column("globus_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["globus_user_id"],
            ["globus_user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["guest_collection_id"],
            ["guest_collection.id"],
        ),
        sa.PrimaryKeyConstraint("guest_collection_id", "globus_user_id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("association")
    op.drop_table("globus_user")
    op.drop_table("guest_collection")
    # ### end Alembic commands ###
