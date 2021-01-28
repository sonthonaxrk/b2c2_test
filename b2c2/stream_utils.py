from typing import AsyncIterator, Any

# This will be added to stdlib soon.
async def anext(ait):
    return await ait.__anext__()


def aiter(ait):
    return ait.__aiter__()


async def repeat_last(iterable: AsyncIterator[Any]) -> AsyncIterator[Any]:
    """
    This will repeat the last value from an async
    stream if nothing else can be yielded.
    """
    async_iter_ = aiter(new_values_iterator)
    repeat_value = await anext(async_iter)
    yield repeat_value

    iter_task = asyncio.create_task(async_iter_.__anext__())
    completed_async_iterable = False

    while True:
        if not iter_task.done() or completed_async_iterable:
            yield repeat_value
        else:
            # create a new iter task
            try:
                repeat_value = iter_task.result()
                iter_task = asyncio.create_task(async_iter_.__anext__())
            except StopAsyncIteration:
                completed_async_iterable = True
