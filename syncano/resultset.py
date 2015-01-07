

class ResultSet(object):

    def __init__(self, connection, data, **kwargs):
        self.connection = connection
        self.data = data or {}
        self.result_class = kwargs.get('result_class')
        self.request_method = kwargs.get('request_method')
        self.request_path = kwargs.get('request_path')
        self.request_params = kwargs.get('request_params') or {}

    def __repr__(self):
        return 'ResultSet for {0} {1}'.format(self.request_method, self.request_path)

    def __str__(self):
        return 'ResultSet for {0} {1}'.format(self.request_method, self.request_path)

    def __iter__(self):
        '''Pagination handler'''

        while True:
            objects = self.data.get('objects')
            next_url = self.data.get('next')
            for o in objects:
                yield self.result_class(**o) if self.result_class else o

            if not objects or not next_url:
                break

            self.data = self.connection.make_request(
                self.request_method,
                next_url,
                **self.request_params
            )
