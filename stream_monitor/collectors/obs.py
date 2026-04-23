"""OBS WebSocket collector for stream metrics"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from .base import BaseCollector, CollectorMetrics
from ..config import get_config

logger = logging.getLogger(__name__)


class OBSCollector(BaseCollector):
    """Collector for OBS Studio metrics via WebSocket"""
    
    def __init__(self, poll_interval: int = 2):
        super().__init__("obs", poll_interval)
        self._config = get_config().obs
        self._client: Optional[Any] = None
        self._reconnect_attempts = 0
        self._last_stats: Optional[Dict[str, Any]] = None
    
    async def connect(self) -> bool:
        """Connect to OBS WebSocket"""
        try:
            # Import here to make obsws-python optional
            from obsws import OBSSocket
            
            self._client = OBSSocket(
                host=self._config.host,
                port=self._config.port,
                password=self._config.password,
                timeout=10
            )
            
            # Test connection
            await self._client.call("GetVersion")
            self._reconnect_attempts = 0
            logger.info(f"Connected to OBS WebSocket at {self._config.host}:{self._config.port}")
            return True
            
        except Exception as e:
            self._set_error(f"Failed to connect to OBS: {e}")
            logger.warning(f"OBS connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from OBS WebSocket"""
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                logger.debug(f"Error closing OBS connection: {e}")
            self._client = None
    
    async def collect(self) -> CollectorMetrics:
        """Collect OBS stats"""
        if not self._client:
            await self.connect()
        
        try:
            # Get stats from OBS
            stats = await self._client.call("GetStats")
            stats_data = stats.json()
            
            # Get stream status
            stream_status = await self._client.call("GetStreamStatus")
            stream_data = stream_status.json()
            
            # Get video settings
            video = await self._client.call("GetVideoSettings")
            video_data = video.json()
            
            metrics = {
                "fps": stats_data.get("activeFps", 0),
                "cpu_usage": stats_data.get("cpuUsage", 0),
                "memory_usage": stats_data.get("memoryUsage", 0),
                "render_skipped": stats_data.get("renderSkippedFrames", 0),
                "render_total": stats_data.get("renderTotalFrames", 0),
                "output_skipped": stats_data.get("outputSkippedFrames", 0),
                "output_total": stats_data.get("outputTotalFrames", 0),
                "is_streaming": stream_data.get("streaming", False),
                "is_recording": stream_data.get("recording", False),
                "width": video_data.get("baseWidth", 0),
                "height": video_data.get("baseHeight", 0),
            }
            
            # Calculate dropped frame percentage
            if metrics["output_total"] > 0:
                metrics["dropped_frames_percent"] = (
                    metrics["output_skipped"] / metrics["output_total"] * 100
                )
            else:
                metrics["dropped_frames_percent"] = 0.0
            
            self._last_stats = metrics
            self._reconnect_attempts = 0
            
            return CollectorMetrics(
                timestamp=datetime.now(),
                source="obs",
                data=metrics
            )
            
        except Exception as e:
            self._set_error(f"Failed to collect OBS stats: {e}")
            logger.warning(f"OBS stats collection error: {e}")
            
            # Try to reconnect
            await self._maybe_reconnect()
            
            # Return last known stats if available
            if self._last_stats:
                return CollectorMetrics(
                    timestamp=datetime.now(),
                    source="obs",
                    data=self._last_stats
                )
            raise
    
    async def _maybe_reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff"""
        if self._reconnect_attempts >= self._config.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self._reconnect_attempts += 1
        delay = self._config.reconnect_interval * (2 ** (self._reconnect_attempts - 1))
        
        logger.info(f"Attempting to reconnect to OBS in {delay}s (attempt {self._reconnect_attempts})")
        await asyncio.sleep(delay)
        
        await self.connect()
    
    async def health_check(self) -> bool:
        """Check if OBS connection is healthy"""
        if not self._client:
            return False
        
        try:
            await self._client.call("GetVersion")
            return True
        except Exception:
            return False
    
    async def get_bitrate(self) -> Optional[int]:
        """Get current bitrate if available"""
        if not self._client:
            return None
        
        try:
            # Try to get stats that include bitrate
            stats = await self._client.call("GetStats")
            return stats.json().get("averageFrameRenderTime", 0)
        except Exception:
            return None