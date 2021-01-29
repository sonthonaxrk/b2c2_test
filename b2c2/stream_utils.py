

# These will be added to stdlib soon.
async def anext(ait):
    return await ait.__anext__()


def aiter(ait):
    return ait.__aiter__()
