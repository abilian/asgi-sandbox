import asyncio
import time

import aiohttp
import httpx
from devtools import debug

URL = "http://localhost:8001/"
N = 10000


async def call_url(session):
    return await session.request(method="GET", url=URL)


async def main_aiohttp():
    start = time.time()
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*[call_url(session) for x in range(N)])

    dt = time.time() - start
    debug(f"{N} call(s) in {dt} seconds, {N / dt} req/s")


async def main_httpx():
    start = time.time()
    async with httpx.AsyncClient() as session:
        await asyncio.gather(*[call_url(session) for x in range(N)])

    dt = time.time() - start
    debug(f"{N} call(s) in {dt} seconds, {N / dt} req/s")


async def main_aiohttp2():
    async def call_url():
        async with aiohttp.ClientSession() as session:
            return await session.request(method="GET", url=URL)

    start = time.time()
    await asyncio.gather(*[call_url() for x in range(N)])

    dt = time.time() - start
    debug(f"{N} call(s) in {dt} seconds, {N / dt} req/s")


async def main_httpx2():
    start = time.time()
    async with httpx.AsyncClient() as session:
        await asyncio.gather(*[call_url(session) for x in range(N)])

    dt = time.time() - start
    debug(f"{N} call(s) in {dt} seconds, {N / dt} req/s")


asyncio.run(main_aiohttp2())
asyncio.run(main_aiohttp())
asyncio.run(main_httpx())
