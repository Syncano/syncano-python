class AuthException(Exception):

    def __init__(self, value='Wrong authorization data'):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ApiException(Exception):

    def __init__(self, value):
        self.value = "Call Exception: " + repr(value)

    def __str__(self):
        return self.value


class ConnectionLost(Exception):

    def __init__(self, value='No connection to server'):
        self.value = "Connection lost: " + repr(value)

    def __str__(self):
        return self.value