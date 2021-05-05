FILE = "/Users/fermigier/tmp/index.html"


async def app(scope, receive, send):
    assert scope["type"] == "http"

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"text/html"],
            ],
        }
    )

    body: bytes = open(FILE, "rb").read()
    await send(
        {
            "type": "http.response.body",
            "body": body,
        }
    )
