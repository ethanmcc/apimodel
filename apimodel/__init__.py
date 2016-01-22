import importlib
import concurrent.futures
from functools import partial
from urllib.parse import urlparse

import requests


class NotFound(BaseException):
    pass


class APIResource(object):
    finders = {}
    url = None

    def __init__(self, data=None, lazy_load=False, **kwargs):
        if lazy_load:
            self._lazy_load = {'data': data, 'kwargs': kwargs}
        else:
            self._lazy_load = False
            self._parse_inputs(data, kwargs)

    def _parse_inputs(self, data, kwargs):
        if data is not None:
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


class APICollection(APIResource):
    model = None

    def __init__(self, model=None, *args, **kwargs):
        if model:
            self.model = model
        super(APICollection, self).__init__(*args, **kwargs)

    def create_model(self, data, lazy_load):
        return self.model(data=data, lazy_load=lazy_load)

    def _load(self, lazy_load):
        if self._lazy_load:
            self._parse_inputs(**self._lazy_load)
            self._lazy_load = False
        if not hasattr(self, '_models'):
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as e:
                create_model = partial(self.model, lazy_load=lazy_load)
                self._models = list(e.map(create_model, self._data))

    def all(self):
        self._load(lazy_load=False)
        return self._models

    def first(self):
        self._load(lazy_load=True)
        if self._models:
            return self._models[0]

    def count(self):
        if hasattr(self, '_models'):
            return len(self._models)
        elif hasattr(self, '_data') and isinstance(self._data, list):
            return len(self._data)
        else:
            return len(self.all())


class APIModel(APIResource):
    fields = {}

    def __getattr__(self, field_name):
        if self._lazy_load:
            self._parse_inputs(**self._lazy_load)
            self._lazy_load = False

        if field_name in self.fields:
            field = self.fields[field_name]
            data = self._data.get(field_name)
            result = field.load(data, self)
            setattr(self, field_name, result)
            return result
        else:
            raise AttributeError(
                'Field name {} not found in model'.format(field_name))


class APIField(object):
    def __init__(self, wrapper_func):
        self.wrapper_func = wrapper_func

    def load(self, data, parent=None):
        if data is not None:
            return self.wrapper_func(data)


class APIModelField(APIField):
    _type = APIModel

    def __init__(self, model):
        super().__init__(wrapper_func=model)

    def load(self, data, parent=None):
        self.wrapper_func = self._string_to_class(self.wrapper_func, parent)
        return super().load(data=data, parent=parent)

    def _string_to_class(self, type_, parent):
        if isinstance(type_, str):
            try:
                mod = importlib.import_module(parent.__module__)
                type_ = getattr(mod, type_)
            except Exception:
                raise ValueError(
                    'Unable to find class "{0}"'.format(type_))
        return type_


class APICollectionField(APIModelField):
    def __init__(self, model, url=None):
        self.url = url
        super().__init__(model=model)

    def load(self, data, parent=None):
        self.wrapper_func = self._string_to_class(self.wrapper_func, parent)
        if self.url:
            data = self.url.format(parent)
        return APICollection(model=self.wrapper_func, data=data)
