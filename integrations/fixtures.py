import alembic
import alembic.config
import pytest

from sqlalchemy import insert
from sqlalchemy.sql import text

from bw.state import State
from bw.auth.permissions import Permissions
from bw.models.auth import DiscordUser, BotUser, User, Session, GroupPermission, Group


@pytest.fixture(scope='session')
def token_1():
    return 'token 1'


@pytest.fixture(scope='session')
def token_2():
    return 'token 2'


@pytest.fixture(scope='session')
def discord_id_1():
    return 1


@pytest.fixture(scope='session')
def expire_valid():
    return '9999-12-23 02:11:06'


@pytest.fixture(scope='session')
def expire_invalid():
    return '1999-12-23 02:11:06'


@pytest.fixture(scope='session')
def permission_1() -> Permissions:
    return Permissions(can_test_mission=False, can_upload_mission=True)


@pytest.fixture(scope='session')
def permission_2() -> Permissions:
    return Permissions(can_test_mission=True, can_upload_mission=False)


@pytest.fixture(scope='session')
def permission_3() -> Permissions:
    return Permissions(can_test_mission=False, can_upload_mission=False)


@pytest.fixture(scope='session')
def permission_name_1() -> str:
    return 'perm 1'


@pytest.fixture(scope='session')
def permission_name_2() -> str:
    return 'perm 2'


@pytest.fixture(scope='session')
def permission_name_3() -> str:
    return 'perm 3'


@pytest.fixture(scope='session')
def group_name_1() -> str:
    return 'group 1'


@pytest.fixture(scope='session')
def group_name_2() -> str:
    return 'group 2'


@pytest.fixture(scope='session')
def group_name_3() -> str:
    return 'group 3'


@pytest.fixture(scope='function')
def state():
    return State()


@pytest.fixture(scope='function')
def session(request, state):
    # Create a temporary DB to do tests in. Per-test
    alembic_cfg = alembic.config.Config(toml_file='./pyproject.toml')

    test_db_name = f'bw_integration__{request.node.name}'
    with state.Engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        conn.execute(text('COMMIT'))
        conn.execute(text(f'CREATE DATABASE {test_db_name}'))

    original_default = state.default_database
    state.register_database(test_db_name)
    state.default_database = test_db_name
    with state.Engine.connect() as session:
        alembic_cfg.attributes['connection'] = session
        alembic.command.upgrade(alembic_cfg, 'heads')
        yield session
    state.Engine.dispose()

    # Drop database; unneeded after test
    state.default_database = original_default
    with state.Engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        conn.execute(text('COMMIT'))
        conn.execute(text(f'DROP DATABASE {test_db_name}'))


@pytest.fixture(scope='function')
def non_db_user_1():
    user = User(id=1)
    yield user


@pytest.fixture(scope='function')
def db_user_1(state, session):
    with state.Session.begin() as session:
        query = insert(User).values(id=1).returning(User)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_user_2(state, session):
    with state.Session.begin() as session:
        query = insert(User).values(id=2).returning(User)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_session_1(state, session, db_user_1, token_1):
    with state.Session.begin() as session:
        query = insert(Session).values(id=1, user_id=db_user_1.id, token=token_1).returning(Session)
        user_session = session.execute(query).first()[0]
        session.expunge(user_session)
    yield user_session


@pytest.fixture(scope='function')
def db_discord_user_1(state, session, db_user_1, discord_id_1):
    with state.Session.begin() as session:
        query = insert(DiscordUser).values(id=1, user_id=db_user_1.id, discord_id=discord_id_1).returning(DiscordUser)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_bot_user_1(state, session, db_user_1, token_1):
    with state.Session.begin() as session:
        query = insert(BotUser).values(id=1, user_id=db_user_1.id, bot_token=token_1).returning(BotUser)
        user = session.execute(query).first()[0]
        session.expunge(user)
    yield user


@pytest.fixture(scope='function')
def db_permission_1(state, session, permission_1, permission_name_1):
    with state.Session.begin() as session:
        query = insert(GroupPermission).values(id=1, name=permission_name_1, **permission_1.as_dict()).returning(GroupPermission)
        perm = session.execute(query).first()[0]
        session.expunge(perm)
    yield perm


@pytest.fixture(scope='function')
def db_permission_2(state, session, permission_2, permission_name_2):
    with state.Session.begin() as session:
        query = insert(GroupPermission).values(id=2, name=permission_name_2, **permission_2.as_dict()).returning(GroupPermission)
        perm = session.execute(query).first()[0]
        session.expunge(perm)
    yield perm


@pytest.fixture(scope='function')
def db_permission_3(state, session, permission_3, permission_name_3):
    with state.Session.begin() as session:
        query = insert(GroupPermission).values(id=3, name=permission_name_3, **permission_3.as_dict()).returning(GroupPermission)
        perm = session.execute(query).first()[0]
        session.expunge(perm)
    yield perm


@pytest.fixture(scope='function')
def db_group_1(state, session, db_permission_1, group_name_1):
    with state.Session.begin() as session:
        query = insert(Group).values(id=1, name=group_name_1, permissions=db_permission_1.id).returning(Group)
        group = session.execute(query).first()[0]
        session.expunge(group)
    yield group


@pytest.fixture(scope='function')
def db_group_2(state, session, db_permission_2, group_name_2):
    with state.Session.begin() as session:
        query = insert(Group).values(id=2, name=group_name_2, permissions=db_permission_2.id).returning(Group)
        group = session.execute(query).first()[0]
        session.expunge(group)
    yield group


@pytest.fixture(scope='function')
def db_group_3(state, session, db_permission_3, group_name_3):
    with state.Session.begin() as session:
        query = insert(Group).values(id=3, name=group_name_3, permissions=db_permission_3.id).returning(Group)
        group = session.execute(query).first()[0]
        session.expunge(group)
    yield group
