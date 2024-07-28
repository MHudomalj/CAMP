import aiohttp
import json


async def llama_generate_query(endpoint, payload, index, count):
    data = {
        "model": "llama2",
        "stream": False,
        "prompt": payload
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, json=data) as response:
            res = await response.json()
        return {"index": index, "data": res["response"], "count": count}


async def llama_chat_query(endpoint, payload, index, count):
    data = {
        "model": "llama2",
        "stream": False,
        "messages": payload,
        "options": {
            "num_predict": 200
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, json=data) as response:
            res = await response.json()
            return {"index": index, "data": res["message"]["content"], "count": count}


async def llama_chat_stream(endpoint, payload, num_predict, index, count, queue):
    data = {
        "model": "llama2",
        "stream": True,
        "messages": payload,
        "options": {
            "num_predict": num_predict
        }
    }
    i = 0
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.post(endpoint, json=data) as response:
            async for line in response.content:
                if line:
                    body = json.loads(line)
                    await queue.put({"index": index,
                                     "data": body["message"]["content"],
                                     "count": [count, i],
                                     "final": False})
                    i += 1
            await queue.put({"index": index,
                             "data": "",
                             "count": [count, i],
                             "final": True})
    print("Finish stream.")


async def whisper_query(endpoint, payload, index, count):
    data = {
        "file": payload
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, data=data) as response:
            res = await response.json()
            return {"index": index, "data": res['transcription'], "count": count}


async def tts_query(endpoint, payload, index, count):
    data = {
        "transcription": payload
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, json=data) as response:
            res = await response.content.read()
            return {"index": index, "data": res, "count": count}
