from unittest import TestCase
import json

import responses

from apimodel import APIModel, NotFound

SERVER_BASKET_URL = 'http://example.com/v1/baskets/{0}/'
SERVER_EGG_URL = 'http://example.com/v1/eggs/{0}/'
SERVER_BASKET_JSON = json.dumps({
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
})
SERVER_EGG_JSON_1 = json.dumps({'egg_id': 'organic'})
SERVER_EGG_JSON_2 = json.dumps({'egg_id': 'regular'})


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
    }


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

