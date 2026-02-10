from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from bw.auth.types import DiscordSnowflake


class Base(DeclarativeBase):
    type_annotation_map = {
        DiscordSnowflake: String,
    }
