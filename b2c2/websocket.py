import websockets
import asyncio
import weakref
# This is a nice little pattern matching library
# (I hate if, elif, elif, chains with a passion)
import pampy
import logging

from weakref import WeakKeyDictionary, WeakValueDictionary, WeakSet
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any
from pydantic import BaseModel

from b2c2.frames import (
    ErrorResponseFrame, TradableInstrumentsFrame, UsernameUpdateFrame,
    # Clean up the names of these frames
    QuoteUnsubscribeFrame, QuoteUnsubscribeResponseFrame,
    QuoteStreamFrame,
    QuoteSubscribeFrame, QuoteSubscribeResponseFrame,
)

logger = logging.getLogger(__name__)


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

    @asynccontextmanager
    async def stream(self):
        async with self.queue() as queue:
            # tranforms a queue into an async generator
            async def _async_gen():
                while True:
                    yield await queue.get()  # noqa

            yield _async_gen()
            del _async_gen

    @asynccontextmanager
    async def queue(self):
        if not self._fanout_task:
            self._fanout_task = (
                asyncio.create_task(self._fanout_job())
            )

        queue = asyncio.Queue()
        self._fanout_queues.add(queue)
        yield queue
        del queue

    async def _fanout_job(self):
        while True:
            frame = await self._queue.get()

            queue = None

            for queue in self._fanout_queues:
                queue.put_nowait(frame)

            # Because python is block scoped this
            # task will keep a reference to the single
            # queue that existed in the last fanout job
            # Unless we delete it
            del queue  # noqa


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

        {'event': 'unsubscribe'},
        lambda _: QuoteUnsubscribeResponseFrame,

        {'event': 'price'},
        lambda _: QuoteStreamFrame,

        {'event': 'subscribe'},
        lambda _: QuoteSubscribeResponseFrame
    )

    @asynccontextmanager
    async def connect(self):
        async with self._websocket_connect as ws:
            self._websocket = ws
            yield self

    async def listen(self):
        async for frame in self.stream():
            frame_cls = self._match_frame(frame)
            frame = frame_cls(**frame)

            callback = self._resp_callbacks.get(frame_cls)
            logger.debug(
                'Incoming Frame %s', str(frame)
            )

            await callback(frame)

    def _match_frame(self, frame):
        return pampy.match(frame, *self._frame_matching_rules)

    def __init__(self, api_client):
        self._websocket_connect = websockets.connect(
            api_client.env['websocket'],
            extra_headers=api_client._get_headers()
        )

        self._websocket = None

        self._resp_callbacks = WeakKeyDictionary([
            (TradableInstrumentsFrame, self._on_tradable_instrument),
            (UsernameUpdateFrame, self._on_username_update),
            (QuoteStreamFrame, self._on_quote_price),
            # These all have tags - and should have corresponding
            # futures to resolve.
            (QuoteUnsubscribeResponseFrame, self._on_tag),
            (QuoteSubscribeResponseFrame, self._on_tag),
            (ErrorResponseFrame, self._on_tag),
        ])

        self.tradable_instruments = Fanout(asyncio.Queue())
        self.username_updates = Fanout(asyncio.Queue())
        self._pending_tags = {}

        # Quote subscription stuff
        self._instrument_fanouts = WeakValueDictionary()
        # Mapping between a instrument and a lock
        self._instrument_creation_locks = defaultdict(asyncio.Lock)
        self._instrument_deletion_locks = defaultdict(asyncio.Lock)

    async def _on_tradable_instrument(self, frame: TradableInstrumentsFrame):
        await self.tradable_instruments._queue.put(frame)

    async def _on_username_update(self, frame: UsernameUpdateFrame):
        await self.username_updates._queue.put(frame)

    async def _on_quote_price(self, frame: QuoteStreamFrame):
        fanout = self._instrument_fanouts[frame._key]
        await fanout._queue.put(frame)

    async def _on_tag(self, frame):
        # There should be two ways of resolving the
        # _quote_subscription_requests future.
        # One is a success response. But the
        # other can just be the frame (but should log
        # a warning).
        # Do tag first
        if frame.tag in self._pending_tags:
            future = self._pending_tags.pop(frame.tag)
            if isinstance(frame, ErrorResponseFrame):
                future.set_exception(frame.to_exception())
            else:
                future.set_result(frame)
        else:
            logger.error('No future for response frame')

    async def _send_frame(self, frame: BaseModel):
        await self._websocket.send(frame.json())

    async def _rpc_request(self, request_frame):
        # Send request
        await self._send_frame(request_frame)
        future_resp = asyncio.Future()
        # Add this to the subscription future registry
        self._pending_tags[request_frame.tag] = future_resp
        # Wait for it to be resolved by incoming frames
        return await future_resp

    @asynccontextmanager
    async def quote_subscribe(self, req: QuoteSubscribeFrame):
        """
        Takes a quote subscribe frame (a request) and yields
        an provides a fanout object which streams can be created
        from.

        The complexity of this function stems from the fact I
        do not know how multiple quote requests are handled by the
        websocket. Thus the locks and weird GC code.


        Example usage:

        .. code-block:: python

            async with B2C2WebsocketClient(WS_URL).connect() as client:
                async with client.quote_subscribe(quote) as fanout:
                    stream = await fanout.stream()
                    async for price_updates in stream:
                        print(price_updates)

        """
        # We don't want people making multiple requests
        # to do the same thing. We need to lock a particular
        # subscribe request.

        # as a note I made req: QuoteSubscribeFrame hashable
        request_lock = self._instrument_creation_locks[req._key]
        deletion_lock = self._instrument_deletion_locks[req._key]

        async def _unsub():
            # It's probably fine, but I don't want multiple
            # deletion requests happening at once.
            if not deletion_lock.locked():
                async with deletion_lock:
                    unsub = QuoteUnsubscribeFrame(instrument=req.instrument)
                    try:
                        await asyncio.wait_for(
                            self._rpc_request(unsub), 5
                        )
                    except asyncio.TimeoutError as e:
                        logger.error(
                            'Could not unsubscribe from quote.',
                            exc_info=e
                        )

        def _gc_fanout():
            # Called when the object is garbage collected
            asyncio.ensure_future(_unsub())

        if request_lock.locked():
            # something else is trying to subscribe
            await request_lock.acquire()
            # Let us wait until that's complete
            request_lock.release()

        # Return the fanout if it already exists
        if req._key in self._instrument_fanouts:
            # If it already exists it means there should
            # a reference to it (and will still be in our WeakRefs)
            yield self._instrument_fanouts[req._key]

        else:  # We need to create it
            async with request_lock:
                await self._rpc_request(req)

            # Because we can yield the same object multiple
            # times we should only cleanup when the object
            # is deferenced and GD'd
            fanout = self._instrument_fanouts[req._key] = Fanout(asyncio.Queue())  # noqa
            weakref.finalize(fanout, _gc_fanout)

            yield self._instrument_fanouts[req._key]
            # NOTE: This ONLY removes this frame's
            # reference to the fanout object. It is
            # deleted when whatever is using the context
            # manager gc'd.
            del fanout
