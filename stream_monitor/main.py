"""Main entry point for StreamHealthMonitor"""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

from .config import load_config, get_config
from .collectors.obs import OBSCollector
from .collectors.system import SystemCollector
from .storage.database import get_database, close_database
from .storage.aggregator import MetricsAggregator
from .alerting.thresholds import ThresholdChecker
from .alerting.notifiers import (
    NotificationDispatcher, ConsoleHandler, FileHandler, WebhookHandler,
    NotificationLevel
)
from .alerting.analysis import TrendAnalyzer
from .integration.streamer_ai import get_streamer_ai_bridge

logger = logging.getLogger(__name__)


class StreamHealthMonitor:
    """Main monitoring application"""
    
    def __init__(self, config_file: Optional[str] = None):
        self._config = load_config(config_file)
        self._running = False
        
        # Collectors
        self._obs_collector: Optional[OBSCollector] = None
        self._system_collector: Optional[SystemCollector] = None
        
        # Storage
        self._aggregator = MetricsAggregator()
        
        # Alerting
        self._threshold_checker = ThresholdChecker()
        self._notification_dispatcher = NotificationDispatcher()
        self._trend_analyzer = TrendAnalyzer()
        
        # Integration
        self._streamer_ai_bridge = get_streamer_ai_bridge()
        
        # Tasks
        self._collectors_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the monitor"""
        self._running = True
        
        # Setup logging
        self._setup_logging()
        
        # Setup notifications
        self._setup_notifications()
        
        # Initialize collectors
        self._obs_collector = OBSCollector(poll_interval=2)
        self._system_collector = SystemCollector(poll_interval=5)
        
        # Connect to collectors
        await self._obs_collector.connect()
        await self._system_collector.connect()
        
        # Connect to StreamerAI if enabled
        if self._config.streamer_ai.enabled:
            await self._streamer_ai_bridge.connect()
        
        # Start background tasks
        self._collectors_task = asyncio.create_task(self._collectors_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Stream Health Monitor started")
        
        # Run until stopped
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
    
    async def stop(self) -> None:
        """Stop the monitor"""
        self._running = False
        
        # Cancel tasks
        if self._collectors_task:
            self._collectors_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Disconnect collectors
        if self._obs_collector:
            await self._obs_collector.disconnect()
        if self._system_collector:
            await self._system_collector.disconnect()
        
        # Disconnect StreamerAI
        if self._config.streamer_ai.enabled:
            await self._streamer_ai_bridge.disconnect()
        
        # Close database
        close_database()
        
        logger.info("Stream Health Monitor stopped")
    
    async def _collectors_loop(self) -> None:
        """Main collectors loop"""
        while self._running:
            try:
                # Collect OBS metrics
                if self._obs_collector:
                    obs_metrics = await self._obs_collector.collect()
                    self._aggregator.add_metric("obs", obs_metrics.data)
                    
                    # Store to database
                    db = get_database()
                    db.save_metrics("obs", obs_metrics.data)
                    
                    # Update trend analyzer
                    for key, value in obs_metrics.data.items():
                        if isinstance(value, (int, float)):
                            self._trend_analyzer.add_data_point(f"obs_{key}", value)
                
                # Collect system metrics
                if self._system_collector:
                    system_metrics = await self._system_collector.collect()
                    self._aggregator.add_metric("system", system_metrics.data)
                    
                    # Store to database
                    db = get_database()
                    db.save_metrics("system", system_metrics.data)
                    
                    # Update trend analyzer
                    for key, value in system_metrics.data.items():
                        if isinstance(value, (int, float)):
                            self._trend_analyzer.add_data_point(f"system_{key}", value)
                
                # Check thresholds and create alerts
                if self._config.alerts.enabled:
                    obs_data = obs_metrics.data if self._obs_collector else {}
                    system_data = system_metrics.data if self._system_collector else {}
                    
                    alerts = self._threshold_checker.check_all(obs_data, system_data)
                    
                    # Filter alerts and send notifications
                    for alert in alerts:
                        if self._threshold_checker.should_alert(alert.alert_type):
                            db = get_database()
                            db.create_alert(
                                severity=alert.severity.value,
                                alert_type=alert.alert_type,
                                message=alert.message,
                                value=alert.value,
                                threshold=alert.threshold
                            )
                            
                            # Coordinate with StreamerAI
                            if self._config.streamer_ai.enabled:
                                await self._streamer_ai_bridge.coordinate_during_issue(alert.alert_type)
                    
                    # Dispatch notifications
                    await self._notification_dispatcher.dispatch(alerts)
                
            except Exception as e:
                logger.error(f"Error in collectors loop: {e}")
            
            # Wait before next collection
            await asyncio.sleep(2)
    
    async def _cleanup_loop(self) -> None:
        """Periodic cleanup loop"""
        while self._running:
            try:
                db = get_database()
                db.cleanup_old_data(self._config.storage.retention_hours)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
            
            # Run cleanup every hour
            await asyncio.sleep(3600)
    
    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
    
    def _setup_notifications(self) -> None:
        """Setup notification handlers"""
        notif_config = self._config.notifications
        
        if notif_config.console_enabled:
            level = NotificationLevel[notif_config.console_level]
            self._notification_dispatcher.add_handler(ConsoleHandler(level))
        
        if notif_config.file_enabled:
            level = NotificationLevel[notif_config.file_level]
            self._notification_dispatcher.add_handler(
                FileHandler(notif_config.file_path, level)
            )
        
        if notif_config.webhook_enabled:
            level = NotificationLevel[notif_config.webhook_level]
            self._notification_dispatcher.add_handler(
                WebhookHandler(notif_config.webhook_url, level)
            )


async def run(config_file: Optional[str] = None) -> None:
    """Run the Stream Health Monitor"""
    monitor = StreamHealthMonitor(config_file)
    
    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(monitor.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass
    
    await monitor.start()


def main():
    """CLI entry point"""
    config_file = None
    
    # Check for config file argument
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Stream Health Monitor")
            print("\nUsage: stream-monitor [config_file]")
            print("\nOptions:")
            print("  config_file    Path to configuration YAML file")
            print("  --help, -h     Show this help message")
            sys.exit(0)
        config_file = sys.argv[1]
    
    asyncio.run(run(config_file))


if __name__ == "__main__":
    main()