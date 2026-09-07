from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, NoResultFound

from bw.error import RemarkDoesNotExist, RemarkOwnedByDifferentUser
from bw.models.auth import Remark as RemarkDb
from bw.models.auth import User
from bw.state import State


@dataclass
class Remark:
    profile_name: str
    nickname: str | None
    steam_id: str
    remark: str | None


class RemarkStore:
    def update_remark(self, state: State, user: User, remark: Remark):
        with state.Session.begin() as session:
            base_query = (
                update(RemarkDb).values(user_id=user.id, nickname=remark.nickname, remark=remark.remark).returning(RemarkDb)
            )
            try:
                session.scalars(
                    base_query.where(
                        RemarkDb.user_id == None,
                        RemarkDb.steam_id == remark.steam_id,
                        RemarkDb.profile_name == remark.profile_name,
                    )
                ).one()
                return
            except NoResultFound:
                pass
            try:
                session.scalars(
                    base_query.where(
                        RemarkDb.user_id == user.id,
                        RemarkDb.steam_id == remark.steam_id,
                        RemarkDb.profile_name == remark.profile_name,
                    )
                ).one()
                return
            except NoResultFound:
                pass

            try:
                session.add(
                    RemarkDb(
                        user_id=user.id,
                        profile_name=remark.profile_name,
                        steam_id=remark.steam_id,
                        nickname=remark.nickname,
                        remark=remark.remark,
                    )
                )
            except IntegrityError:
                raise RemarkOwnedByDifferentUser()

    def user_remark(self, state: State, user: User) -> Remark:
        with state.Session.begin() as session:
            query = select(RemarkDb).where(RemarkDb.user_id == user.id).order_by(RemarkDb.creation_date.desc())
            remark = session.scalars(query).first()
            if not remark:
                raise RemarkDoesNotExist()

            return Remark(
                profile_name=remark.profile_name, nickname=remark.nickname, steam_id=remark.steam_id, remark=remark.remark
            )

    def all_remarks(self, state: State) -> tuple[Remark, ...]:
        with state.Session.begin() as session:
            query = select(RemarkDb).order_by(RemarkDb.creation_date.desc(), RemarkDb.profile_name.asc(), RemarkDb.nickname.asc())
            remarks = session.scalars(query).fetchall()
            return tuple(
                Remark(profile_name=remark.profile_name, nickname=remark.nickname, steam_id=remark.steam_id, remark=remark.remark)
                for remark in remarks
            )
