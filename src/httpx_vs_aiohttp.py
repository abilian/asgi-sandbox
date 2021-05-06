"""
From: https://gist.github.com/imbolc/15cab07811c32e7d50cc12f380f7f62f
"""

import aiohttp
import httpx
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

HOST, PORT = "localhost", 8000
# URL = f"http://{HOST}:{PORT}/"

URL = "http://localhost:8001/"


async def index(request):
    return PlainTextResponse("world")


async def aiohttp_single(request):
    async with aiohttp.ClientSession() as client:
        async with client.get(URL) as r:
            return _response(await r.text())


async def aiohttp_session(request):
    async with aiohttp_session.get(URL) as r:
        return _response(await r.text())


async def httpx_single(request):
    async with httpx.AsyncClient() as client:
        r = await client.get(URL)
        return _response(r.text)


async def httpx_session(request):
    r = await httpx_session.get(URL)
    return _response(r.text)


async def httpx_single_http2(request):
    async with httpx.AsyncClient(http2=True) as client:
        r = await client.get(URL)
        return _response(r.text)


async def httpx_session_http2(request):
    r = await httpx_session_http2.get(URL)
    return _response(r.text)


def _response(name):
    return PlainTextResponse("Hello, " + name)


routes = [
    Route("/", endpoint=index),
    Route("/aiohttp/single", endpoint=aiohttp_single),
    Route("/aiohttp/session", endpoint=aiohttp_session),
    Route("/httpx/single", endpoint=httpx_single),
    Route("/httpx/session", endpoint=httpx_session),
    Route("/httpx/single/http2", endpoint=httpx_single_http2),
    Route("/httpx/session/http2", endpoint=httpx_session_http2),
]


async def on_startup():
    global aiohttp_session, httpx_session, httpx_session_http2
    aiohttp_session = aiohttp.ClientSession()
    httpx_session = httpx.AsyncClient()
    httpx_session_http2 = httpx.AsyncClient(http2=True)


app = Starlette(debug=True, routes=routes, on_startup=[on_startup])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
