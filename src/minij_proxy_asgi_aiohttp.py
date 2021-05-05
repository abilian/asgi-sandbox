import asyncio
from typing import Mapping

import aiohttp
import fire
import uvicorn
from aiohttp import ClientSSLError, ClientTimeout, TooManyRedirects
from starlette.requests import Request
from starlette.responses import Response

# Extremely aggressive and hardcoded value
TIMEOUT = 10

DEFAULT_ACCESS_URL = "https://mynij.app.officejs.com"


async def application(scope, receive, send):
    if scope["type"] != "http":
        return

    request = Request(scope, receive)
    response = Response()

    if request.method != "GET":
        response.status = 405
    else:
        async with aiohttp.ClientSession() as client:
            await fetch_content(client, request, response)

    await response(scope, receive, send)


async def fetch_content(
    client: aiohttp.ClientSession, request: Request, response: Response
) -> None:
    url = request.query_params["url"]
    proxy_query_header = make_request_headers(request.headers)

    try:
        proxy_response = await client.get(
            url, headers=proxy_query_header, timeout=TIMEOUT
        )
    except ClientSSLError:
        # Invalid SSL Certificate
        status = 526
    except ConnectionError:
        status = 523
    except ClientTimeout:
        status = 524
    except TooManyRedirects:
        status = 520
    else:
        response.body = await proxy_response.content.read()
        if proxy_response.status == 500:
            response.status = 520
        else:
            copy_proxy_headers(proxy_response, response)

    response.headers["Access-Control-Allow-Origin"] = get_access_url(request.headers)


def make_request_headers(headers: Mapping):
    request_headers = {}
    HEADERS = [
        "Content-Type",
        "Accept",
        "Accept-Language",
        "Range",
        "If-Modified-Since",
        "If-None-Match",
    ]
    for k in HEADERS:
        v = headers.get(k)
        if v:
            request_headers[k] = str(v)

    return request_headers


def get_access_url(headers: Mapping):
    return headers.get("Origin", DEFAULT_ACCESS_URL)


def copy_proxy_headers(proxy_response, response) -> None:
    HEADERS = [
        "Content-Disposition",
        "Content-Type",
        "Date",
        "Last-Modified",
        "Vary",
        "Cache-Control",
        "Etag",
        "Accept-Ranges",
        "Content-Range",
    ]
    for k, v in proxy_response.headers.items():
        k = k.title()
        if k in HEADERS:
            response.headers[k] = v


def main(host="localhost", port=8000, server="uvicorn"):
    if server == "uvicorn":
        uvicorn.run(
            "minij_proxy_asgi_aiohttp:application",
            host=host,
            port=port,
            log_level="info",
        )

    elif server == "hypercorn":
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = [f"{host}:{port}"]
        asyncio.run(serve(application, config))


if __name__ == "__main__":
    fire.Fire(main)
