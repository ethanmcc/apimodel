import requests
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


class NotFound(BaseException):
    pass


class APIModel(object):
    finders = {}
    fields = {}

    def __init__(self, data=None, **kwargs):
        if data:
            if urlparse(str(data)).scheme != '':
                self.load_data(data)
            else:
                self._data = data
        elif not self.finders:
            raise NotImplementedError
        else:
            for key in kwargs:
                if key in self.finders:
                    self.load_data(self.finders[key].format(kwargs[key]))
                    break
            else:
                raise ValueError('No finders for provided keys')

    def load_data(self, url):
        response = requests.get(url)
        if response.status_code != 200:
            raise NotFound(
                'Received status code {0}'.format(response.status_code))
        try:
            self._data = response.json()
        except ValueError:
            raise ValueError('Invalid JSON in response: {0}'.format(
                response.content))

    def __getattr__(self, field):
        if field in self.fields:
            type_ = self.fields[field]
            if isinstance(type_, list):
                collection_type = type_[0]
                return [collection_type(i) for i in self._data.get(field, [])]
            return type_(self._data.get(field, None))
        else:
            raise AttributeError
