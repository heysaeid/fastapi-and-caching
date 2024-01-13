# fastapi-and-caching
<strong>FastAPI and Caching</strong> is an extension for FastAPI that provides support for various caching mechanisms, allowing you to easily leverage caching within your FastAPI applications.


# Install
```
pip install git+https://github.com/heysaeid/fastapi-and-logging/tree/master
```

## How to Use:

### RedisCache
First, configure it as follows:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_and_caching import RedisCache
from config import settings


app = FastAPI()
cache = RedisCache(namespace="fastapi") # 

@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.init(connection_url="redis://localhost")

    yield

    await cache.close()
```

Then you can use it as follows:
‍‍‍
```python
@app.get("/")
@cache.cached(key="root", expire=30, prefix="router")
def root():
    return "FastAPI And Caching"
```

Cached input parameters:
- `key` (str, optional): The key under which to store the cached result. 
  Defaults to the function name if not provided.
- `expire` (int, optional): Time in seconds for the cache to expire. Defaults to 60 seconds.
- `prefix` (str, optional): A prefix to add to the cache key. Defaults to None.
- `none` (bool, optional): Whether to cache None values. Defaults to True.
- `use_params` (bool, optional): Whether to include function parameters in the cache key. Defaults to True.
- `key_builder` (callable, optional): A custom function to build the cache key. Defaults to None.

#### Other methods:
cache.keys()
- `key` (str): The specific key or pattern to search for in the cache.
- `prefix` (str): A prefix to be added to the key before searching.


cache.get()
- `key` (str): The key to be used for retrieving the cached value.
- `prefix` (str, optional): A prefix to be added to the key before retrieving. Defaults to None.
- `params` (dict, optional): Additional parameters to be considered when generating the cache key. Defaults to None.
- `key_builder` (typing.Callable, optional): A custom function for building the cache key. Defaults to None.


cache.set()
- `key` (str): The key under which to store the value in the cache.
- `value` (str): The value to be stored in the cache.
- `expire` (int, optional): Time in seconds for the cache entry to expire. Defaults to None.
- `prefix` (str, optional): A prefix to be added to the key before storing. Defaults to None.
- `params` (dict, optional): Additional parameters to be considered when generating the cache key. Defaults to None.
- `key_builder` (typing.Callable, optional): A custom function for building the cache key. Defaults to None.
- `**kwargs`: Additional keyword arguments to be passed to the cache backend's set method.


cache.exists()
- `key` (str): The key to check for existence in the cache.
- `prefix` (str, optional): A prefix to be added to the key before checking. Defaults to None.


cache.expire()
- `key` (str): The key for which to set the expiration time.
- `seconds` (int): The number of seconds until the key expires.


cache.delete()
- `key` (str): The key to be deleted from the cache.
- `prefix` (str, optional): A prefix to be added to the key before deletion. Defaults to None.
- `params` (dict, optional): Additional parameters to be considered when generating the cache key. Defaults to None.


cache.delete_startswith()
- `key` (str): The pattern to match at the beginning of cache keys.
- `prefix` (str, optional): A prefix to be added to the key before deletion. Defaults to None.
- `params` (dict, optional): Additional parameters to be considered when generating the cache key. Defaults to None.