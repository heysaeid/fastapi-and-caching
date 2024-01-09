from abc import ABC, abstractmethod


class BaseCache(ABC):
    
    def __init__(self, namespace: str = ""):
        self.namespace = namespace
        self.cache = None

    @abstractmethod
    async def init(self, connection_url: str) -> None:
        ...

    @abstractmethod
    async def close(self):
        ...
    
    @abstractmethod
    async def keys(self, key: str, prefix: str) -> list[str]:
        ...

    @abstractmethod
    async def get(
        self, 
        key: str, 
        prefix: str = None, 
        params: dict = None,
    ):
        ...
    
    @abstractmethod
    async def set(
        self, 
        key: str, 
        value: str, 
        expire: int = None,
        prefix: str = None,
        params: dict = None,
        key_builder: callable = None,
        **kwargs
    ):
        ...
    
    @abstractmethod
    async def exists(self, key: str, prefix: str = None):
        ...
    
    @abstractmethod
    async def delete(self, key: str, prefix: str = None, params: dict = None): 
        ...
    
    @abstractmethod
    async def delete_startswith(
        self, 
        key: str, 
        prefix: str = None, 
        params: dict = None
    ) -> None:
        ...