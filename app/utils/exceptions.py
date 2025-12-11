class AppError(Exception):
    """Base application exception."""
    pass


class NotFoundError(AppError):
    pass

