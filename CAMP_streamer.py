import asyncio


async def streamer_getter(queue):
    ret = await queue.get()
    if not ret["final"]:
        task = asyncio.run_coroutine_threadsafe(streamer_getter(queue), asyncio.get_event_loop())
        ret["task"] = task
    return ret


async def streamer_wrapper(function, args):
    queue = asyncio.Queue()
    asyncio.run_coroutine_threadsafe(function(*args, queue), asyncio.get_event_loop())
    ret = await queue.get()
    if not ret["final"]:
        task = asyncio.run_coroutine_threadsafe(streamer_getter(queue), asyncio.get_event_loop())
        ret["task"] = task
    return ret
