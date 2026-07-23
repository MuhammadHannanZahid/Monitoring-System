from abc import ABC, abstractmethod

class BaseSeeder(ABC):
    @abstractmethod
    async def run(self) -> None:
        raise NotImplementedError