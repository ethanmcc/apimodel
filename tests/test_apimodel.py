from unittest import TestCase
from unittest.mock import Mock
import json

import responses

from apimodel import APICollection, APIModel, NotFound, \
    APIField, APIModelField, APICollectionField

SERVER_BASKET_URL = 'http://example.com/v1/baskets/{0}/'
# TODO: responses does not support mocking querystring requests
SERVER_BASKET_SEARCH_URL = 'http://example.com/v1/baskets/basket_id={0}'
SERVER_EGG_URL = 'http://example.com/v1/eggs/{0}/'
SERVER_EGG_COLLECTION_URL = 'http://example.com/v1/eggs/'
BASKET1_DATA = {
    'basket_id': 'myid',
    'eggs': [
        SERVER_EGG_URL.format('organic'),
        SERVER_EGG_URL.format('regular'),
    ],
    'candies': [
        {
            'candy_id': 'mycandy',
        }
    ],
    'egg': SERVER_EGG_URL.format('organic'),
    'empty': None,
}
BASKET2_DATA = BASKET1_DATA.copy()
BASKET2_DATA['basket_id'] = 'myid2'
SERVER_BASKET_JSON = json.dumps(BASKET1_DATA)
SERVER_EGG_JSON_1 = json.dumps({'egg_id': 'organic'})
SERVER_EGG_JSON_2 = json.dumps({'egg_id': 'regular'})
SERVER_EGG_COLLECTION = json.dumps([
    {'egg_id': 'organic'},
    {'egg_id': 'regular'},
])
SERVER_EMPTY_EGG_COLLECTION = json.dumps([])
SERVER_BASKET2_COLLECTION = json.dumps([BASKET2_DATA])


class DescribeAPIModel(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = APIModel

    def test_should_have_empty_finders(self):
        self.assertEqual(self.model.finders, {})

    def test_should_have_empty_fields(self):
        self.assertEqual(self.model.fields, {})


class DescribeAPICollection(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collection = APICollection

    def test_should_have_empty_finders(self):
        self.assertEqual(self.collection.finders, {})

    def test_should_have_null_model(self):
        self.assertIsNone(self.collection.model)


class Candy(APIModel):
    fields = {
        'candy_id': APIField(str),
    }


class Egg(APIModel):
    fields = {
        'egg_id': APIField(str),
        'basket_id': APIField(str),
    }

    finders = {
        'basket_id': SERVER_BASKET_URL,
    }


class Basket(APIModel):
    finders = {
        'basket_id': SERVER_BASKET_URL,
    }

    fields = {
        'basket_id': APIField(str),
        'candies': APICollectionField(model=Candy),
        'eggs': APICollectionField(model=Egg),
        'egg': APIModelField(model=Egg),
        'empty': APIField(str),
    }


class CandyCollection(APICollection):
    model = Candy


class BetterBasket(APIModel):
    finders = {
        'basket_id': SERVER_BASKET_URL,
    }

    fields = {
        'basket_id': APIField(str),
        'candies': APICollectionField(model=Candy),
        'eggs': APICollectionField(
            model=Egg,
            url='%sbasket_id={0.basket_id}' % SERVER_EGG_COLLECTION_URL,
        ),
        'egg': APIModelField(model=Egg),
        'empty': APIField(str),
    }


class BasketCollection(APICollection):
    finders = {
        'basket_id': SERVER_BASKET_SEARCH_URL,
    }

    model = Basket


class DescribeSubclassAPIModel(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = Basket

    def test_can_not_be_instantiated_with_no_args(self):
        self.assertRaises(ValueError, self.model)


class EggCollection(APICollection):
    url = 'http://example.com/v1/eggs/'
    model = Egg

    def test_can_not_be_instantiated_with_invalid_key(self):
        self.assertRaises(ValueError, self.model, jawn='turkey')

    @responses.activate
    def test_can_not_be_instantiated_with_bad_value(self):
        responses.add(responses.GET, SERVER_BASKET_URL.format('123'),
                      status=404, content_type='application/json')
        self.assertRaises(NotFound, self.model, basket_id=123)

    @responses.activate
    def test_can_be_instantiated_with_good_value(self):
        responses.add(responses.GET, SERVER_BASKET_URL.format('myid'),
                      body=SERVER_BASKET_JSON, content_type='application/json')
        self.assertIsInstance(self.model(basket_id='myid'), self.model)

    def test_can_be_instantiated_with_data(self):
        model = self.model(dict(basket_id='myid'))
        self.assertIsInstance(model, self.model)
        self.assertEqual(model.basket_id, 'myid')

    def test_can_handle_null_value(self):
        model = self.model(dict(basket_id='myid'))
        self.assertIsNone(model.empty)


class DescribeBadJSONRequest(TestCase):
    @responses.activate
    def test_can_not_be_instantiated_with_bad_json_response(self):
        responses.add(responses.GET, SERVER_BASKET_URL.format('myid'),
                      body=' ', content_type='application/json')
        self.assertRaises(ValueError, Basket, basket_id='myid')


class DescribeSubclassInstance(TestCase):
    @classmethod
    @responses.activate
    def setUpClass(cls):
        responses.add(responses.GET, SERVER_BASKET_URL.format('myid'),
                      body=SERVER_BASKET_JSON, content_type='application/json')
        cls.model = Basket(basket_id='myid')

    def test_does_not_populate_undefined_attributes(self):
        try:
            self.model.jawn
        except AttributeError:
            pass
        else:
            self.assert_(False, 'should not have undefined attributes')

    def test_populates_defined_attributes(self):
        self.assertEqual(self.model.basket_id, 'myid')

    def test_populates_collections(self):
        self.assertIsInstance(self.model.candies.first(), Candy)
        self.assertEqual(self.model.candies.first().candy_id, 'mycandy')

    @responses.activate
    def test_populates_collections_from_urls(self):
        responses.add(responses.GET, SERVER_EGG_URL.format('organic'),
                      body=SERVER_EGG_JSON_1, content_type='application/json')
        responses.add(responses.GET, SERVER_EGG_URL.format('regular'),
                      body=SERVER_EGG_JSON_2, content_type='application/json')
        self.assertIsInstance(self.model.eggs.first(), Egg)
        self.assertIsInstance(self.model.eggs.all()[1], Egg)
        self.assertIn(self.model.eggs.first().egg_id, ['organic', 'regular'])


class DescribeRequestBehavior(TestCase):
    @responses.activate
    def test_one_response_given(self):
        responses.add(responses.GET, SERVER_BASKET_URL.format('myid'),
                      body=SERVER_BASKET_JSON, content_type='application/json')
        self.model = Basket(basket_id='myid')
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_caches_individual_attributes(self):
        responses.add(responses.GET, SERVER_BASKET_URL.format('myid'),
                      body=SERVER_BASKET_JSON, content_type='application/json')
        responses.add(responses.GET, SERVER_EGG_URL.format('organic'),
                      body=SERVER_EGG_JSON_1, content_type='application/json')
        self.model = Basket(basket_id='myid')
        self.assertEqual(len(responses.calls), 1)
        self.model.egg.egg_id
        self.assertEqual(len(responses.calls), 2)
        self.model.egg.egg_id
        self.assertEqual(len(responses.calls), 2)

    @responses.activate
    def test_lazy_loading_of_collections(self):
        responses.add(responses.GET, SERVER_BASKET_URL.format('myid'),
                      body=SERVER_BASKET_JSON, content_type='application/json')
        responses.add(responses.GET, SERVER_EGG_URL.format('organic'),
                      body=SERVER_EGG_JSON_1, content_type='application/json')
        responses.add(responses.GET, SERVER_EGG_URL.format('regular'),
                      body=SERVER_EGG_JSON_2, content_type='application/json')
        self.model = Basket(basket_id='myid')
        self.assertEqual(len(responses.calls), 1)
        self.model.eggs.first()
        self.assertEqual(len(responses.calls), 1)
        self.model.eggs.first().egg_id
        self.assertEqual(len(responses.calls), 2)
        self.model.eggs.all()[1]
        self.assertEqual(len(responses.calls), 2)
        self.model.eggs.all()[1].egg_id
        self.assertEqual(len(responses.calls), 3)


    @responses.activate
    def test_lazy_loading_of_collections_starting_with_all(self):
        responses.add(responses.GET, SERVER_BASKET_URL.format('myid'),
                      body=SERVER_BASKET_JSON, content_type='application/json')
        responses.add(responses.GET, SERVER_EGG_URL.format('organic'),
                      body=SERVER_EGG_JSON_1, content_type='application/json')
        responses.add(responses.GET, SERVER_EGG_URL.format('regular'),
                      body=SERVER_EGG_JSON_2, content_type='application/json')
        self.model = Basket(basket_id='myid')
        self.assertEqual(len(responses.calls), 1)
        self.model.eggs.all()
        self.assertEqual(len(responses.calls), 3)


class DescribeCollectionInstance(TestCase):
    @classmethod
    @responses.activate
    def setUpClass(cls):
        responses.add(responses.GET, SERVER_EGG_COLLECTION_URL,
                      body=SERVER_EGG_COLLECTION,
                      content_type='application/json')
        cls.collection = EggCollection()

    def test_should_have_models(self):
        models = self.collection.all()
        self.assertEqual(len(models), 2)
        for model in models:
            self.assertIsInstance(model, Egg)

    def test_first_should_return_model(self):
        model = self.collection.first()
        self.assertIsInstance(model, Egg)


class DescribeEmptyCollectionInstance(TestCase):
    @classmethod
    @responses.activate
    def setUpClass(cls):
        responses.add(responses.GET, SERVER_EGG_COLLECTION_URL,
                      body=SERVER_EMPTY_EGG_COLLECTION,
                      content_type='application/json')
        cls.collection = EggCollection()

    def test_first_should_return_none(self):
        model = self.collection.first()
        self.assertIsNone(model)


class DescribeCollectionWithFinder(TestCase):
    @classmethod
    @responses.activate
    def setUpClass(cls):
        responses.add(responses.GET, SERVER_BASKET_SEARCH_URL.format('myid2'),
                      body=SERVER_BASKET2_COLLECTION,
                      content_type='application/json')
        cls.collection = BasketCollection(basket_id='myid2')

    def test_should_have_models(self):
        self.assertEqual(len(self.collection.all()), 1)

    def test_first_should_return_model(self):
        model = self.collection.first()
        self.assertIsInstance(model, Basket)


class DescribeEmptyCollectionWithFinder(TestCase):
    @classmethod
    @responses.activate
    def setUpClass(cls):
        responses.add(responses.GET, SERVER_BASKET_SEARCH_URL.format('myid2'),
                      body=json.dumps([]),
                      content_type='application/json')
        cls.collection = BasketCollection(basket_id='myid2')

    def test_should_have_models(self):
        self.assertEqual(len(self.collection.all()), 0)

    def test_first_should_return_none(self):
        model = self.collection.first()
        self.assertIsNone(model)


class DescribeModelWithCollectionFinderAndEmptyCollection(TestCase):
    @classmethod
    @responses.activate
    def setUpClass(cls):
        responses.add(responses.GET,
                      SERVER_BASKET_URL.format('myid2'),
                      json=BASKET2_DATA)
        responses.add(responses.GET,
                      '{}basket_id=myid2'.format(SERVER_EGG_COLLECTION_URL),
                      body=json.dumps([]),
                      content_type='application/json')
        cls.model = BetterBasket(basket_id='myid2')
        cls.eggs = cls.model.eggs.all()
        cls.egg = cls.model.eggs.first()

    def test_should_have_models(self):
        self.assertEqual(len(self.eggs), 0)

    def test_first_should_return_none(self):
        self.assertIsNone(self.egg)


class DescribeModelWithCollectionFinderAndCollection(TestCase):
    @classmethod
    @responses.activate
    def setUpClass(cls):
        responses.add(responses.GET,
                      SERVER_BASKET_URL.format('myid2'),
                      json=BASKET2_DATA)
        responses.add(responses.GET,
                      '{}basket_id=myid2'.format(SERVER_EGG_COLLECTION_URL),
                      body=SERVER_EGG_COLLECTION,
                      content_type='application/json')
        cls.model = BetterBasket(basket_id='myid2')
        cls.eggs = cls.model.eggs.all()
        cls.egg = cls.model.eggs.first()

    def test_should_have_models(self):
        self.assertEqual(len(self.eggs), 2)

    def test_first_should_return_none(self):
        self.assertEqual(self.egg.egg_id, 'organic')


class BaseTestAPIField(TestCase):
    field_class = APIField
    data = None
    wrapper_func = Mock()

    @classmethod
    @responses.activate
    def setUpClass(cls):
        cls.configure()
        cls.execute()

    @classmethod
    def configure(cls):
        pass

    @classmethod
    def execute(cls):
        cls.field = cls.field_class(wrapper_func=cls.wrapper_func)
        cls.result = cls.field.load(cls.data)


class BaseTestAPIModelField(BaseTestAPIField):

    @classmethod
    def execute(cls):
        cls.field = cls.field_class(model=cls.wrapper_func)
        cls.result = cls.field.load(cls.data)


class BaseTestAPICollectionField(BaseTestAPIField):

    @classmethod
    def execute(cls):
        cls.field = cls.field_class(model=cls.wrapper_func,
                                    url=SERVER_EGG_COLLECTION_URL)
        cls.result = cls.field.load(cls.data)


class DescribeEmptyAPIField(BaseTestAPIField):
    def test_should_return_none(self):
        self.assertIsNone(self.result)


class DescribeNonEmptyAPIField(BaseTestAPIField):
    data = b'hello'

    def test_should_return_string(self):
        self.assertEqual(self.result, self.wrapper_func.return_value)

    def test_wrapper_is_called(self):
        self.wrapper_func.assertCalledOnceWith(self.data)


class DescribeEmptyAPIModelField(BaseTestAPIModelField):
    field_class = APIModelField
    wrapper_func = Egg

    def test_should_return_none(self):
        self.assertIsNone(self.result)


class DescribeInvalidAPIModelField(TestCase):
    field_class = APIModelField
    wrapper_func = object

    def test_should_fail(self):
        self.assertRaises(
            TypeError, self.field_class, model=self.wrapper_func)


class DescribeNonEmptyAPIModelField(BaseTestAPIModelField):
    field_class = APIModelField
    data = json.loads(SERVER_EGG_JSON_2)
    wrapper_func = Egg

    def test_should_return_model(self):
        self.assertIsInstance(self.result, Egg)

    def test_should_return_egg(self):
        self.assertEqual(self.result.egg_id, self.data['egg_id'])


class DescribeEmptyAPICollectionField(BaseTestAPICollectionField):
    field_class = APICollectionField
    wrapper_func = Egg

    @classmethod
    def configure(cls):
        responses.add(responses.GET, SERVER_EGG_COLLECTION_URL,
                      body=SERVER_EMPTY_EGG_COLLECTION,
                      content_type='application/json')

    def test_should_return_none(self):
        self.assertEqual(self.result.all(), [])


class DescribeInvalidAPICollectionField(TestCase):
    field_class = APICollectionField
    wrapper_func = object

    def test_should_fail(self):
        self.assertRaises(
            TypeError, self.field_class, model=self.wrapper_func)


class DescribeNonEmptyAPICollectionField(BaseTestAPICollectionField):
    field_class = APICollectionField
    data = json.loads(SERVER_EGG_COLLECTION)
    wrapper_func = Egg

    @classmethod
    def configure(cls):
        responses.add(responses.GET, SERVER_EGG_COLLECTION_URL,
                      body=SERVER_EGG_COLLECTION,
                      content_type='application/json')

    def test_should_return_collection(self):
        self.assertIsInstance(self.result, APICollection)

    def test_result(self):
        self.assertEqual(self.result.first().egg_id, self.data[0]['egg_id'])
