class NotFoundError(Exception):
    pass


class PipelineError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class BadRequestError(Exception):
    pass


class SideEffectError(Exception):
    pass
