import aiohttp

class AsyncResponse:
    def __init__(self, status, headers, text, url):
        self.status_code = status
        self.headers = headers
        self._text = text
        self.url = url
        self.ok = 200 <= self.status_code < 300

    @property
    def text(self):
        return self._text

    def json(self):
        import json
        return json.loads(self._text)

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"HTTP {self.status_code} for {self.url}")


def _convert_timeout(timeout):
    """把 requests 风格的 timeout 转成 aiohttp 的 ClientTimeout"""
    if timeout is None:
        return aiohttp.ClientTimeout(total=None)
    if isinstance(timeout, (int, float)):
        return aiohttp.ClientTimeout(total=timeout)
    if isinstance(timeout, tuple) and len(timeout) == 2:
        connect, read = timeout
        return aiohttp.ClientTimeout(sock_connect=connect, sock_read=read, total=None)
    raise TypeError("timeout must be None, number, or (connect, read) tuple")


async def post(url, data=None, json=None, headers=None, timeout=None, **kwargs):
    """
    asyncio 版本的 requests.post
    返回值、参数和行为与 requests.post 尽可能一致
    """
    client_timeout = _convert_timeout(timeout)
    async with aiohttp.ClientSession(timeout=client_timeout) as session:
        async with session.post(url, data=data, json=json, headers=headers) as resp:
            text = await resp.text()
            return AsyncResponse(
                status=resp.status,
                headers=dict(resp.headers),
                text=text,
                url=str(resp.url)
            )
