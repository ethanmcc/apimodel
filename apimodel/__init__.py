import importlib

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

    def __init__(self, data=None, lazy_load=False, **kwargs):
        if lazy_load:
            self.lazy_load = {'data': data, 'kwargs': kwargs}
        else:
            self.lazy_load = False
            self.parse_inputs(data, kwargs)

    def parse_inputs(self, data, kwargs):
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

    def string_to_class(self, type_):
        if isinstance(type_, str):
            try:
                mod = importlib.import_module(self.__module__)
                type_ = getattr(mod, type_)
            except Exception:
                raise ValueError(
                    'Unable to find class "{0}"'.format(type_))
        return type_

    @staticmethod
    def get_submodels_lazily(type_, data):
        if issubclass(type_, APIModel):
            result = type_(data, lazy_load=True)
        else:
            result = type_(data)
        return result

    def __getattr__(self, field):
        if self.lazy_load:
            self.parse_inputs(self.lazy_load['data'], self.lazy_load['kwargs'])
            self.lazy_load = False

        if field in self.fields:
            type_ = self.string_to_class(self.fields[field])
            if isinstance(type_, list):
                collection_type = self.string_to_class(type_[0])
                collection = []
                for data in self._data.get(field, []):
                    collection.append(
                        self.get_submodels_lazily(collection_type, data))
                result = collection
            else:
                result = self.get_submodels_lazily(type_,
                                                   self._data.get(field, None))
            setattr(self, field, result)
            return result
        else:
            raise AttributeError
