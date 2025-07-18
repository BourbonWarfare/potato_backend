from uuid import UUID
from sqlalchemy import delete, select
from sqlalchemy.exc import NoResultFound, IntegrityError

from bw.state import State
from bw.models.auth import User
from bw.models.missions import Review, Iteration, TestResult, TestCosign
from bw.error import CouldNotCreateTestResult, CouldNotCosignResult, NoReviewFound, NoResultFound as NoTestResultFound
from bw.missions.test_status import TestStatus, Review as IterationReview


class TestStore:
    def create_review(self, state: State, tester: User, test_status: TestStatus, notes: dict) -> Review:
        """
        ### Create a new review for a mission iteration

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `tester` (`User`): The user performing the review.
        - `test_status` (`TestStatus`): The status of the test (e.g., passed, failed).
        - `notes` (`dict`): Additional notes for the review.

        **Returns:**
        - `Review`: The created review object.
        """
        with state.Session.begin() as session:
            review = Review(tester_id=tester.id, status=test_status, notes=notes)
            session.add(review)
            session.flush()
            session.expunge(review)
        return review

    def change_review_status(self, state: State, tester: User, iteration: Iteration, new_status: TestStatus):
        """
        ### Change the status of a review

        Changes the status of a review for a given tester and iteration.
        Raises `NoReviewFound` if no review exists for the tester and iteration.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `tester` (`User`): The user whose review status is to be changed.
        - `iteration` (`Iteration`): The mission iteration being reviewed.
        - `new_status` (`TestStatus`): The new status to set for the review.

        **Raises:**
        - `NoReviewFound`: If no review exists for the tester and iteration.
        """
        with state.Session.begin() as session:
            query = (
                select(Review)
                .join(TestResult, TestResult.review_id == Review.id)
                .where(Review.tester_id == tester.id)
                .where(TestResult.iteration_id == iteration.id)
            )
            try:
                review = session.execute(query).one()[0]
            except NoResultFound:
                raise NoReviewFound()
            review.status = new_status

    def create_result(self, state: State, iteration: Iteration, review: Review) -> TestResult:
        """
        ### Create a new test result

        Creates a new test result for a given iteration and review.
        Raises `CouldNotCreateTestResult` if a result cannot be created due to a constraint violation.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `iteration` (`Iteration`): The mission iteration being tested.
        - `review` (`Review`): The review associated with the test result.

        **Returns:**
        - `TestResult`: The created test result object.

        **Raises:**
        - `CouldNotCreateTestResult`: If a result cannot be created due to a constraint violation.
        """
        with state.Session.begin() as session:
            result = TestResult(review_id=review.id, iteration_id=iteration.id)
            try:
                session.add(result)
                session.flush()
            except IntegrityError:
                raise CouldNotCreateTestResult()
            session.expunge(result)
        return result

    def result_by_uuid(self, state: State, uuid: UUID) -> TestResult:
        """
        ### Retrieve existing test result via it's UUID

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `uuid` (`UUID`): The UUID a review may have.

        **Returns:**
        - `TestResult | None`: The test result, if the UUID is in the database; otherwise `None`.
        """
        with state.Session.begin() as session:
            query = select(TestResult).where(TestResult.uuid == uuid)
            try:
                review = session.execute(query).one()[0]
            except NoResultFound:
                raise NoTestResultFound()
            session.expunge(review)
        return review

    def cosign_result(self, state: State, tester: User, test_result: TestResult) -> TestCosign:
        """
        ### Add a cosign to a test result

        Adds a cosign to a test result by a tester.
        Raises `CouldNotCosignResult` if the tester is the original reviewer or if a cosign constraint is violated.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `tester` (`User`): The user cosigning the test result.
        - `test_result` (`TestResult`): The test result to cosign.

        **Returns:**
        - `TestCosign`: The created cosign object.

        **Raises:**
        - `CouldNotCosignResult`: If the tester is the original reviewer or a cosign constraint is violated.
        """
        if test_result.review_id == tester.id:
            raise CouldNotCosignResult()

        with state.Session.begin() as session:
            review = TestCosign(test_result_id=test_result.id, tester_id=tester.id)
            try:
                session.add(review)
                session.flush()
            except IntegrityError:
                raise CouldNotCosignResult()
            session.expunge(review)
        return review

    def remove_cosign(self, state: State, tester: User, test_result: TestResult):
        """
        ### Remove a cosign from a test result

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `tester` (`User`): The user whose cosign is to be removed.
        - `test_result` (`TestResult`): The test result from which to remove the cosign.
        """
        with state.Session.begin() as session:
            query = delete(TestCosign).where(TestCosign.tester_id == tester.id).where(TestCosign.test_result_id == test_result.id)
            session.execute(query)

    def iteration_reviews(self, state: State, iteration: Iteration) -> list[IterationReview]:
        """
        ### Retrieve all reviews and cosigns for a mission iteration

        Returns all reviews and cosigns for the reviews given a mission iteration.

        **Args:**
        - `state` (`State`): The application state containing the database connection.
        - `iteration` (`Iteration`): The mission iteration for which to retrieve reviews.

        **Returns:**
        - `list[IterationReview]`: A list of `IterationReview` objects containing review and cosign information.
        """
        with state.Session.begin() as session:
            query = (
                select(TestResult.id, TestResult.uuid, TestResult.date_tested, Review.status, Review.notes, Review.tester_id)
                .join(Review, TestResult.review_id == Review.id)
                .where(TestResult.iteration_id == iteration.id)
                .order_by(TestResult.date_tested.desc())
            )
            try:
                reviews = session.execute(query).all()
            except NoResultFound:
                return []

            iteration_reviews = []
            for result_id, result_uuid, date_tested, status, notes, tester in reviews:
                query = select(TestCosign.tester_id).where(TestCosign.test_result_id == result_id)
                try:
                    cosigns = [row[0] for row in session.execute(query).all()]
                except NoResultFound:
                    cosigns = []
                iteration_reviews.append(
                    IterationReview(
                        uuid=result_uuid,
                        date_tested=date_tested,
                        status=status,
                        notes=notes,
                        original_tester_id=tester,
                        cosign_ids=cosigns,
                    )
                )
        return iteration_reviews
