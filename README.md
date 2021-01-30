# B2C2 Exercise

This is my [Rollo's] attempt at this task.

However, I refuse to do technical tests if I do not get anything out of it myself.
The way I see it, this is my personal development time.

I realize I haven't followed the test requirements to the letter, as I did not
create what can be strictly called a CLI, but more like a command-line GUI that runs
in IPython. I just thought that would be a more useful demonstration of skills, ideas,
and product development.

## Quickstart

Create a new virtual environment

	$ pip install "./path/to/zip[gui,dev]"

This should install a Jupyter extension. This helps improve the UX. If in doubt:

	$ jupyter nbextension install b2c2/b2c2_jupyter_extension.js
	$ jupyter nbextension enable b2c2_jupyter_extension

You can pass the authentication token to the client with an environment variable:

	$ export B2C2_APIKEY="key"

You can also pass it into the client like so, but throws a warning discouraging you from doing so:

	$ client = B2C2APIClient(env.uat, api_key="ABC")

Launch Jupyter:

	# GUI Examples
	$ jupyter notebook example.ipynb

## Recommended IPython Setting

I  strongly recommend setting your IPython to automatically print all expressions in cells. By setting
the config:


	# ipython_kernel_config.py
	c.InteractiveShell.ast_node_interactivity = 'last_expr_or_assign'

This file can be found in the folder:

	$ ipython locate profile
	/Users/rollokonig-brock/.ipython/profile_default

If you need help: https://ipython.org/ipython-doc/stable/config/intro.html

## Running tests

Because this is a package for local installation I am using tox.

To run the tests:

	$ PYTHONPATH=$PWD tox

## GUI

The GUI is based on some ideas I implemented for institutional clients previously.
I found that mixing the GUI and the command line client tends to be well received. It
lowers the barrier for entry, and integrates with a data-scientist's main tool:
a Jupyter notebook.

Open up the instrument selector, and create a quote. Everything returned is an API object. The nice display properties are done with IPython hooks. In Jupyter they have
GUIs, while in IPython they rely on the `__repr__` method.

Things are updated live as objects are created. This relied on `asyncio`.

#### Instrument Selector

This allows you to select instruments and create quotes (monitors from the WebSocket wasn't implemented).

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

Quotes are a `b2c2.model.Quote` class.

![Quote](https://gist.githubusercontent.com/sonthonaxrk/01a0428bd318e477686d21a8b3135534/raw/a658fb3a0186fd842b91f657cc4721ac7c672ed1/quote.png)

The quote API has one method that corresponds to the button:

	quote.execute_trade()

Both the button and method will raise a subclass of `B2C2ClientException` if the quote is expired.

#### History

![History](https://gist.githubusercontent.com/sonthonaxrk/01a0428bd318e477686d21a8b3135534/raw/a658fb3a0186fd842b91f657cc4721ac7c672ed1/history.png)

This is a reflection of the `client.history` object.  This will be updated when you create a quote or a trade.
It is not a singleton and can be created many times (asyncio pubsub).

#### Balance

![Balance](https://gist.github.com/sonthonaxrk/01a0428bd318e477686d21a8b3135534/raw/463ca97272f195c2e37393b87dd95be6f1bd4775/balances.png)

This is a reflection of your balances. It will poll the API for updates, while also listening to the stream of new trades that you make using the current client.

#### Monitors

There's a button on the instrument selector that doesn't do anything. I didn't quite
have the time to implement the time series WebSocket monitor. I only wrote the
WebSocket client.

## API Usage

Methods are generated automatically from a specification and take `pydantic` objects



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

I did write a WebSocket API that works quite well and pretty much implements all
of its functionality. This was going to be for the monitor GUI element.

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
loggers under the namespace 'b2c2'. However I have included lots of warnings, which are
better for user feedback as they can be configured to show only once, on the first time
they happen.


To activate:

	import logging
	logger = logging.getLogger('b2c2')
	logger.setLevel(logging.DEBUG)
	logger.addHandler(logging.StreamHandler())


#### Server Side Logging and tracing

Server logging is just as important for client-side products. This is why I include
a unique request ID (which I would log using a `logging.Formatter`); and the version
string, in the headers of the HTTP and Websocket requests.


## Why is the API client so complicated?

In this exercise, I tried to solve a few different problems that pertain to IPC between
microservices; namely these:

1. API clients are repetitive to build;

2. People frequently use OpenAPI as documentation rather than a formal specification;

3. It is difficult to enforce formal specifications in Python without expensive runtime checking.

Some companies have developed in-house tools to solve these problems. For example,
Google developed ProtocolBuffers and GRPC to solve these issues. But the developer
experience is poor when using Python.

My API client's base-class automatically creates typed methods from a pseudo-OpenAPI
definition. This uses a formal definition of an API to save time. However MyPy will not
work with dynamically created classes; and for MyPy to recognize metaprogramming, a
plug-in is needed (this is how data classes, attrs, and ctypes are supported in MyPy).

With this plug-in you can use static analysis to verify you are using the API correctly (as long as the OpenAPI specification is correct).


# Ways I would improve this

This is the first time I used ipywigets like this, and the first time I used asyncio (In previous projects I tended to use eventlets because of asyncio's immature ecosystem). I have also taken a break from programming for a few months, so I was a bit rusty.

### Logging

The logging can be improved. Loggers should have been preconfigured to write to a file that logs the client identifier (perhaps part of the API key), and requests should log the request_id.

### Error handling

I think error handling for the RESTful operations is okay. Raising HTTP errors is generally enough for application developers. Errors also contain the raw error response object for introspection.

I also implemented decent error handling for the WebSocket client, that relies on `future.set_exeception()`.

However, error handling on the GUI is poor. I probably should have written an error dialogue, and I should have caught more possible errors. Async tasks erroring out is also poorly handled (Partly because developing with AsyncIO in Jupyter was quite difficult - as the event loop runs in a different context to your cell).

### Testing

I would add more tests, specifically GUI tests. Now that I am more familiar with AsyncIO, Jupyter, and IPywidgets, I would use test driven development (like I did for the api and websocket clients) to build the GUI.

### Improving the GUI API and UX

One problem is the GUI's reliance on globals. This can be a problem because the notebook will have an ephemeral state. On reflection, if I had not already submitted this test, I would make the GUI action methods asynchronous, allowing you to do something like this:


	In  [1]:
	
	async def quote_selection_workflow():
		instrument_selector = client.gui.instrument_selector()

		while True:
			# Set the cell output to the instrument selector
			display(instrument_selector)
			
			# Wait for user input
			quote = await instrument_selector.request_for_quote()
			
			# Now set the input to the quote
			
			if is_quote_all_good(quote):
				quote.execute()
			else:
				# Something is wrong with the quote
				# give the user some time to review it
				display(quote)
				await quote.expiry_or_execution()
				
			# Rinse and repeat
			
	await quote_selection_workflow()
	
	Out [1]:
	
		.... result of display...
		

This would constitute GUI building blocks that can be composed into workflows for traders. Something that I think could be really useful.
