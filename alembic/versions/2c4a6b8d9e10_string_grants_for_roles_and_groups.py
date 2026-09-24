"""string grants for roles and groups

Revision ID: 2c4a6b8d9e10
Revises: 7498f41deef6
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c4a6b8d9e10'
down_revision: Union[str, Sequence[str], None] = '7498f41deef6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_GRANTS = {
    'can_create_role': 'role:can_create_role',
    'can_create_group': 'role:can_create_group',
    'can_manage_server': 'role:can_manage_server',
    'can_publish_realtime_events': 'role:can_publish_realtime_events',
    'can_manage_session': 'role:can_manage_session',
}
PERMISSION_GRANTS = {
    'can_upload_mission': 'group:can_upload_mission',
    'can_test_mission': 'group:can_test_mission',
}


def _grant_concat_sql(grants: dict[str, str]) -> str:
    return ' || '.join(f"CASE WHEN {column} IS TRUE THEN '{grant},' ELSE '' END" for column, grant in grants.items())


def _contains_grant_sql(grant: str) -> str:
    return f"lower(',' || grants || ',') LIKE '%,{grant},%'"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user_roles', sa.Column('grants', sa.Text(), nullable=True))
    op.add_column('group_permissions', sa.Column('grants', sa.Text(), nullable=True))

    op.execute(f"UPDATE user_roles SET grants = rtrim({_grant_concat_sql(ROLE_GRANTS)}, ',')")
    op.execute(f"UPDATE group_permissions SET grants = rtrim({_grant_concat_sql(PERMISSION_GRANTS)}, ',')")

    op.alter_column('user_roles', 'grants', nullable=False)
    op.alter_column('group_permissions', 'grants', nullable=False)

    with op.batch_alter_table('user_roles') as batch_op:
        for column in ROLE_GRANTS:
            batch_op.drop_column(column)

    with op.batch_alter_table('group_permissions') as batch_op:
        for column in PERMISSION_GRANTS:
            batch_op.drop_column(column)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('user_roles') as batch_op:
        for column in ROLE_GRANTS:
            batch_op.add_column(sa.Column(column, sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table('group_permissions') as batch_op:
        for column in PERMISSION_GRANTS:
            batch_op.add_column(sa.Column(column, sa.Boolean(), nullable=False, server_default=sa.false()))

    for column, grant in ROLE_GRANTS.items():
        op.execute(f"UPDATE user_roles SET {column} = CASE WHEN {_contains_grant_sql(grant)} THEN TRUE ELSE FALSE END")
    for column, grant in PERMISSION_GRANTS.items():
        op.execute(f"UPDATE group_permissions SET {column} = CASE WHEN {_contains_grant_sql(grant)} THEN TRUE ELSE FALSE END")

    op.drop_column('group_permissions', 'grants')
    op.drop_column('user_roles', 'grants')
