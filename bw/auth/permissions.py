from dataclasses import dataclass


@dataclass(kw_only=True, slots=True)
class Permissions:
    can_upload_mission: bool
    can_test_mission: bool

    def as_dict(self) -> dict:
        return {slot: getattr(self, slot) for slot in self.__slots__}

    @staticmethod
    def from_many(*permissions):
        final = Permissions(**{slot: False for slot in Permissions.__slots__})
        for permission in permissions:
            for grant, value in permission.as_dict().items():
                current_value = getattr(final, grant)
                setattr(final, grant, current_value or value)
        return final
