

class ResultSet(object):

    def __init__(self, connection, data, cls=None):
        self.connection = connection
        self.data = data
        self.cls = cls

    def __iter__(self):
        pass
