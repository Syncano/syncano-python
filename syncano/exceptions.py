import six


class SyncanoException(Exception):
    """
    General Syncano client exception
    """

    def __init__(self, reason=None, *args):
        super(SyncanoException, self).__init__(reason, *args)
        self.reason = reason

    def __repr__(self):
        return self.reason

    def __str__(self):
        return self.reason


class SyncanoValueError(SyncanoException):
    pass


class SyncanoRequestError(SyncanoException):

    def __init__(self, status_code, reason, *args):
        self.status_code = status_code

        if isinstance(reason, dict):
            message = reason.get('detail', '') or reason.get('error', '')
            if not message:
                for name, erros in six.iteritems(reason):
                    message += "{0}: {1}\n".format(name, ', '.join(erros))
            reason = message

        super(SyncanoRequestError, self).__init__(reason, *args)

    def __repr__(self):
        return '{0} {1}'.format(self.status_code, self.reason)

    def __str__(self):
        return '{0} {1}'.format(self.status_code, self.reason)


class SyncanoValidationError(SyncanoValueError):
    pass


class SyncanoFieldError(SyncanoValidationError):
    field_name = None

    def __repr__(self):
        return '{0}: {1}'.format(self.field_name, self.reason)

    def __str__(self):
        return '{0}: {1}'.format(self.field_name, self.reason)


class SyncanoDoesNotExist(SyncanoException):
    pass
