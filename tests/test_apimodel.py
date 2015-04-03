from unittest import TestCase
import json

import responses

from apimodel import APICollection, APIModel, NotFound

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

    def test_can_not_instantiate(self):
        self.assertRaises(NotImplementedError, self.model)


class DescribeAPICollection(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collection = APICollection

    def test_should_have_empty_finders(self):
        self.assertEqual(self.collection.finders, {})

    def test_should_have_null_model(self):
        self.assertIsNone(self.collection.model)

    def test_can_not_instantiate(self):
        self.assertRaises(NotImplementedError, self.collection)


class Candy(APIModel):
    fields = {
        'candy_id': str,
    }


class Egg(APIModel):
    fields = {
        'egg_id': str,
    }
    finders = {
        'basket_id': SERVER_BASKET_URL,
    }


class Basket(APIModel):
    finders = {
        'basket_id': SERVER_BASKET_URL,
    }

    fields = {
        'basket_id': str,
        'candies': ['Candy'],
        'eggs': [Egg],
        'egg': Egg,
        'empty': str,
    }


class EggCollection(APICollection):
    url = 'http://example.com/v1/eggs/'
    model = Egg


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
        self.assertIsInstance(self.model.candies[0], Candy)
        self.assertEqual(self.model.candies[0].candy_id,
                         'mycandy')

    @responses.activate
    def test_populates_collections_from_urls(self):
        responses.add(responses.GET, SERVER_EGG_URL.format('organic'),
                      body=SERVER_EGG_JSON_1, content_type='application/json')
        responses.add(responses.GET, SERVER_EGG_URL.format('regular'),
                      body=SERVER_EGG_JSON_2, content_type='application/json')
        self.assertIsInstance(self.model.eggs[0], Egg)
        self.assertIsInstance(self.model.eggs[1], Egg)
        self.assertIn(self.model.eggs[0].egg_id, ['organic', 'regular'])


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
        self.model.eggs
        self.assertEqual(len(responses.calls), 1)
        self.model.eggs[0]
        self.assertEqual(len(responses.calls), 1)
        self.model.eggs[0].egg_id
        self.assertEqual(len(responses.calls), 2)
        self.model.eggs[1]
        self.assertEqual(len(responses.calls), 2)
        self.model.eggs[1].egg_id
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
        import logging
        logging.error(SERVER_BASKET_SEARCH_URL.format('myid2'))
        responses.add(responses.GET, SERVER_BASKET_SEARCH_URL.format('myid2'),
                      body=json.dumps([]),
                      content_type='application/json')
        cls.collection = BasketCollection(basket_id='myid2')

    def test_should_have_models(self):
        self.assertEqual(len(self.collection.all()), 0)

    def test_first_should_return_none(self):
        model = self.collection.first()
        self.assertIsNone(model)
