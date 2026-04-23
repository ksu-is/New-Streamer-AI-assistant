"""Notification handlers for alerts"""
import logging
import aiohttp
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Optional

from .thresholds import Alert, Severity

logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """Log levels for notifications"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class NotificationHandler(ABC):
    """Abstract base for notification handlers"""
    
    def __init__(self, level: NotificationLevel = NotificationLevel.INFO):
        self.level = level
        self._severity_map = {
            Severity.INFO: NotificationLevel.INFO,
            Severity.WARNING: NotificationLevel.WARNING,
            Severity.CRITICAL: NotificationLevel.ERROR,
        }
    
    @abstractmethod
    async def send(self, alert: Alert) -> None:
        """Send notification for an alert"""
        pass
    
    def _should_notify(self, alert: Alert) -> bool:
        """Check if this handler should notify for the alert severity"""
        alert_level = self._severity_map.get(alert.severity, NotificationLevel.INFO)
        
        levels = [NotificationLevel.DEBUG, NotificationLevel.INFO, NotificationLevel.WARNING, NotificationLevel.ERROR]
        return levels.index(alert_level) >= levels.index(self.level)


class ConsoleHandler(NotificationHandler):
    """Console notification handler"""
    
    async def send(self, alert: Alert) -> None:
        """Print alert to console"""
        if not self._should_notify(alert):
            return
        
        severity_emoji = {
            Severity.INFO: "ℹ️",
            Severity.WARNING: "⚠️",
            Severity.CRITICAL: "🚨",
        }
        
        emoji = severity_emoji.get(alert.severity, "📢")
        print(f"{emoji} [{alert.severity.value}] {alert.message}")


class FileHandler(NotificationHandler):
    """File logging notification handler"""
    
    def __init__(self, file_path: str, level: NotificationLevel = NotificationLevel.DEBUG):
        super().__init__(level)
        self.file_path = file_path
    
    async def send(self, alert: Alert) -> None:
        """Write alert to log file"""
        if not self._should_notify(alert):
            return
        
        import os
        from pathlib import Path
        
        # Ensure directory exists
        log_file = Path(self.file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().isoformat()
        log_line = f"[{timestamp}] [{alert.severity.value}] {alert.message}\n"
        
        with open(self.file_path, "a") as f:
            f.write(log_line)


class WebhookHandler(NotificationHandler):
    """Webhook notification handler for Discord/Slack"""
    
    def __init__(self, webhook_url: str, level: NotificationLevel = NotificationLevel.WARNING):
        super().__init__(level)
        self.webhook_url = webhook_url
    
    async def send(self, alert: Alert) -> None:
        """Send alert to webhook"""
        if not self._should_notify(alert):
            return
        
        if not self.webhook_url:
            return
        
        # Build Discord-compatible payload
        color = {
            Severity.INFO: 3447003,      # Blue
            Severity.WARNING: 16776960, # Yellow
            Severity.CRITICAL: 15158332, # Red
        }
        
        payload = {
            "embeds": [{
                "title": f"Stream Alert: {alert.severity.value}",
                "description": alert.message,
                "color": color.get(alert.severity, 0),
                "fields": [
                    {"name": "Type", "value": alert.alert_type, "inline": True},
                    {"name": "Source", "value": alert.source, "inline": True},
                    {"name": "Value", "value": f"{alert.value:.2f}", "inline": True},
                    {"name": "Threshold", "value": f"{alert.threshold:.2f}", "inline": True},
                ],
                "timestamp": datetime.now().isoformat(),
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                await session.post(self.webhook_url, json=payload)
            except Exception as e:
                logger.error(f"Failed to send webhook: {e}")


class NotificationDispatcher:
    """Dispatch alerts to multiple handlers"""
    
    def __init__(self):
        self._handlers: List[NotificationHandler] = []
    
    def add_handler(self, handler: NotificationHandler) -> None:
        """Add a notification handler"""
        self._handlers.append(handler)
    
    async def dispatch(self, alerts: List[Alert]) -> None:
        """Dispatch all alerts to handlers"""
        for alert in alerts:
            for handler in self._handlers:
                try:
                    await handler.send(alert)
                except Exception as e:
                    logger.error(f"Handler {handler.__class__.__name__} failed: {e}")