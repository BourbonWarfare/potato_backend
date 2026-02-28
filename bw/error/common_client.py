from bw.error.base import ClientError


class BadArguments(ClientError):
    def __init__(self):
        super().__init__('Arguments are invalid')


class BadHeader(ClientError):
    def __init__(self):
        super().__init__('A malformed header parameter exists')


class MismatchedArguments(ClientError):
    def __init__(self, expected_keys=[], extra_keys=[]):
        if expected_keys == [] and extra_keys == []:
            raise BadArguments()
        elif expected_keys == [] and extra_keys != []:
            super().__init__(f'Extra keys supplied: {"', '".join(extra_keys)}')
        elif expected_keys != [] and extra_keys == []:
            super().__init__(f'Keys expected but not supplied: {", ".join(expected_keys)}')
        else:
            super().__init__(
                f'Keys expected but not supplied: {", ".join(expected_keys)}. Extra keys supplied: {", ".join(extra_keys)}'
            )


class ExpectedJson(ClientError):
    def status(self) -> int:
        return 415

    def __init__(self):
        super().__init__('Expected JSON payload, got something else')


class JsonPayloadError(ClientError):
    def __init__(self):
        super().__init__('JSON payload malformed')


class UploadError(ClientError):
    def status(self) -> int:
        return 422

    def __init__(self, reason: str):
        super().__init__(f'Something went wrong with the upload: {reason}')


class MissionDoesNotHaveMetadata(UploadError):
    def __init__(self):
        super().__init__('mission does not have attached mission testing attributes')
