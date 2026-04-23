"""StreamerAI integration bridge"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import get_config
from ..storage.database import Database, get_database

logger = logging.getLogger(__name__)


class StreamerAIBridge:
    """Bridge for StreamerAI integration"""
    
    def __init__(self):
        self._config = get_config().streamer_ai
        self._database: Optional[Database] = None
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to StreamerAI database"""
        if not self._config.enabled:
            logger.info("StreamerAI integration disabled")
            return False
        
        db_path = Path(self._config.database_path)
        if not db_path.exists():
            logger.warning(f"StreamerAI database not found: {db_path}")
            return False
        
        try:
            self._database = Database(str(db_path))
            self._database.connect()
            self._connected = True
            logger.info("Connected to StreamerAI database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to StreamerAI: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from StreamerAI"""
        if self._database:
            self._database.close()
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def get_ai_metrics(self) -> Dict[str, Any]:
        """Get AI performance metrics from StreamerAI"""
        if not self._connected or not self._database:
            return {}
        
        # This would read from StreamerAI's tables
        # Placeholder for actual implementation
        return {
            "tts_response_time_ms": 0,
            "gpt_processing_latency_ms": 0,
            "active_products": 0,
            "comments_processed": 0,
        }
    
    async def pause_ai(self) -> bool:
        """Send PAUSE_AI command to StreamerAI"""
        if not self._connected:
            return False
        
        try:
            db = get_database()
            db.write_command("PAUSE_AI")
            logger.info("Sent PAUSE_AI command to StreamerAI")
            return True
        except Exception as e:
            logger.error(f"Failed to send PAUSE_AI: {e}")
            return False
    
    async def resume_ai(self) -> bool:
        """Send RESUME_AI command to StreamerAI"""
        if not self._connected:
            return False
        
        try:
            db = get_database()
            db.write_command("RESUME_AI")
            logger.info("Sent RESUME_AI command to StreamerAI")
            return True
        except Exception as e:
            logger.error(f"Failed to send RESUME_AI: {e}")
            return False
    
    async def skip_product(self) -> bool:
        """Send SKIP_PRODUCT command to StreamerAI"""
        if not self._connected:
            return False
        
        try:
            db = get_database()
            db.write_command("SKIP_PRODUCT")
            logger.info("Sent SKIP_PRODUCT command to StreamerAI")
            return True
        except Exception as e:
            logger.error(f"Failed to send SKIP_PRODUCT: {e}")
            return False
    
    async def emergency_stop(self) -> bool:
        """Send EMERGENCY_STOP command to StreamerAI"""
        if not self._connected:
            return False
        
        try:
            db = get_database()
            db.write_command("EMERGENCY_STOP")
            logger.info("Sent EMERGENCY_STOP command to StreamerAI")
            return True
        except Exception as e:
            logger.error(f"Failed to send EMERGENCY_STOP: {e}")
            return False
    
    async def coordinate_during_issue(self, issue_type: str) -> None:
        """Coordinate with StreamerAI during a stream issue"""
        if issue_type in ["high_cpu", "high_memory", "network_latency"]:
            await self.pause_ai()
        elif issue_type == "stream_restored":
            await self.resume_ai()


# Global bridge instance
_bridge: Optional[StreamerAIBridge] = None


def get_streamer_ai_bridge() -> StreamerAIBridge:
    """Get the global StreamerAI bridge instance"""
    global _bridge
    if _bridge is None:
        _bridge = StreamerAIBridge()
    return _bridge