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
    """A Python :class:`ValueError` error occurred."""


class SyncanoRequestError(SyncanoException):
    """An HTTP error occurred.

    :ivar status_code: HTTP status code e.g: 404
    :ivar reason: Error text representation
    """

    def __init__(self, status_code, reason, *args):
        self.status_code = status_code

        if isinstance(reason, dict):
            joined_details = (''.join(reason.get(k, '')) for k in ['detail', 'error', '__all__'])
            message = ''.join(joined_details)

            if not message:
                for name, value in six.iteritems(reason):
                    if isinstance(value, (list, dict)):
                        value = ', '.join(value)
                    message += '{0}: {1}\n'.format(name, value)
            reason = message

        super(SyncanoRequestError, self).__init__(reason, *args)

    def __repr__(self):
        return '{0} {1}'.format(self.status_code, self.reason)

    def __str__(self):
        return '{0} {1}'.format(self.status_code, self.reason)


class SyncanoValidationError(SyncanoValueError):
    """A validation error occurred."""


class SyncanoFieldError(SyncanoValidationError):
    """A field error occurred.

    :ivar field_name: Related field name
    """
    field_name = None

    def __repr__(self):
        return '{0}: {1}'.format(self.field_name, self.reason)

    def __str__(self):
        return '{0}: {1}'.format(self.field_name, self.reason)


class SyncanoDoesNotExist(SyncanoException):
    """Syncano object doesn't exist error occurred."""


class RevisionMismatchException(SyncanoRequestError):
    """Revision do not match with expected one"""
