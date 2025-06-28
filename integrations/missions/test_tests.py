# ruff: noqa: F811, F401

import pytest
from sqlalchemy import select

from bw.error import NoReviewFound, CouldNotCreateTestResult, CouldNotCosignResult
from bw.models.missions import Review
from bw.missions.tests import TestStore
from bw.missions.test_status import TestStatus, Review as IterationReview
from integrations.missions.fixtures import (
    state,
    session,
    db_mission_type_1,
    db_mission_type_2,
    db_user_1,
    db_mission_1,
    db_iteration_1,
    db_iteration_2,
    db_review_1,
    db_test_result_1,
    db_review_2,
    db_user_2,
    db_test_result_2,
    db_test_result_1_2,
)


def test__test_store__create_review__can_create_review(state, session, db_user_1):
    review = TestStore().create_review(state, db_user_1, TestStatus.PASSED, {'briefing': 'i understand now'})

    assert review.tester_id == db_user_1.id
    assert review.status == TestStatus.PASSED
    assert review.notes == {'briefing': 'i understand now'}

    with state.Session.begin() as session:
        query = select(Review).where(Review.id == review.id)
        row = session.execute(query).first()
        assert row is not None


def test__test_store__change_review_status__can_change_status(
    state, session, db_user_1, db_review_1, db_iteration_1, db_test_result_1
):
    TestStore().change_review_status(state, db_user_1, db_iteration_1, TestStatus.FAILED)
    with state.Session.begin() as session:
        query = select(Review).where(Review.id == db_review_1.id)
        review = session.execute(query).one()[0]
        assert review.status == TestStatus.FAILED


def test__test_store__change_review_status__no_review_fails(state, session, db_user_1, db_review_1, db_iteration_1):
    with pytest.raises(NoReviewFound):
        TestStore().change_review_status(state, db_user_1, db_iteration_1, TestStatus.FAILED)


def test__test_store__create_result__can_create_result(state, session, db_iteration_1, db_review_1):
    result = TestStore().create_result(state, db_iteration_1, db_review_1)

    assert result.review_id == db_review_1.id
    assert result.iteration_id == db_iteration_1.id

    with state.Session.begin() as session:
        query = select(Review).where(Review.id == result.review_id)
        row = session.execute(query).first()
        assert row is not None


def test__test_store__create_result__duplicate_fails(state, session, db_iteration_1, db_iteration_2, db_review_1):
    TestStore().create_result(state, db_iteration_1, db_review_1)
    with pytest.raises(CouldNotCreateTestResult):
        TestStore().create_result(state, db_iteration_2, db_review_1)


def test__test_store__create_result__review_maps_to_single_iteration(state, session, db_iteration_1, db_iteration_2, db_review_1):
    TestStore().create_result(state, db_iteration_1, db_review_1)
    with pytest.raises(CouldNotCreateTestResult):
        TestStore().create_result(state, db_iteration_2, db_review_1)


def test__test_store__cosign_result__can_cosign_result(state, session, db_user_2, db_test_result_1):
    cosign = TestStore().cosign_result(state, db_user_2, db_test_result_1)

    assert cosign.tester_id == db_user_2.id
    assert cosign.test_result_id == db_test_result_1.id

    with state.Session.begin() as session:
        query = select(Review).where(Review.id == cosign.test_result_id)
        row = session.execute(query).first()
        assert row is not None


def test__test_store__cosign_result__cant_cosign_own_result(state, session, db_user_1, db_test_result_1):
    with pytest.raises(CouldNotCosignResult):
        TestStore().cosign_result(state, db_user_1, db_test_result_1)


def test__test_store__cosign_result__cant_cosign_twice(state, session, db_user_2, db_test_result_1):
    TestStore().cosign_result(state, db_user_2, db_test_result_1)
    with pytest.raises(CouldNotCosignResult):
        TestStore().cosign_result(state, db_user_2, db_test_result_1)


def test__test_store__remove_cosign__can_remove_cosign(state, session, db_user_2, db_test_result_1):
    TestStore().cosign_result(state, db_user_2, db_test_result_1)
    TestStore().remove_cosign(state, db_user_2, db_test_result_1)

    with state.Session.begin() as session:
        query = select(Review).where(Review.id == db_test_result_1.id)
        row = session.execute(query).first()
        assert row is not None


def test__test_store__remove_cosign__removing_non_existing_cosign_no_error(state, session, db_user_2, db_test_result_1):
    TestStore().remove_cosign(state, db_user_2, db_test_result_1)


def test__test_store__iteration_reviews__returns_all_reviews(
    state, session, db_iteration_1, db_review_1, db_review_2, db_test_result_1, db_test_result_1_2, db_user_1, db_user_2
):
    reviews = TestStore().iteration_reviews(state, db_iteration_1)

    assert len(reviews) == 2
    assert reviews[0].status == TestStatus.PASSED
    assert reviews[0].notes == db_review_1.notes
    assert reviews[0].original_tester_id == db_user_1.id
    assert len(reviews[0].cosign_ids) == 0

    assert reviews[1].status == TestStatus.FAILED
    assert reviews[1].notes == db_review_2.notes
    assert reviews[1].original_tester_id == db_user_2.id
    assert len(reviews[1].cosign_ids) == 0


def test__test_store__iteration_reviews__returns_cosigns(
    state, session, db_iteration_1, db_review_1, db_review_2, db_test_result_1, db_user_1, db_user_2
):
    TestStore().cosign_result(state, db_user_2, db_test_result_1)
    reviews = TestStore().iteration_reviews(state, db_iteration_1)

    assert len(reviews) == 1
    assert reviews[0].status == TestStatus.PASSED
    assert reviews[0].notes == db_review_1.notes
    assert reviews[0].original_tester_id == db_user_1.id
    assert len(reviews[0].cosign_ids) == 1
    assert reviews[0].cosign_ids[0] == db_user_2.id


def test__test_store__remove_cosign__removes_cosign_from_iteration_reviews(
    state, session, db_iteration_1, db_review_1, db_review_2, db_test_result_1, db_test_result_1_2, db_user_1, db_user_2
):
    TestStore().cosign_result(state, db_user_2, db_test_result_1)
    TestStore().remove_cosign(state, db_user_2, db_test_result_1)

    reviews = TestStore().iteration_reviews(state, db_iteration_1)

    assert len(reviews) == 2
    assert reviews[0].status == TestStatus.PASSED
    assert reviews[0].notes == db_review_1.notes
    assert reviews[0].original_tester_id == db_user_1.id
    assert len(reviews[0].cosign_ids) == 0

    assert reviews[1].status == TestStatus.FAILED
    assert reviews[1].notes == db_review_2.notes
    assert reviews[1].original_tester_id == db_user_2.id
    assert len(reviews[1].cosign_ids) == 0
