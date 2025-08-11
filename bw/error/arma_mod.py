from bw.error.base import BwServerError, ClientError


class ArmaModError(BwServerError):
    def __init__(self, reason: str):
        super().__init__(f'An error occured with a mod: {reason}')


class ModNotDefined(ArmaModError):
    def __init__(self, mod_name: str):
        super().__init__(f'Mod "{mod_name}" is not defined in the configuration.')


class ModAlreadyDefined(ArmaModError):
    def __init__(self, mod_name: str):
        super().__init__(f'Mod "{mod_name}" is already defined.')


class ModMissingField(ArmaModError):
    def __init__(self, mod_name: str, field_name: str):
        super().__init__(f'Mod "{mod_name}" is missing required field "{field_name}".')


class ModFieldInvalid(ArmaModError):
    def __init__(self, mod_name: str, field_name: str, reason: str | None = None):
        if reason:
            super().__init__(f'Mod "{mod_name}" has invalid field "{field_name}": {reason}.')
        else:
            super().__init__(f'Mod "{mod_name}" is has invalid field field "{field_name}".')


class ModInvalidKind(ArmaModError):
    def __init__(self, mod_name: str, kind: str, valid_kinds: list[str]):
        super().__init__(f'Mod "{mod_name}" has invalid kind "{kind}". Must be one of {", ".join(valid_kinds)}.')


class DuplicateModWorkshopID(ArmaModError):
    def __init__(self, workshop_id: str, this_mod_name: str, original_mod_name: str):
        super().__init__(f'Mod "{this_mod_name}" has a workshop ID already defined by "{original_mod_name}" ({workshop_id}).')


class DuplicateModPath(ArmaModError):
    def __init__(self, mod_name: str, existing_mod: str, mod_path: str):
        super().__init__(f'"{mod_name}" has a path already defined by "{existing_mod}": {mod_path}.')


class ModStoreError(ClientError):
    def __init__(self, reason: str):
        super().__init__(f'Database operation failed: {reason}')


class ModAlreadyExists(ModStoreError):
    def status(self):
        return 409

    def __init__(self, workshop_id: int):
        super().__init__(f'Mod with workshop ID {workshop_id} already exists in the database.')


class ModCreationFailed(ModStoreError):
    def __init__(self, workshop_id: int):
        super().__init__(f'Failed to create mod record for workshop ID {workshop_id}.')


class ModNotFound(ModStoreError):
    def status(self):
        return 404

    def __init__(self, workshop_id: int):
        super().__init__(f'Mod with workshop ID {workshop_id} not found in the database.')
