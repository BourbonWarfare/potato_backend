# ruff: noqa: F811, F401

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from bw.auth.remarks import Remark, RemarkStore
from bw.error import RemarkDoesNotExist
from bw.models.auth import Remark as RemarkDb
from integrations.auth.fixtures import (
    db_unclaimed_remark_1,
    db_user_1,
    db_user_2,
    nickname_1,
    nickname_2,
    profile_name_1,
    profile_name_2,
    remark_1,
    remark_1_updated,
    remark_2,
    remark_no_nickname,
    remark_text_1,
    remark_text_2,
    steam_id_1,
    steam_id_2,
)

# Tests for update_remark


def test__update_remark__can_create_no_throw(state, db_user_1, remark_1):
    """Test that a brand new remark is written to the database with the expected fields."""
    RemarkStore().update_remark(state, db_user_1, remark_1)

    with state.Session.begin() as session:
        query = select(RemarkDb).where(RemarkDb.user_id == db_user_1.id)
        row = session.scalars(query).one()
        assert row.profile_name == remark_1.profile_name
        assert row.nickname == remark_1.nickname
        assert row.steam_id == remark_1.steam_id
        assert row.remark == remark_1.remark


def test__update_remark__can_create_with_null_nickname_and_remark(state, db_user_1, remark_no_nickname):
    """Test that nickname and remark are nullable and stored as such."""
    RemarkStore().update_remark(state, db_user_1, remark_no_nickname)

    with state.Session.begin() as session:
        query = select(RemarkDb).where(RemarkDb.user_id == db_user_1.id)
        row = session.scalars(query).one()
        assert row.nickname is None
        assert row.remark is None


def test__update_remark__claims_existing_unclaimed_remark(state, db_user_1, db_unclaimed_remark_1, remark_1_updated):
    """Test that submitting a remark matching an unclaimed row (user_id is null, same steam_id/profile_name)
    updates that same row in place rather than inserting a new one."""
    RemarkStore().update_remark(state, db_user_1, remark_1_updated)

    with state.Session.begin() as session:
        query = select(RemarkDb).where(
            RemarkDb.profile_name == remark_1_updated.profile_name, RemarkDb.steam_id == remark_1_updated.steam_id
        )
        rows = session.scalars(query).fetchall()
        assert len(rows) == 1
        assert rows[0].user_id == db_user_1.id
        assert rows[0].nickname == remark_1_updated.nickname
        assert rows[0].remark == remark_1_updated.remark


def test__update_remark__does_not_claim_row_with_different_profile_name(
    state, db_user_1, db_unclaimed_remark_1, steam_id_1, profile_name_2
):
    """Test that a mismatched profile_name means the unclaimed row is left alone and a new row is inserted."""
    mismatched_remark = Remark(profile_name=profile_name_2, nickname='someone else', steam_id=steam_id_1, remark=None)
    RemarkStore().update_remark(state, db_user_1, mismatched_remark)

    with state.Session.begin() as session:
        unclaimed_row = session.get(RemarkDb, (db_unclaimed_remark_1.profile_name, db_unclaimed_remark_1.steam_id))
        assert unclaimed_row.user_id is None

        new_row_query = select(RemarkDb).where(RemarkDb.user_id == db_user_1.id)
        new_row = session.scalars(new_row_query).one()
        assert new_row.profile_name == profile_name_2


def test__update_remark__does_not_claim_row_with_different_steam_id(
    state, db_user_1, db_unclaimed_remark_1, profile_name_1, steam_id_2
):
    """Test that a mismatched steam_id means the unclaimed row is left alone and a new row is inserted."""
    mismatched_remark = Remark(profile_name=profile_name_1, nickname='someone else', steam_id=steam_id_2, remark=None)
    RemarkStore().update_remark(state, db_user_1, mismatched_remark)

    with state.Session.begin() as session:
        unclaimed_row = session.get(RemarkDb, (db_unclaimed_remark_1.profile_name, db_unclaimed_remark_1.steam_id))
        assert unclaimed_row.user_id is None

        new_row_query = select(RemarkDb).where(RemarkDb.user_id == db_user_1.id)
        new_row = session.scalars(new_row_query).one()
        assert new_row.steam_id == steam_id_2


def test__update_remark__second_remark_for_different_profile_creates_new_row(state, db_user_1, remark_1, remark_2):
    """Test that leaving a remark on a second, different profile adds a row rather than overwriting the first."""
    RemarkStore().update_remark(state, db_user_1, remark_1)
    RemarkStore().update_remark(state, db_user_1, remark_2)

    with state.Session.begin() as session:
        query = select(RemarkDb).where(RemarkDb.user_id == db_user_1.id)
        rows = session.scalars(query).fetchall()
        assert len(rows) == 2
        steam_ids = {row.steam_id for row in rows}
        assert steam_ids == {remark_1.steam_id, remark_2.steam_id}


def test__update_remark__resubmitting_same_profile_updates_remark(state, db_user_1, remark_1, remark_1_updated):
    """Test that once a profile's remark has been claimed, submitting another remark for that same
    profile_name/steam_id/user.id updates that row.
    """
    RemarkStore().update_remark(state, db_user_1, remark_1)
    RemarkStore().update_remark(state, db_user_1, remark_1_updated)

    with state.Session.begin() as session:
        query = select(RemarkDb).where(
            RemarkDb.profile_name == remark_1_updated.profile_name, RemarkDb.steam_id == remark_1_updated.steam_id
        )
        rows = session.scalars(query).fetchall()
        assert len(rows) == 1
        assert rows[0].user_id == db_user_1.id
        assert rows[0].nickname == remark_1_updated.nickname
        assert rows[0].remark == remark_1_updated.remark


def test__update_remark__different_user_cannot_claim_already_claimed_profile(state, db_user_1, db_user_2, remark_1):
    """Test that once one user has claimed a profile's remark, a different user cannot also claim it."""
    RemarkStore().update_remark(state, db_user_1, remark_1)

    with pytest.raises(IntegrityError):
        RemarkStore().update_remark(state, db_user_2, remark_1)


def test__update_remark__does_not_affect_other_users_rows(state, db_user_1, db_user_2, remark_1, remark_2):
    """Test that each user's remark rows are independent."""
    RemarkStore().update_remark(state, db_user_1, remark_1)
    RemarkStore().update_remark(state, db_user_2, remark_2)

    with state.Session.begin() as session:
        row_1 = session.scalars(select(RemarkDb).where(RemarkDb.user_id == db_user_1.id)).one()
        row_2 = session.scalars(select(RemarkDb).where(RemarkDb.user_id == db_user_2.id)).one()
        assert row_1.steam_id == remark_1.steam_id
        assert row_2.steam_id == remark_2.steam_id


# Tests for user_remark


def test__user_remark__raises_when_no_remark(state, db_user_1):
    """Test that a user with no remarks raises RemarkDoesNotExist."""
    with pytest.raises(RemarkDoesNotExist):
        RemarkStore().user_remark(state, db_user_1)


def test__user_remark__does_not_return_unclaimed_remark(state, db_user_1, db_unclaimed_remark_1):
    """Test that an unclaimed row (user_id is null) is not returned as belonging to any user."""
    with pytest.raises(RemarkDoesNotExist):
        RemarkStore().user_remark(state, db_user_1)


def test__user_remark__returns_correct_remark(state, db_user_1, remark_1):
    """Test that the stored remark's fields are returned correctly."""
    RemarkStore().update_remark(state, db_user_1, remark_1)

    remark = RemarkStore().user_remark(state, db_user_1)
    assert remark == remark_1


def test__user_remark__returns_most_recently_created_remark(state, db_user_1, remark_1, remark_2):
    """Test that when a user has multiple remarks (on different profiles), the most recently created
    one is returned."""
    RemarkStore().update_remark(state, db_user_1, remark_1)
    RemarkStore().update_remark(state, db_user_1, remark_2)

    remark = RemarkStore().user_remark(state, db_user_1)
    assert remark == remark_2


def test__user_remark__isolated_per_user(state, db_user_1, db_user_2, remark_1):
    """Test that one user's remark is not visible to another user."""
    RemarkStore().update_remark(state, db_user_1, remark_1)

    with pytest.raises(RemarkDoesNotExist):
        RemarkStore().user_remark(state, db_user_2)


# Tests for all_remarks


def test__all_remarks__empty_database_returns_empty_tuple(state, session):
    """Test that all_remarks returns an empty tuple when no remarks exist."""
    remarks = RemarkStore().all_remarks(state)
    assert remarks == ()


def test__all_remarks__includes_unclaimed_remarks(state, db_unclaimed_remark_1):
    """Test that all_remarks includes rows with no associated user, unlike user_remark."""
    remarks = RemarkStore().all_remarks(state)
    assert len(remarks) == 1
    assert remarks[0].steam_id == db_unclaimed_remark_1.steam_id


def test__all_remarks__returns_remarks_for_multiple_users(state, db_user_1, db_user_2, remark_1, remark_2):
    """Test that remarks belonging to every user are returned."""
    RemarkStore().update_remark(state, db_user_1, remark_1)
    RemarkStore().update_remark(state, db_user_2, remark_2)

    remarks = RemarkStore().all_remarks(state)
    assert len(remarks) == 2
    assert remark_1 in remarks
    assert remark_2 in remarks


def test__all_remarks__reflects_claim_without_duplicating(state, db_user_1, db_unclaimed_remark_1, remark_1_updated):
    """Test that claiming an unclaimed remark is reflected in all_remarks without adding a new entry."""
    RemarkStore().update_remark(state, db_user_1, remark_1_updated)

    remarks = RemarkStore().all_remarks(state)
    assert remarks == (remark_1_updated,)
