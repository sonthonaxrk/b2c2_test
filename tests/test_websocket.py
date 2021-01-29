import pytest
import asyncio

from unittest.mock import MagicMock
from b2c2.websocket import B2C2WebsocketClient
from b2c2.frames import QuoteSubscribeFrame, QuoteUnsubscribeFrame
from b2c2.stream_utils import anext
from b2c2.exceptions import quote_exceptions
from tests.frame_examples import frames


loop = asyncio.get_event_loop()


def async_return(result):
    f = asyncio.Future()
    f.set_result(result)
    return f


async def run_in(seconds, coro):
    await asyncio.sleep(seconds)
    return await coro


class B2C2WebsocketTestClient(B2C2WebsocketClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        websocket = MagicMock()
        websocket_calls = MagicMock()
        websocket.send.return_value = async_return(websocket_calls)
        self._websocket = websocket


@pytest.mark.parametrize(
    'expected_cls,frame', frames.cls_mapping.items()
)
def test_websocket_response_matching(expected_cls, frame):
    client = B2C2WebsocketTestClient()
    assert expected_cls == client._match_frame(frame)


def test_websocket_tradable_instruments():
    """
    Test response to initial events
    """
    client = B2C2WebsocketTestClient()

    frames_queue = asyncio.Queue()
    frames_queue.put_nowait(frames.tradable_instruments)
    frames_queue.put_nowait(frames.tradable_instruments_update)
    client.stream = frames.stream(frames_queue)

    async def _test():
        async with client.tradable_instruments.stream() as ti_s1,\
                   client.tradable_instruments.stream() as ti_s2:

            frame = await anext(ti_s1)
            assert frame.dict() == frames.tradable_instruments

            frame = await anext(ti_s2)
            assert frame.dict() == frames.tradable_instruments

            # Simulate an object dying
            del ti_s1

            # see that nothing is changed
            frame = await anext(ti_s2)
            assert frame.dict() == frames.tradable_instruments_update

    listen_task = loop.create_task(client.listen())

    loop.run_until_complete(
        asyncio.wait(
            [listen_task, _test()],
            return_when=asyncio.FIRST_COMPLETED
        )
    )

    listen_task.cancel()


def test_subscribe_test_context_manager_open_close():
    client = B2C2WebsocketTestClient()
    frames_queue = asyncio.Queue()
    client.stream = frames.stream(frames_queue)

    async def _test():
        loop.create_task(frames_queue.put(frames.subscribe_request_success))
        subscribe_req = QuoteSubscribeFrame(**frames.subscribe_request)
        async with client.quote_subscribe(subscribe_req):
            pass

    listen_task = loop.create_task(client.listen())

    loop.run_until_complete(
        asyncio.wait(
            [listen_task, _test()],
            return_when=asyncio.FIRST_COMPLETED
        )
    )

    subscribe_req = QuoteSubscribeFrame.parse_raw(
        client._websocket.send.mock_calls[0][1][0]
    )

    unsubscribe_req = QuoteUnsubscribeFrame.parse_raw(
        client._websocket.send.mock_calls[1][1][0]
    )

    unsub_response = frames.unsub_response.copy()
    unsub_response['tag'] = unsubscribe_req.tag

    frames_queue.put_nowait(unsub_response)

    loop.run_until_complete(
        asyncio.wait(
            asyncio.all_tasks(loop),
            return_when=asyncio.FIRST_COMPLETED
        )
    )

    listen_task.cancel()

    assert subscribe_req.instrument == unsubscribe_req.instrument
    # assert garbage collection worked
    assert len(client._instrument_fanouts) == 0


def test_subscribe_concurrent_returns_same_fanout():
    client = B2C2WebsocketTestClient()
    frames_queue = asyncio.Queue()
    client.stream = frames.stream(frames_queue)

    fanouts = []

    async def _test():
        loop.create_task(frames_queue.put(frames.subscribe_request_success))
        subscribe_req = QuoteSubscribeFrame(**frames.subscribe_request)
        async with client.quote_subscribe(subscribe_req) as fanout:
            fanouts.append(fanout)

    listen_task = loop.create_task(client.listen())

    loop.run_until_complete(
        asyncio.wait(
            # Run the test twice
            [listen_task, asyncio.wait([_test(), _test()])],
            return_when=asyncio.FIRST_COMPLETED
        )
    )

    f1, f2 = fanouts
    assert f1 == f2


def test_subscribe_queues():
    client = B2C2WebsocketTestClient()
    frames_queue = asyncio.Queue()
    client.stream = frames.stream(frames_queue)

    async def _test():
        loop.create_task(frames_queue.put(frames.subscribe_request_success))
        subscribe_req = QuoteSubscribeFrame(**frames.subscribe_request)
        async with client.quote_subscribe(subscribe_req) as fanout:
            loop.create_task(frames_queue.put(frames.subscribe_stream_frame))
            async with fanout.stream() as stream:
                frame = await anext(stream)
                assert (
                    frame.timestamp ==
                    frames.subscribe_stream_frame['timestamp']
                )

    loop.run_until_complete(
        asyncio.wait(
            [client.listen(), _test()],
            return_when=asyncio.FIRST_COMPLETED
        )
    )


def test_subscribe_error():
    client = B2C2WebsocketTestClient()
    frames_queue = asyncio.Queue()
    client.stream = frames.stream(frames_queue)

    did_execute = MagicMock()

    async def _test():
        loop.create_task(
            frames_queue.put(frames.error_response_bad_instrument)
        )

        subscribe_req = QuoteSubscribeFrame(**frames.subscribe_request)

        try:
            async with client.quote_subscribe(subscribe_req):
                pass
        except quote_exceptions.InvalidSubscriptionRequest:
            did_execute()

    loop.run_until_complete(
        asyncio.wait(
            [client.listen(), _test()],
            return_when=asyncio.FIRST_COMPLETED
        )
    )

    assert did_execute.called
