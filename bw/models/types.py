import sqlalchemy.types as types
import sqlalchemy.engine as engine
import nh3


class HtmlSafeString(types.TypeDecorator):
    impl = types.String

    def process_bind_param(self, value: str | None, dialect: engine.Dialect) -> str | None:
        if value is None:
            return None

        return nh3.clean(value)

    def process_result_value(self, value: str | None, dialect: engine.Dialect) -> str | None:
        if value is None:
            return None

        return nh3.clean(value)
