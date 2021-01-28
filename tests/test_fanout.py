import asyncio
import gc

from b2c2.websocket import Fanout
from b2c2.stream_utils import anext, aiter


loop = asyncio.get_event_loop()


def test_gc():
    fanout = Fanout(asyncio.Queue())
    fanout._queue.put_nowait(None)

    async def _test():
        # assignment used for gc test
        stream = await fanout.stream()  # noqa
        assert len(fanout._fanout_queues.data) == 1
        # When stream is out of scope the fanout removes the queue
        # from the fanout list (when the GC is called). Thus the
        # WeakSet

    loop.run_until_complete(_test())

    # Otherwise we might need to wait
    gc.collect()

    assert len(fanout._fanout_queues.data) == 0


def test_async_generators():
    """
    Assert that the stream can be duplicated
    """
    fanout = Fanout(asyncio.Queue())
    fanout._queue.put_nowait(1)

    # The problem is with the queue approach is that you
    # can't have multiple listeners
    async def _test():
        stream1 = await fanout.stream()
        stream2 = await fanout.stream()
        value1 = await anext(aiter(stream1))
        value2 = await anext(aiter(stream2))
        assert value1 == value2 == 1
        # When stream is out of scope the client removes the queue
        # from the fanout list (when the GC is called). Thus the
        # WeakSet

    loop.run_until_complete(_test())

    # Otherwise we'd need to wait
    gc.collect()

    assert len(fanout._fanout_queues.data) == 0
