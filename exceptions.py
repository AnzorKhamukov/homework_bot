class FailedConnection(Exception):
    pass


class ResponseDataError(Exception):
    ...


class WrongStatus(Exception):
    pass


class FormatError(Exception):
    ...


class ParsingError(Exception):
    ...
