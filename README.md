# Python API-Backed Models

This is an API-backed, read-only model class inspired by [https://github.com/tarttelin/pyrestmodels](https://github.com/tarttelin/pyrestmodels). It was written using TDD, and will likely be ported or wrapped to behave like a Django model.

## Usage

Subclass `apimodel.APIModel`, define `fields` and `finders` attributes, the start instantiating models using keyword arguments that correspond with your `finders` keys.

### Example Endpoints
	
#### /v1/eggs/organic

	{
		"egg_id": "organic"
	}

#### /v1/eggs/regular

	{
		"egg_id": "regular"
	}
	
#### /v1/baskets/myid

	{
		"basket_id": "myid",
		"candies": [
			{"candy_id": "mycandy"}
		],
		"eggs": [
			"http://example.com/v1/eggs/organic/",
			"http://example.com/v1/eggs/regular/"
		]
	}
	
### Example Clases

#### Basic Model

This model has `fields` and `finder`s:

	class Egg(APIModel):
	"""Demo class with a finder."""		
    fields = {	
        'egg_id': str,	
    }	
    finders = {	
        'basket_id': 'http://example.com/v1/eggs/{0}/',	
    }

You can instantiate an egg using:

	>>> egg = Egg(egg_id='organic')
	
That will give you access to its fields:

	>>> print(egg.egg_id)
	organic

#### Structure-only Model
	
This class doesn't have `finder`s, but is used to instantiate Candy objects
from data that's included in collections inside the `Basket` model. This type of class is only useful for organizing data that you already have, either from a link in another endpoint or in your own code.
	
	class Candy(APIModel):
	"""Demo class with no finders.""" 	    
    fields	 = {
        'candy_id': str,
    }
	    
Without any `finders`, the only way to instantiate a structure-only model directly is by passing in data:

	>>> candy = Candy({'candy_id': 'nutrageous'})
	>>> print(candy.candy_id)
	nutrageous
	
#### Linked Model
	
	class Basket(APIModel):
	"""Demo class that links in Candy and Egg.
	
	Candy is linked using data provided from the baskets endpoint. Egg
	is retrieved by urls provided in the baskets endpoint.
			:
    finders = 	{
        'basket_id': 'http://example.com/v1/baskets/{0}/'	,
    	}	

    fields = 	{
        'basket_id': str	,
        'candies': [Candy]	,
        'eggs': [Egg],
   	}
	    
This class includes its own `basket_id` field, plus links to collections of basic and structure-only models. When I insantiate this model, it gives me access to the `Candy` objects that are defined within its JSON, and also to the `Egg` models, whose URLs are included in the JSON.

	>>> basket = Basket(basket_id='myid')
	>>> print(basket.candies)
	[<__main__.Candy at 0x10cec4650>]
	>>> print(basket.candies[0].candy_id)
	nutrageous
	>>> print(baseket.eggs[1].egg_id)
	regular

**Note:** Associated models are loaded lazily, so they don't make requests until
at least one of their attributes is accessed. Only one request will be made per 
instance per association. If your API doesn't change much, you can cache all your
requests easily using
[requests-cache](https://pypi.python.org/pypi/requests-cache).

## Testing

To run the tests, make sure you have [tox](https://tox.readthedocs.org/en/latest/) installed, as well as the appropriate Python versions (currently 2.7 and 3.4) installed on your machine. Then simply run `tox`.
