import logging
import asyncio
from websockets import serve

logger = logging.getLogger(__name__)


async def handle(ws):
    async for message in ws:
        await ws.send(message)


async def start_serve():
    async with serve(handle, "0.0.0.0", 8080):
        await asyncio.Future()


def start():
    asyncio.run(start_serve())
