import importlib

import requests


try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


class NotFound(BaseException):
    pass


class APIResource(object):
    finders = {}
    collection_finders = {}
    url = None

    def __init__(self, data=None, lazy_load=False, **kwargs):
        if lazy_load:
            self._lazy_load = {'data': data, 'kwargs': kwargs}
        else:
            self._lazy_load = False
            self._parse_inputs(data, kwargs)

    def _parse_inputs(self, data, kwargs):
        if data:
            if urlparse(str(data)).scheme != '':
                self._load_data(data)
            else:
                self._data = data
        elif not kwargs and self.url:
            self._load_data(self.url)
        elif not self.finders:
            raise NotImplementedError
        else:
            for key in kwargs:
                if key in self.finders:
                    self._load_data(self.finders[key].format(kwargs[key]))
                    break
            else:
                raise ValueError('No finders for provided keys')

    def _load_data(self, url):
        response = requests.get(url)
        if response.status_code != 200:
            raise NotFound(
                'Received status code {0}'.format(response.status_code))
        try:
            self._data = response.json()
        except ValueError:
            raise ValueError('Invalid JSON in response: {0}'.format(
                response.content))

    @staticmethod
    def _get_submodel_lazily(type_, data):
        if data is None:
            result = None
        elif issubclass(type_, APIModel):
            result = type_(data, lazy_load=True)
        else:
            result = type_(data)
        return result


class APICollection(APIResource):
    model = None

    def __init__(self, model=None, *args, **kwargs):
        if model:
            self.model = model
        super(APICollection, self).__init__(*args, **kwargs)

    def _do_lazy_load(self):
        if self._lazy_load:
            self._parse_inputs(**self._lazy_load)
            self._lazy_load = False
        if not hasattr(self, '_models'):
            self._models = [
                self.model(data=d, lazy_load=True) for d in self._data]

    def all(self):
        self._do_lazy_load()
        return self._models

    def first(self):
        self._do_lazy_load()
        if self._models:
            return self._models[0]


class APIModel(APIResource):
    fields = {}

    def __getattr__(self, field):
        if self._lazy_load:
            self._parse_inputs(**self._lazy_load)
            self._lazy_load = False

        if field in self.fields:
            type_ = self._string_to_class(self.fields[field])
            if isinstance(type_, APICollection) or \
                    issubclass(type_, APICollection):
                if field in self.collection_finders:
                    result = type_(
                        data=self.collection_finders[field].format(self),
                        lazy_load=True,
                    )
                else:
                    data = self._data.get(field, [])
                    if isinstance(type_, APICollection):
                        result = APICollection(model=type_.model, data=data,
                                               lazy_load=True)
                    else:
                        result = type_(data=data, lazy_load=True)
            else:
                result = self._get_submodel_lazily(type_,
                                                   self._data.get(field, None))
            setattr(self, field, result)
            return result
        else:
            raise AttributeError

    def _string_to_class(self, type_):
        if isinstance(type_, str):
            try:
                mod = importlib.import_module(self.__module__)
                type_ = getattr(mod, type_)
            except Exception:
                raise ValueError(
                    'Unable to find class "{0}"'.format(type_))
        return type_
