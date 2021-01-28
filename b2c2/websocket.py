import websockets
import asyncio
import uuid
# This is a nice little pattern matching library
# (I hate if, elif, elif, chains with a passion)
import pampy

from weakref import WeakKeyDictionary, WeakSet
from contextlib import asynccontextmanager
from collections import defaultdict
from typing import Dict, Any, Optional

from b2c2.frames import (
    ErrorResponseFrame, TradableInstrumentsFrame, UsernameUpdateFrame,
    QuoteUnsubscribeResponseFrame, QuoteResponseFrame
)

# create a queue that can create subqueues
class Fanout:
    """
    This provides fan out functionality so that
    multiple objects can listen to an async websocket
    stream

    I don't really know the AsyncIO ecosystem that well
    and every time I take a look at it I get the sense
    it's still a bit immature. Something like this, while
    not in the standard library should have a well known
    library that does it. But I couldn't work out what to use.
    """

    def __init__(self, queue):
        self._queue = queue
        # Only the subscribing objects should
        # have a ref to the queue
        self._fanout_queues = WeakSet()
        self._fanout_task = None

    async def stream(self):
        if not self._fanout_task:
            self._fanout_task = (
                asyncio.create_task(self._fanout_job())
            )

        queue = asyncio.Queue()
        self._fanout_queues.add(queue)
        
        # tranforms a queue into an async generator
        async def _async_gen():
            while True:
                yield await queue.get()

        return _async_gen()

    async def _fanout_job(self):
        while True:
            frame = await self._queue.get()
            for queue in self._fanout_queues:
                queue.put_nowait(frame)

            # Because python is block scoped this
            # task will keep a reference to the single
            # queue that existed in the last fanout job

            # Unless we delete it
            del queue


class B2C2WebsocketClient:
    """
    These are the websocket frame types


        - tradable_instruments and tradable_instruments_update
        - username_update

    This is an obvious choice for a context manager:

        - subscribe - request
        - subscribe - stream response
        - unsubscribe - request
    """

    # just for testing
    _stream_terminate = object()

    # List of rules - paired (not the most readable API, but
    # it is a lot more readable, testable, and maintainable
    # than the if else statements).
    _frame_matching_rules = (
        # This pair is a matching rule. It will match
        # all dictionaries where success=False and the
        # error_code=Any. On match the lambda is called and returned
        {'success': False, 'error_code': Any},
        lambda _: ErrorResponseFrame,

        # Statements are checked in order (so check for errors first)
        {'event': 'tradable_instruments'},
        lambda _: TradableInstrumentsFrame,
        
        {'event': 'tradable_instruments_update'},
        lambda _: TradableInstrumentsFrame,

        {'event': 'username_update'},
        lambda _: UsernameUpdateFrame,

        {'event': 'unsubscribe', 'instrument': str},
        lambda _: QuoteUnsubscribeResponseFrame,

        {'event': 'price', 'instrument': str},
        lambda _: QuoteResponseFrame,
    )

    async def stream(self):
        # Turn the websocket into an async generator
        async with websockets.connect(
            'wss://echo.websocket.org'
        ) as ws:
            while True:
                yield await websocket.recv()

    async def listen(self):
        async for frame in self.stream():
            # Do some pattern matching and enque the message
            if frame == self._stream_terminate:
                break

            frame_cls = self._match_frame(frame)
            frame = frame_cls(**frame)
            callback = self._resp_callbacks[frame_cls]
            await callback(frame)

    def _match_frame(self, frame):
        return pampy.match(frame, *self._frame_matching_rules)

    def __init__(self, *args):
        self._resp_callbacks = WeakKeyDictionary([
            (TradableInstrumentsFrame, self._on_tradable_instrument),
            (UsernameUpdateFrame, self._on_username_update),
        ])

        self.tradable_instruments = Fanout(asyncio.Queue())
        self.username_updates = Fanout(asyncio.Queue())


    async def _on_tradable_instrument(self, frame: TradableInstrumentsFrame):
        await self.tradable_instruments._queue.put(frame)

    async def _on_username_update(self, frame: UsernameUpdateFrame):
        await self.username_updates._queue.put(frame)

    @asynccontextmanager
    async def subscribe(self, subscribe: QuoteSubscribeFrame):


