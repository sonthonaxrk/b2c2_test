# B2C2 Exercise

This is my [Rollo's] attempt at this task.

However, I refuse to do technical tests if I do not get anything out of it myself.
The way I see it, this is my personal development time.


## Quickstart

Create a new virtual environment

	$ pip install "./path/to/zip[gui,dev]"

This should install a Jupyter extension. This helps improve the UX. If in doubt:

	$ jupyter nbextension install b2c2/b2c2_jupyter_extension.js
	$ jupyter nbextension enable b2c2_jupyter_extension

Launch Jupyter:

	# GUI Examplez
	$ jupyter notebook example.ipynb


## GUI Usage

Open up the instrument selector, and create a quote. Everything returned is and API
object. The nice display properties are done with IPython hooks.

Things are updated live as objects are created.

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


## Websocket API

I did write a websocket API that works quite well and pretty much implements all
of it's functionality.

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
	    async with ws_client.quote_subscribe(sub) as fanout:
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
loggers under the namespace 'b2c2'

To activate:

	import logging
	logger = logging.getLogger('b2c2')
	logger.setLevel(logging.DEBUG)
	logger.addHandler(logging.StreamHandler())


## The GUI

The GUI is based around some ideas I implemented for institutional clients previously.
I found that mixing the GUI and the command line client tends to be well received. It
lowers the barrier for entry, and integrates with a data-scientist's main tool:
a Jupyter notebook.


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
