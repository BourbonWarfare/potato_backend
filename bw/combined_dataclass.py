from bw.error import MismatchedArguments


class SlotCombiner:
    def as_dict(self) -> dict:
        return {slot: getattr(self, slot) for slot in self.__slots__}

    @classmethod
    def from_keys(cls, default_if_key_not_present=None, **keys):
        expected_keys = [key for key in cls.__slots__ if key not in keys]
        extra_keys = [key for key in keys if key not in cls.__slots__]

        if default_if_key_not_present is not None and expected_keys != []:
            for key in expected_keys:
                keys[key] = default_if_key_not_present
            expected_keys = []

        if expected_keys != [] or extra_keys != []:
            raise MismatchedArguments(expected_keys=expected_keys, extra_keys=extra_keys)
        return cls(**keys)

    @classmethod
    def from_many(cls, *permissions):
        final = cls(**{slot: False for slot in cls.__slots__})
        for permission in permissions:
            for grant, value in permission.as_dict().items():
                current_value = getattr(final, grant)
                setattr(final, grant, current_value or value)
        return final
