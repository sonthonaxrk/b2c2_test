# B2C2 Exercise

This is my [Rollo's] attempt at this task.

However, I refuse to do technical tests if I do not get anything out of it myself.
The way I see it, this is my personal development time.

I realise I haven't quite followed the test requirements to the letter as I did not
create what can be stricly called a CLI, but more like a command line GUI that runs
in IPython. I just thought that would be more useful demonstration of skills and ideas
than a while loop with an input function. And from a product pespective, I think this
would be more useful.

## Quickstart

Create a new virtual environment

	$ pip install "./path/to/zip[gui,dev]"

This should install a Jupyter extension. This helps improve the UX. If in doubt:

	$ jupyter nbextension install b2c2/b2c2_jupyter_extension.js
	$ jupyter nbextension enable b2c2_jupyter_extension

You can pass the authentication token to the client with an environment variable:

	$ export B2C2_APIKEY="key"

You can also pass it into the client like so, but throws a warning discouraging you from doing so:

	$ client = B2C2APIClient(env.uat, api_key="abc")

Launch Jupyter:

	# GUI Examples
	$ jupyter notebook example.ipynb


## Running tests

Because this is a package for local installation I am using tox.

To run the tests:

	$ PYTHONPATH=$PWD tox

## GUI

The GUI is based around some ideas I implemented for institutional clients previously.
I found that mixing the GUI and the command line client tends to be well received. It
lowers the barrier for entry, and integrates with a data-scientist's main tool:
a Jupyter notebook.

Open up the instrument selector, and create a quote. Everything returned is and API
object. The nice display properties are done with IPython hooks. In Jupyter they have
GUIs, while in IPython they rely on the `__repr__` method.

Things are updated live as objects are created. This relied on `asyncio`.

#### Instrument Selector

This allows you to select instruments and create quotes (monitors from the websocket wasn't implemented).

![Selector](https://gist.githubusercontent.com/sonthonaxrk/01a0428bd318e477686d21a8b3135534/raw/a658fb3a0186fd842b91f657cc4721ac7c672ed1/instument_selector.png)

Creating a quote will add `quote` into the IPython namespace, and if the Jupyter extension is running, it will be automatically displayed.

All GUI objects are normal Python objects and have methods that allow to action their current state (corresponding to their buttons). For example:

	In  [1]: selector = client.gui.instrument_selector()
	Out [1]:
			... display gui...
			
	In  [2]: request_for_quote = selector.request_for_quote()
	Out [2]: 
			... display request for quote ...

#### Quote

Quotes are normal `b2c2.model.Quote` class.

![Quote](https://gist.githubusercontent.com/sonthonaxrk/01a0428bd318e477686d21a8b3135534/raw/a658fb3a0186fd842b91f657cc4721ac7c672ed1/quote.png)

The quote API has one method that corresponds to the button:

	quote.execute_trade()

Both the button and method will raise a subclass of `B2C2ClientException` if the quote is expired.

#### History

![History](https://gist.githubusercontent.com/sonthonaxrk/01a0428bd318e477686d21a8b3135534/raw/a658fb3a0186fd842b91f657cc4721ac7c672ed1/history.png)

This is a reflection of the `client.history` object.  This will be updated when you create a quote or a trade.
It is not a singleton, and can be created many times (asyncio pubsub).

#### Balance

![Balance](https://gist.github.com/sonthonaxrk/01a0428bd318e477686d21a8b3135534/raw/463ca97272f195c2e37393b87dd95be6f1bd4775/balances.png)

This is a reflection of your balances. It will poll the API for updates, while also listening to the stream of new trades that you make using the current client.

#### Monitors

There's a button on the instrument selector that doesn't do anything. I didn't quite
have the time to implement the time series websocket monitor. I only wrote the
websocket client.

## API Usage

Methods are generated automatically from a specification and take pydantic objects



	from b2c2.exceptions import B2C2ClientException
	from b2c2.models import SideEnum, RequestForQuote, Instrument
	from b2c2.client import B2C2APIClient, env

	client = B2C2APIClient(env.uat)

	rfq = RequestForQuote(
	    instrument='BTCNZD.SPOT',
	    quantity='1',
	    side=SideEnum.buy,
	    client_rfq_id=None
	)

	# Errors example
	try:
	    quote = client.post_request_for_quote(rfq)
	except B2C2ClientException:
	    pass
		
	trade = quote.execute_trade()
	
	
#### Client Object

To provide a custom environment and API key:

	client = B2C2APIClient(
		{
			'rest_api': 'https://mycustomapi/',
			'websocket': 'wss://customwebsocket/path',
		},
		api_key='key'
	)



## Websocket API

I did write a websocket API that works quite well and pretty much implements all
of it's functionality. This was going to be for the monitor GUI element.

I paid close attention to usability, memory management, and concurrency. Please do take
a look at `websocket.py`.

Usage:

	ws_client = B2C2WebsocketClient(client)

	loop = asyncio.get_event_loop()


	sub = QuoteSubscribeFrame(**{
	    "event": "subscribe",
	    "instrument": "BTCUSD.SPOT",
	    "levels": [1, 3],
	})


	async def tradable_instruments():
	    async with ws_client.tradable_instruments.stream() as stream:
		async for frame in stream:
		    # stream of instruments
		    pass


	async def quote_subscribe():
	    # Note: if multiple async tasks try to subscribe to the same
	    # quote stream, the same object will be returned by different
	    # context managers. Preventing concurrency issues.
	    async with ws_client.quote_subscribe(sub) as fanout:
	    	# Fanouts are objects that provide a stream based pub-sub 
		async with fanout.stream() as stream:
		    async for frame in stream:
			# stream of quotes
			pass


	async def listen():
	    async with ws_client.connect() as ws:
		asyncio.ensure_future(tradable_instruments())
		asyncio.ensure_future(quote_subscribe())
		await ws.listen()


	loop.run_until_complete(listen())


## Logging

It's really hard to get a default setup that works in Jupyter nicely. But I've left
loggers under the namespace 'b2c2'.


To activate:

	import logging
	logger = logging.getLogger('b2c2')
	logger.setLevel(logging.DEBUG)
	logger.addHandler(logging.StreamHandler())


Server logging is just as important for client side products. Which is why I include
a unique request ID (which I would log using a `logging.Formatter`); and the version
string.


## Why is the API client so complicated?

In this exercise I tried to solve a few different problems that pertain to IPC between
microservices; namely these:

1. API clients are repetitive to build;

2. People frequently use OpenAPI as documentation rather than a formal specification;

3. It is difficult to enforce formal specifications in Python without expensive runtime checking.

Some companies have developed in-house tools to solve these problems. For example,
Google developed ProtocolBuffers and GRPC to solve these issues. But the developer
experience is poor when using Python.

My API client's base-class automatically creates typed methods from a pseudo-OpenAPI
definition. This uses a formal definition of an API to save time. However MyPy will not
work with dynamically created classes; and for MyPy to recognise metaprogramming, a
plug-in is needed (this is how dataclasses, attrs, and ctypes are supported in MyPy).

With this plug-in you can use static analysis to verify you are using the API
correctly (as long as the OpenAPI specification is correct).
