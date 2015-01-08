class SyncanoException(Exception):
    """
    General Syncano client exception
    """
    pass


class SyncanoValueError(SyncanoException):
    pass


class SyncanoRequestError(SyncanoException):

    def __init__(self, status_code, *args):
        self.status_code = status_code
        super(SyncanoRequestError, self).__init__(*args)

    def __repr__(self):
        return '{0} {1}'.format(self.status_code, self.reason)

    def __str__(self):
        return '{0} {1}'.format(self.status_code, self.reason)
