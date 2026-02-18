from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from bw.auth.types import DiscordSnowflake
from bw.server_ops.arma.types import WorkshopId


class Base(DeclarativeBase):
    type_annotation_map = {DiscordSnowflake: String, WorkshopId: String}
