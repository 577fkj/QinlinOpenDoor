import json
import logging
from time import time
from typing import Optional, TYPE_CHECKING
import httpx
from httpx import AsyncBaseTransport, Request, Response, URL

if TYPE_CHECKING:
    from .client import QinlinClient

from ..core.security import Crypto
from ..models.device import Device

logger = logging.getLogger(__name__)


def get_timestamp() -> int:
    return int(time() * 1000)


class ApiTransport(AsyncBaseTransport):
    def __init__(self, client: 'QinlinClient', **kwargs):
        self._wrapper = httpx.AsyncHTTPTransport(http2=True, **kwargs)
        self._client = client

    async def handle_async_request(self, request: Request) -> Response:
        url = request.url
        headers = request.headers.copy()
        
        content_type = headers.get('Content-Type')
        data = self._extract_data(request, content_type)
        
        timestamp = get_timestamp()
        nonce = Crypto.generate_nonce()
        
        data.update({
            'timestamp': timestamp,
            'version': self._client.device.app_version_name,
            'nonce': nonce
        })
        
        data['sign'] = Crypto.get_api_sign({
            'token': self._client.token,
            **data
        })
        
        new_request = self._build_request(request, url, headers, data, content_type)
        response = await self._wrapper.handle_async_request(new_request)
        
        return await self._process_response(response)

    def _extract_data(self, request: Request, content_type: Optional[str]) -> dict:
        if content_type is None:
            return dict(request.url.params)
        elif content_type == 'application/json':
            return json.loads(request.content)
        elif content_type == 'application/x-www-form-urlencoded':
            content = request.content.decode()
            return dict(item.split('=') for item in content.split('&'))
        else:
            raise ValueError(f"Unsupported Content-Type: {content_type}")

    def _build_request(self, original: Request, url: URL, headers: dict, 
                      data: dict, content_type: Optional[str]) -> Request:
        
        if content_type is None:
            if self._client.token:
                data['sessionId'] = self._client.token
            url = URL(url, params=data)
            content = None
            headers['Content-Type'] = 'application/json'
        elif content_type == 'application/json':
            content = json.dumps(data).encode()
        else:
            content = '&'.join(f'{k}={v}' for k, v in data.items()).encode()
        
        headers['Content-Length'] = str(len(content) if content else 0)
        
        if content_type is not None and self._client.token:
            url = URL(url, params={'sessionId': self._client.token})
        
        return Request(
            method=original.method,
            url=url,
            headers=headers,
            content=content
        )

    async def _process_response(self, response: Response) -> Response:
        await response.aread()
        
        if response.status_code != 200:
            raise httpx.HTTPStatusError(
                f"Error({response.status_code})",
                request=response.request,
                response=response
            )
        
        data = response.json()
        if data.get('code') != 0:
            raise ValueError(f"Error({data.get('code')}): {data.get('message')}")
        
        new_data = json.dumps(data['data']).encode()
        headers = response.headers.copy()
        headers['Content-Length'] = str(len(new_data))
        
        return Response(
            status_code=response.status_code,
            headers=headers,
            content=new_data
        )

    async def aclose(self):
        await self._wrapper.aclose()
