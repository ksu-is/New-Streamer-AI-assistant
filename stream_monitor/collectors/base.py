"""Abstract base collector interface"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class CollectorMetrics:
    """Base metrics container"""
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data
        }


class BaseCollector(ABC):
    """Abstract base class for all collectors"""
    
    def __init__(self, name: str, poll_interval: int = 5):
        self.name = name
        self.poll_interval = poll_interval
        self._last_collection: Optional[datetime] = None
        self._is_running = False
        self._last_error: Optional[str] = None
    
    @abstractmethod
    async def collect(self) -> CollectorMetrics:
        """Collect metrics from the source"""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the source"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the source"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the collector is healthy"""
        pass
    
    async def start(self) -> None:
        """Start the collector"""
        self._is_running = True
    
    async def stop(self) -> None:
        """Stop the collector"""
        self._is_running = False
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def last_error(self) -> Optional[str]:
        return self._last_error
    
    def _set_error(self, error: str) -> None:
        self._last_error = error