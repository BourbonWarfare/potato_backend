from sqlalchemy import insert, delete, select
from sqlalchemy.exc import NoResultFound, IntegrityError

from bw.state import State
from bw.models.auth import User, Group, GroupPermission, UserGroup
from bw.error import GroupCreationFailed, GroupPermissionCreationFailed, NoGroupPermissionWithCredentials, GroupAssignmentFailed
from bw.auth.permissions import Permissions


class GroupStore:
    def create_permission(self, state: State, name: str, permissions: Permissions) -> GroupPermission:
        with state.Session.begin() as session:
            query = insert(GroupPermission).values(name=name, **permissions.as_dict()).returning(GroupPermission)
            try:
                group_permission = session.execute(query).one()[0]
            except IntegrityError:
                raise GroupPermissionCreationFailed(name)
            session.expunge(group_permission)
        return group_permission

    def create_group(self, state: State, group_name: str, permission_group: str) -> Group:
        try:
            permission = self.get_permission(state, permission_group)
        except NoGroupPermissionWithCredentials:
            raise GroupCreationFailed(group_name)

        with state.Session.begin() as session:
            query = insert(Group).values(name=group_name, permissions=permission.id).returning(Group)
            try:
                group = session.execute(query).one()[0]
            except IntegrityError:
                raise GroupCreationFailed(group_name)
            session.expunge(group)
        return group

    def get_permission(self, state: State, permission_name: str) -> GroupPermission:
        with state.Session.begin() as session:
            query = select(GroupPermission).where(GroupPermission.name == permission_name)
            try:
                permission = session.execute(query).one()[0]
            except NoResultFound:
                raise NoGroupPermissionWithCredentials(permission_name)
            session.expunge(permission)
        return permission

    def edit_permission(self, state: State, permission_name: str, permissions: Permissions) -> GroupPermission:
        with state.Session.begin() as session:
            query = select(GroupPermission).where(GroupPermission.name == permission_name)
            try:
                permission = session.execute(query).one()[0]
            except NoResultFound:
                raise NoGroupPermissionWithCredentials(permission_name)

            for grant, allowed in permissions.as_dict().items():
                setattr(permission, grant, allowed)

            session.flush()
            session.expunge(permission)
        return permission

    def assign_user_to_group(self, state: State, user: User, group: Group):
        with state.Session.begin() as session:
            query = insert(UserGroup).values(user_id=user.id, group_id=group.id)
            try:
                session.execute(query)
            except IntegrityError:
                raise GroupAssignmentFailed()

    def remove_user_from_group(self, state: State, user: User, group: Group):
        with state.Session.begin() as session:
            query = delete(UserGroup).where(UserGroup.user_id == user.id).where(UserGroup.group_id == group.id)
            session.execute(query)

    def delete_group(self, state: State, group_name: str):
        with state.Session.begin() as session:
            query = delete(UserGroup).where(Group.id == UserGroup.group_id).where(Group.name == group_name)
            session.execute(query)

            query = delete(Group).where(Group.name == group_name)
            session.execute(query)

    def get_all_permissions_user_has(self, state: State, user: User) -> Permissions:
        with state.Session.begin() as session:
            query = (
                select(GroupPermission)
                .join(Group)
                .where(Group.permissions == GroupPermission.id)
                .join(UserGroup)
                .where(UserGroup.group_id == Group.id)
                .where(UserGroup.user_id == user.id)
            )

            all_permissions = []
            for permission_group in session.execute(query).partitions():
                for permissions in permission_group:
                    all_permissions.extend([permission.into_permissions() for permission in permissions])
        return Permissions.from_many(*all_permissions)
