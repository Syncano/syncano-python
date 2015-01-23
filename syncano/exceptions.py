class SyncanoException(Exception):
    """
    General Syncano client exception
    """

    def __init__(self, reason, *args):
        super(SyncanoException, self).__init__(reason, *args)
        self.reason = reason

    def __repr__(self):
        return self.reason

    def __str__(self):
        return self.reason


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


class SyncanoValidationError(SyncanoValueError):
    pass


class SyncanoFieldError(SyncanoValidationError):

    def __init__(self, field_name, *args):
        self.field_name = field_name
        super(SyncanoFieldError, self).__init__(*args)

    def __repr__(self):
        return '{0}: {1}'.format(self.field_name, self.reason)

    def __str__(self):
        return '{0}: {1}'.format(self.field_name, self.reason)
