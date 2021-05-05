import asyncio
import traceback
from typing import Mapping

import falcon.asgi
import fire
import httpx
import uvicorn

# Extremely aggressive and hardcoded value
from httpx import Timeout, TooManyRedirects

TIMEOUT = 10

DEFAULT_ACCESS_URL = "https://mynij.app.officejs.com"


class ProxyResource:
    async def on_get(self, request, response):
        try:
            await self._on_get(request, response)
        except:
            traceback.print_exc()

    async def _on_get(self, request, response):
        url = request.get_param("url")

        proxy_query_header = make_request_headers(request.headers)

        body = b""

        try:
            async with httpx.AsyncClient() as client:
                proxy_response = await client.get(
                    url, headers=proxy_query_header, timeout=TIMEOUT
                )

        # except SSLError:
        #     # Invalid SSL Certificate
        #     status = 526
        except ConnectionError:
            status = 523
        except Timeout:
            status = 524
        except TooManyRedirects:
            status = 520
        else:
            body = proxy_response.content
            if proxy_response.status_code == 500:
                status = 520
            else:
                status = 200

        headers = []
        if status == 200:
            copy_proxy_headers(proxy_response, response)
            response.append_header(
                "Access-Control-Allow-Origin", get_access_url(request.headers)
            )

        response.data = body


app = falcon.asgi.App()
proxy = ProxyResource()
app.add_route("/", proxy)


def make_request_headers(headers):
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
            response.append_header(k, v)


def main(host="localhost", port=8000, server="uvicorn"):
    if server == "uvicorn":
        uvicorn.run("minij_proxy_falcon:app", host=host, port=port, log_level="info")

    elif server == "hypercorn":
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = [f"{host}:{port}"]
        asyncio.run(serve(app, config))


if __name__ == "__main__":
    fire.Fire(main)
