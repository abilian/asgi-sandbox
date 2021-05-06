import asyncio
import time
from typing import Mapping, Optional, Tuple

import fire
import httpx
import requests
import uvicorn
from devtools import debug
from httpx import AsyncClient, TransportError, HTTPError
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

# Extremely aggressive and hardcoded value
TIMEOUT = 10

DEFAULT_ACCESS_URL = "https://mynij.app.officejs.com"

httpx_session = None


class ProxyEndPoint(HTTPEndpoint):
    async def get(self, request: Request):
        global httpx_session

        url = request.query_params["url"]
        headers = request.headers
        status_code, content, new_headers = await self.fetch_content(
            httpx_session, url, headers
        )
        response = Response(content, status_code, new_headers)
        time.sleep(10)
        return response

    async def fetch_content(
        self, client: AsyncClient, url: str, headers
    ) -> Tuple[int, bytes, Mapping]:
        proxy_query_header = self.make_request_headers(headers)
        body = b""

        try:
            proxy_response = await client.get(
                url, headers=proxy_query_header, timeout=TIMEOUT
            )

        # except SSLError:
        #     # Invalid SSL Certificate
        #     status = 526
        except TimeoutError:
            # Gateway Timeout
            status = 504
        except TransportError:
            # Service Unavailable
            status = 503
        except HTTPError:
            # Internal Server Error
            status = 500
        else:
            body = proxy_response.content
            if proxy_response.status_code == 500:
                status = 500
            else:
                status = 200


        response_headers = {}
        # copy_proxy_headers(proxy_response, response)
        # response.headers["Access-Control-Allow-Origin"] = get_access_url(request.headers)
        return status, body, response_headers

    def make_request_headers(self, headers: Mapping) -> Mapping:
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

    def get_access_url(self, headers: Mapping):
        return headers.get("Origin", DEFAULT_ACCESS_URL)

    def copy_proxy_headers(self, proxy_response, response) -> None:
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


async def toto(request):
    return PlainTextResponse("toto")


routes = [
    Route("/", ProxyEndPoint),
    Route("/toto", toto),
]


async def on_startup():
    global httpx_session

    httpx_session = httpx.AsyncClient()


app = Starlette(debug=True, routes=routes, on_startup=[on_startup])


def main(host="localhost", port=8000, server="uvicorn"):
    if server == "uvicorn":
        uvicorn.run(app, host=host, port=port, log_level="info")

    elif server == "hypercorn":
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = [f"{host}:{port}"]
        asyncio.run(serve(app, config))


if __name__ == "__main__":
    fire.Fire(main)
