import typing
import ujson
import pickle
from redis import asyncio as aioredis
from fastapi_and_caching.backends.base import BaseCache


class RedisCache(BaseCache):

    async def init(self, connection_url: str) -> None:
        self.cache = await aioredis.from_url(connection_url)

    async def close(self):
        await self.cache.close()

    async def keys(self, key: str, prefix: str) -> typing.List[str]:
        key = self._generate_cache_key(key, prefix)
        return await self.cache.keys(f"*{key}*")

    async def get(
        self, 
        key: str, 
        prefix: str = None, 
        params: dict = None,
        key_builder: typing.Callable = None
    ):
        if key_builder is None:
            key = self._generate_cache_key(key, prefix, params)
        else:
            key = key_builder(key)
            
        result = await self.cache.get(key)
        
        if not result:
            return

        try:
            return ujson.loads(result.decode("utf8"))
        except UnicodeDecodeError:
            return pickle.loads(result)

    async def set(
        self, 
        key: str, 
        value: str, 
        expire: int = None,
        prefix: str = None,
        params: dict = None,
        key_builder: typing.Callable = None,
        **kwargs
    ):  
        if isinstance(value, dict):
            value = ujson.dumps(value)
        elif isinstance(value, object):
            value = pickle.dumps(value)
        
        if key_builder is None:
            key = self._generate_cache_key(key, prefix, params)
        else:
            key = key_builder(key)
        
        await self.cache.set(name=key, value=value, ex=expire, **kwargs)

    async def exists(self, key: str, prefix: str = None):
        key = self._generate_cache_key(key,  prefix)
        return await self.cache.exists(key)

    async def expire(self, key: str, seconds: int):
        return await self.cache.expire(key, seconds)

    async def delete(self, key: str, prefix: str = None, params: dict = None): 
        key = self._generate_cache_key(key, prefix, params) 
        return await self.cache.delete(key)
    
    async def delete_startswith(self, key: str, prefix: str = None, params: dict = None) -> None:
        key = self._generate_cache_key(key, prefix, params) 
        async for name in self.cache.scan_iter(f"{key}:*"):
            await self.cache.delete(name)
            
    def _generate_cache_key(
        self, 
        key: str, 
        prefix: str = None, 
        params: dict = None
    ) -> str:
        cache_key = self.namespace
        
        if prefix:
            cache_key += f":{prefix}"
            
        cache_key += f":{key}"
        if params:
            for value in params.values():
                cache_key += f":{value}"

        return cache_key