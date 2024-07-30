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
        """
        Retrieve a list of cache keys matching a given pattern.

        Parameters:
        - `key` (str): The specific key or pattern to search for in the cache.
        - `prefix` (str): A prefix to be added to the key before searching.

        Returns:
        - `typing.List[str]`: A list of cache keys matching the specified pattern.
        """
        key = self._generate_cache_key(key, prefix)
        return await self.cache.keys(f"*{key}*")

    async def get(
        self, 
        key: str, 
        prefix: str = None, 
        params: dict = None,
        key_builder: typing.Callable = None
    ):
        """
        Retrieve a cached value from the cache.

        Parameters:
        - `key` (str): The key to be used for retrieving the cached value.
        - `prefix` (str, optional): A prefix to be added to the key before retrieving. Defaults to None.
        - `params` (dict, optional): Additional parameters to be considered when generating the cache key. Defaults to None.
        - `key_builder` (typing.Callable, optional): A custom function for building the cache key. Defaults to None.

        Returns:
        - `typing.Union[None, typing.Any]`: The cached value if found, or None if the key is not in the cache.
        """
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
        """
        Set a value in the cache with the specified key.

        Parameters:
        - `key` (str): The key under which to store the value in the cache.
        - `value` (str): The value to be stored in the cache.
        - `expire` (int, optional): Time in seconds for the cache entry to expire. Defaults to None.
        - `prefix` (str, optional): A prefix to be added to the key before storing. Defaults to None.
        - `params` (dict, optional): Additional parameters to be considered when generating the cache key. Defaults to None.
        - `key_builder` (typing.Callable, optional): A custom function for building the cache key. Defaults to None.
        - `**kwargs`: Additional keyword arguments to be passed to the cache backend's set method.

        Returns:
        - None
        """
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
        """
        Check whether a key exists in the cache.

        Parameters:
        - `key` (str): The key to check for existence in the cache.
        - `prefix` (str, optional): A prefix to be added to the key before checking. Defaults to None.

        Returns:
        - `bool`: True if the key exists in the cache, False otherwise.
        """
        key = self._generate_cache_key(key,  prefix)
        return await self.cache.exists(key)

    async def expire(self, key: str, seconds: int):
        """
        Set an expiration time (in seconds) for a key in the cache.

        Parameters:
        - `key` (str): The key for which to set the expiration time.
        - `seconds` (int): The number of seconds until the key expires.

        Returns:
        - `bool`: True if the expiration time was set successfully, False otherwise.
        """
        return await self.cache.expire(key, seconds)

    async def delete(self, key: str, prefix: str = None, params: dict = None):
        """
        Delete a key from the cache.

        Parameters:
        - `key` (str): The key to be deleted from the cache.
        - `prefix` (str, optional): A prefix to be added to the key before deletion. Defaults to None.
        - `params` (dict, optional): Additional parameters to be considered when generating the cache key. Defaults to None.

        Returns:
        - `bool`: True if the key was successfully deleted, False otherwise.
        """
        key = self._generate_cache_key(key, prefix, params) 
        return await self.cache.delete(key)
    
    async def delete_startswith(self, key: str, prefix: str = None, params: dict = None) -> None:
        """
        Delete all keys from the cache that start with a given pattern.

        Parameters:
        - `key` (str): The pattern to match at the beginning of cache keys.
        - `prefix` (str, optional): A prefix to be added to the key before deletion. Defaults to None.
        - `params` (dict, optional): Additional parameters to be considered when generating the cache key. Defaults to None.

        Returns:
        - None
        """
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
        """
        Decorator function for caching the results of an asynchronous function.

        Parameters:
        - `key` (str, optional): The key under which to store the cached result. 
        Defaults to the function name if not provided.
        - `expire` (int, optional): Time in seconds for the cache to expire. Defaults to 60 seconds.
        - `prefix` (str, optional): A prefix to add to the cache key. Defaults to None.
        - `none` (bool, optional): Whether to cache None values. Defaults to True.
        - `use_params` (bool, optional): Whether to include function parameters in the cache key. Defaults to True.
        - `key_builder` (callable, optional): A custom function to build the cache key. Defaults to None.

        Returns:
        - `callable`: A decorator function for caching the decorated asynchronous function.
        """
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