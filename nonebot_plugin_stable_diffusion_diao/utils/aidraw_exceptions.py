__all__ = ("NoAvailableBackendError", "PostingFailedError", "AIDrawExceptions")


class AIDrawExceptions(BaseException):

    class NoAvailableBackendError(Exception):
        def __init__(self, message="没有可用后端"):
            super().__init__(message)

    class PostingFailedError(Exception):
        def __init__(self, message="Post服务器试出现错误"):
            super().__init__(message)






