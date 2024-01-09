import typing
import ujson
import pickle
import inspect
from functools import wraps
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
            
    def cached(
        self, 
        key: str = None, 
        expire: int = 60, 
        prefix: str = None, 
        none: bool = True,
        use_params: bool = True,
        key_builder: callable = None,
    ):
        def _cached(func):
            @wraps(func)
            async def __cached(*args, **kwargs):
                params = self.__get_params(func, use_params, args, kwargs)
                cache_key = func.__name__ if key is None else key
                
                result = await self.get(
                    key=cache_key, 
                    prefix=prefix, 
                    params=params, 
                    key_builder=key_builder
                )

                if result is None:
                    result = await func(*args, **kwargs)
                    if none or result:
                        await self.set(
                            key=cache_key, 
                            value=result, 
                            expire=expire,
                            prefix=prefix,
                            params=params,
                            key_builder=key_builder,
                        )
                    
                return result

            return __cached

        return _cached
    
    def __get_params(
        self, 
        func: typing.Callable, 
        use_params: bool, 
        args: tuple,
        kwargs: dict,
    ) -> str | None:
        params = None
        if use_params:
            sig = inspect.signature(func)    
            bound_args = sig.bind(*args, **kwargs)
            params = bound_args.arguments
            params.pop("self", None)
        return params
            
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