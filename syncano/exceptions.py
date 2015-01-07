class SyncanoException(Exception):
    """
    General Syncano client exception
    """

    def __init__(self, reason, *args):
        super(SyncanoException, self).__init__(reason, *args)
        self.reason = reason

    def __repr__(self):
        return '%s: %s' % (self.__class__.__name__, self.reason)

    def __str__(self):
        return '%s: %s' % (self.__class__.__name__, self.reason)


class SyncanoValueError(SyncanoException):
    pass


class SyncanoRequestError(SyncanoException):

    def __init__(self, status_code, *args):
        self.status_code = status_code
        super(SyncanoRequestError, self).__init__(*args)

    def __repr__(self):
        return '%s: %d %s' % (
            self.__class__.__name__,
            self.status_code,
            self.reason
        )

    def __str__(self):
        return '%s: %d %s' % (
            self.__class__.__name__,
            self.status_code,
            self.reason
        )
