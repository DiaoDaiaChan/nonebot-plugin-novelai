class AIDrawExceptions(BaseException):
    pass


class NoAvailableBackendError(AIDrawExceptions):
    pass


class PostingFailedError(AIDrawExceptions):
    pass

