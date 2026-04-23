"""Configuration management for StreamHealthMonitor"""
import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from dataclasses import dataclass, field


@dataclass
class OBSConfig:
    host: str = "localhost"
    port: int = 4455
    password: str = ""
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10


@dataclass
class SystemConfig:
    poll_interval: int = 5
    obs_process_monitoring: bool = True


@dataclass
class StorageConfig:
    database_path: str = "data/stream_health.db"
    retention_hours: int = 24
    aggregation_intervals: list = field(default_factory=lambda: [5, 60, 300])


@dataclass
class ThresholdConfig:
    dropped_frames_percent: float = 5.0
    cpu_percent: float = 85.0
    memory_percent: float = 90.0
    bitrate_variance_percent: float = 15.0
    network_latency_ms: int = 200
    fps_drop_threshold: int = 5


@dataclass
class AlertConfig:
    enabled: bool = True
    suppression_seconds: int = 300
    thresholds: ThresholdConfig = field(default_factory=ThresholdConfig)


@dataclass
class NotificationConfig:
    console_enabled: bool = True
    console_level: str = "INFO"
    file_enabled: bool = True
    file_path: str = "logs/stream_health.log"
    file_level: str = "DEBUG"
    webhook_enabled: bool = False
    webhook_url: str = ""
    webhook_level: str = "WARNING"


@dataclass
class PlatformConfig:
    douyin_enabled: bool = False
    douyin_poll_interval: int = 30
    bili_enabled: bool = False
    bili_poll_interval: int = 30


@dataclass
class StreamerAIConfig:
    enabled: bool = False
    database_path: str = "../StreamerAI/data/test.db"
    control_table: str = "monitor_commands"


@dataclass
class Config:
    obs: OBSConfig = field(default_factory=OBSConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    streamer_ai: StreamerAIConfig = field(default_factory=StreamerAIConfig)

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load configuration from YAML file"""
        config_path = Path(path)
        if not config_path.exists():
            return cls()
        
        with open(config_path) as f:
            data = yaml.safe_load(f)
        
        if not data:
            return cls()
        
        return cls(
            obs=OBSConfig(**data.get("obs", {})),
            system=SystemConfig(**data.get("system", {})),
            storage=StorageConfig(**data.get("storage", {})),
            alerts=AlertConfig(
                enabled=data.get("alerts", {}).get("enabled", True),
                suppression_seconds=data.get("alerts", {}).get("suppression_seconds", 300),
                thresholds=ThresholdConfig(**data.get("alerts", {}).get("thresholds", {}))
            ),
            notifications=NotificationConfig(
                console_enabled=data.get("notifications", {}).get("console", {}).get("enabled", True),
                console_level=data.get("notifications", {}).get("console", {}).get("level", "INFO"),
                file_enabled=data.get("notifications", {}).get("file", {}).get("enabled", True),
                file_path=data.get("notifications", {}).get("file", {}).get("path", "logs/stream_health.log"),
                file_level=data.get("notifications", {}).get("file", {}).get("level", "DEBUG"),
                webhook_enabled=data.get("notifications", {}).get("webhook", {}).get("enabled", False),
                webhook_url=data.get("notifications", {}).get("webhook", {}).get("url", ""),
                webhook_level=data.get("notifications", {}).get("webhook", {}).get("level", "WARNING")
            ),
            platform=PlatformConfig(
                douyin_enabled=data.get("platform", {}).get("douyin", {}).get("enabled", False),
                douyin_poll_interval=data.get("platform", {}).get("douyin", {}).get("poll_interval", 30),
                bili_enabled=data.get("platform", {}).get("bili", {}).get("enabled", False),
                bili_poll_interval=data.get("platform", {}).get("bili", {}).get("poll_interval", 30)
            ),
            streamer_ai=StreamerAIConfig(
                enabled=data.get("streamer_ai", {}).get("enabled", False),
                database_path=data.get("streamer_ai", {}).get("database_path", "../StreamerAI/data/test.db"),
                control_table=data.get("streamer_ai", {}).get("control_table", "monitor_commands")
            )
        )

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        return cls(
            obs=OBSConfig(
                host=os.getenv("OBS_HOST", "localhost"),
                port=int(os.getenv("OBS_PORT", "4455")),
                password=os.getenv("OBS_PASSWORD", ""),
                reconnect_interval=int(os.getenv("OBS_RECONNECT_INTERVAL", "5")),
                max_reconnect_attempts=int(os.getenv("OBS_MAX_RECONNECT", "10"))
            ),
            system=SystemConfig(
                poll_interval=int(os.getenv("SYSTEM_POLL_INTERVAL", "5")),
                obs_process_monitoring=os.getenv("OBS_PROCESS_MONITORING", "true").lower() == "true"
            )
        )


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def load_config(config_file: Optional[str] = None) -> Config:
    """Load configuration from file or environment"""
    global _config
    if config_file and Path(config_file).exists():
        _config = Config.from_file(config_file)
    else:
        _config = Config.from_env()
    return _config