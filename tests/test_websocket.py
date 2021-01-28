import pytest
import asyncio
import aiostream
import gc

from b2c2.websocket import B2C2WebsocketClient
from b2c2.frames import TradableInstrumentsFrame
from b2c2.stream_utils import anext, aiter

from tests.frame_examples import frames


@pytest.mark.parametrize(
    'expected_cls,frame', frames.cls_mapping.items()
)
def test_websocket_response_matching(expected_cls, frame):
    client = B2C2WebsocketClient()
    assert expected_cls == client._match_frame(frame)


def test_websocket_initial_protocol():
    """
    Test response to initial events
    """
    client = B2C2WebsocketClient()

    frames_queue = asyncio.Queue()
    frames_queue.put_nowait(frames.tradable_instruments)
    frames_queue.put_nowait(frames.tradable_instruments_update)

    client.stream = frames.stream(frames_queue)

    # The problem is with the queue approach is that you
    # can't have multiple listeners
    async def _test():
        result = await client._tradable_instrument_queue.get()
        assert result.tradable_instruments == [
            'BTCUSD', 'BTCEUR', 'ETHEUR'
        ]

        result = await client._tradable_instrument_queue.get()
        assert result.tradable_instruments == [
            'BTCUSD', 'BTCEUR'
        ]

        # Demoing the test function can add stuff to the stream
        await frames_queue.put(frames.tradable_instruments)

        result = await client._tradable_instrument_queue.get()
        assert result.tradable_instruments == [
            'BTCUSD', 'BTCEUR', 'ETHEUR'
        ]

        # Terminate
        await frames_queue.put(None)
    

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        asyncio.gather(client.listen(), _test())
    )


def test_stream_fanout_garbage_collection():
    """
    A websocket stream could have multiple listeners.
    Each listener has a reference to a fan out queue.

    Assert when the listener dies the queue is no longer
    kept as a reference. Otherwise you'll get memory
    leaks each time someone subscribes to a websocket event.
    """
    client = B2C2WebsocketClient()
    frames_queue = asyncio.Queue()
    frames_queue.put_nowait(None)
    client.stream = frames.stream(frames_queue)

    # The problem is with the queue approach is that you
    # can't have multiple listeners
    async def _test():
        stream = client.get_tradable_instrument_stream()
        assert len(client._tradable_instrument_fanout_queues.data) == 1
        # When stream is out of scope the client removes the queue
        # from the fanout list (when the GC is called).

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        asyncio.gather(client.listen(), _test())
    )

    # Otherwise we'd need to wait
    gc.collect()

    assert len(client._tradable_instrument_fanout_queues.data) == 0
