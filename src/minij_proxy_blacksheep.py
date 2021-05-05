import asyncio
from typing import Mapping

import blacksheep
import fire
import httpx
import requests
import uvicorn
from blacksheep import Content, Headers, Request, Response
from blacksheep.server import Application

# Extremely aggressive and hardcoded value
from devtools import debug

TIMEOUT = 10

DEFAULT_ACCESS_URL = "https://mynij.app.officejs.com"

app = Application()


@app.router.get("/")
async def home(url: str, request: Request):
    headers = request.headers
    proxy_query_header = make_request_headers(headers)

    try:
        async with httpx.AsyncClient() as client:
            proxy_response = await client.get(
                url, headers=proxy_query_header, timeout=TIMEOUT
            )

    except requests.exceptions.SSLError:
        # Invalid SSL Certificate
        status = 526
    except requests.exceptions.ConnectionError:
        status = 523
    except requests.exceptions.Timeout:
        status = 524
    except requests.exceptions.TooManyRedirects:
        status = 520
    else:
        body = proxy_response.content
        if proxy_response.status_code == 500:
            status = 520
        else:
            status = 200

    headers = []
    if status == 200:
        # copy_proxy_headers(proxy_response, response)
        headers += [(b"Access-Control-Allow-Origin", get_access_url(headers))]

    response = blacksheep.Response(
        status, content=Content(b"text/html", body), headers=headers
    )
    return response


def make_request_headers(headers: Headers):
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
        v = headers.get(k.encode("ascii"))
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
            "minij_proxy_blacksheep:app", host=host, port=port, log_level="info"
        )

    elif server == "hypercorn":
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = [f"{host}:{port}"]
        asyncio.run(serve(app, config))


if __name__ == "__main__":
    fire.Fire(main)
