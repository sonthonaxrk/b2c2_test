import asyncio

from b2c2.websocket import Fanout
from asyncstdlib import islice, chain


loop = asyncio.get_event_loop()


def test_fanout_queue():
    fanout = Fanout(asyncio.Queue())
    fanout._queue.put_nowait(1)
    fanout._queue.put_nowait(2)

    async def _test():

        async with fanout.stream() as s1,\
                   fanout.stream() as s2,\
                   fanout.stream() as s3:

            s1 = islice(s1, 2)
            s2 = islice(s2, 2)
            s3 = islice(s3, 2)

            chained = chain(s1, s2, s3)
            items = [item async for item in chained]
            assert [1, 2, 1, 2, 1, 2] == items
            assert len(fanout._fanout_queues.data) == 3

    loop.run_until_complete(_test())
    assert len(fanout._fanout_queues.data) == 0
