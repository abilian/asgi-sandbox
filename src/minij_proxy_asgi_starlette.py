import traceback
from typing import Mapping, Tuple

import httpx
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

# Extremely aggressive and hardcoded value
TIMEOUT = 10

DEFAULT_ACCESS_URL = "https://mynij.app.officejs.com"

httpx_session = httpx.AsyncClient()


class ProxyEndPoint(HTTPEndpoint):
    headers: Mapping[str, str]
    url: str

    async def get(self, request: Request):
        self.headers = request.headers
        self.url = request.query_params["url"]

        status_code, content, new_headers = await self.fetch_content()
        # debug(status_code, content, new_headers)
        response = Response(content, status_code, new_headers)
        return response

    async def fetch_content(self) -> Tuple[int, bytes, dict]:
        proxy_query_header = self.make_query_headers(self.headers)
        body = b""
        response_headers = {}

        try:
            proxy_response = await httpx_session.get(
                self.url, headers=proxy_query_header, timeout=TIMEOUT
            )
            response_headers = self.filter_response_headers(proxy_response)
            response_headers["Access-Control-Allow-Origin"] = self.get_access_url()
            body = proxy_response.content
            status = proxy_response.status_code

        # except SSLError:
        #     # Invalid SSL Certificate
        #     status = 526
        except TimeoutError:
            traceback.print_exc()
            # Gateway Timeout
            status = 504
        except httpx.TransportError:
            traceback.print_exc()
            # Service Unavailable
            status = 503
        except httpx.HTTPError:
            traceback.print_exc()
            # Internal Server Error
            status = 500

        return status, body, response_headers

    def make_query_headers(self, headers: Mapping) -> Mapping:
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

    def get_access_url(self):
        return self.headers.get("Origin", DEFAULT_ACCESS_URL)

    def filter_response_headers(self, proxy_response) -> dict[str, str]:
        headers = {}
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
                headers[k] = v
        return headers


async def ping(request):
    return PlainTextResponse("OK")


routes = [
    Route("/proxy", ProxyEndPoint),
    Route("/ping", ping),
]


app = Starlette(debug=True, routes=routes)
