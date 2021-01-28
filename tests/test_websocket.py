import pytest
import asyncio
import aiostream
import gc

from b2c2.websocket import B2C2WebsocketClient, Fanout
from b2c2.frames import TradableInstrumentsFrame
from b2c2.stream_utils import anext, aiter

from tests.frame_examples import frames


loop = asyncio.get_event_loop()


@pytest.mark.parametrize(
    'expected_cls,frame', frames.cls_mapping.items()
)
def test_websocket_response_matching(expected_cls, frame):
    client = B2C2WebsocketClient()
    assert expected_cls == client._match_frame(frame)


def test_websocket_tradable_instruments():
    """
    Test response to initial events
    """
    client = B2C2WebsocketClient()

    frames_queue = asyncio.Queue()
    frames_queue.put_nowait(frames.tradable_instruments)
    frames_queue.put_nowait(frames.tradable_instruments_update)
    frames_queue.put_nowait(B2C2WebsocketClient._stream_terminate)
    client.stream = frames.stream(frames_queue)

    async def _test():
        tradable_instruments_stream1 = aiter(await client.tradable_instruments.stream())
        tradable_instruments_stream2 = aiter(await client.tradable_instruments.stream())

        frame = await anext(tradable_instruments_stream1)
        assert frame.dict() == frames.tradable_instruments

        frame = await anext(tradable_instruments_stream2)
        assert frame.dict() == frames.tradable_instruments

        # Simulate an object dying
        del tradable_instruments_stream1

        # see that nothing is changed
        frame = await anext(tradable_instruments_stream2)
        assert frame.dict() == frames.tradable_instruments_update

    loop.run_until_complete(
        asyncio.gather(client.listen(), _test())
    )



