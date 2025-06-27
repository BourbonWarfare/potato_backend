class SlotCombiner:
    def as_dict(self) -> dict:
        return {slot: getattr(self, slot) for slot in self.__slots__}

    @classmethod
    def from_many(cls, *permissions):
        final = cls(**{slot: False for slot in cls.__slots__})
        for permission in permissions:
            for grant, value in permission.as_dict().items():
                current_value = getattr(final, grant)
                setattr(final, grant, current_value or value)
        return final
