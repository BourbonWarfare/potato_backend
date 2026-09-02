from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.exc import NoResultFound

from bw.error import RemarkDoesNotExist
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
            query = (
                update(RemarkDb)
                .where(
                    RemarkDb.user_id == None, RemarkDb.steam_id == remark.steam_id, RemarkDb.profile_name == remark.profile_name
                )
                .values(user_id=user.id, nickname=remark.nickname, remark=remark.remark)
                .returning(RemarkDb)
            )

            try:
                session.scalars(query).one()
            except NoResultFound:
                session.add(
                    RemarkDb(
                        user_id=user.id,
                        profile_name=remark.profile_name,
                        steam_id=remark.steam_id,
                        nickname=remark.nickname,
                        remark=remark.remark,
                    )
                )

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
            remarks = session.scalars(select(RemarkDb)).fetchall()
            return tuple(
                Remark(profile_name=remark.profile_name, nickname=remark.nickname, steam_id=remark.steam_id, remark=remark.remark)
                for remark in remarks
            )
