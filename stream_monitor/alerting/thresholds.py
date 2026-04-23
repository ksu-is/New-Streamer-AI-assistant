"""Threshold checking for alerts"""
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..config import get_config, ThresholdConfig

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """Represents an alert"""
    severity: Severity
    alert_type: str
    message: str
    value: float
    threshold: float
    source: str


class ThresholdChecker:
    """Check metrics against configured thresholds"""
    
    def __init__(self):
        self._config = get_config()
        self._thresholds = self._config.alerts.thresholds
        self._last_alert_time: Dict[str, datetime] = {}
    
    def check_all(
        self, 
        obs_metrics: Dict[str, Any], 
        system_metrics: Dict[str, Any]
    ) -> List[Alert]:
        """Check all metrics against thresholds"""
        alerts = []
        
        # Check OBS metrics
        alerts.extend(self._check_obs_metrics(obs_metrics))
        
        # Check system metrics
        alerts.extend(self._check_system_metrics(system_metrics))
        
        return alerts
    
    def _check_obs_metrics(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check OBS-specific metrics"""
        alerts = []
        
        # Dropped frames
        if "dropped_frames_percent" in metrics:
            value = metrics["dropped_frames_percent"]
            if value > self._thresholds.dropped_frames_percent:
                alerts.append(Alert(
                    severity=self._get_severity(value, self._thresholds.dropped_frames_percent),
                    alert_type="dropped_frames",
                    message=f"Dropped frames: {value:.1f}% (threshold: {self._thresholds.dropped_frames_percent}%)",
                    value=value,
                    threshold=self._thresholds.dropped_frames_percent,
                    source="obs"
                ))
        
        # FPS
        if "fps" in metrics:
            value = metrics["fps"]
            if value > 0 and value < self._thresholds.fps_drop_threshold:
                alerts.append(Alert(
                    severity=Severity.WARNING,
                    alert_type="low_fps",
                    message=f"Low FPS: {value:.1f} (threshold: {self._thresholds.fps_drop_threshold})",
                    value=value,
                    threshold=self._thresholds.fps_drop_threshold,
                    source="obs"
                ))
        
        return alerts
    
    def _check_system_metrics(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check system-wide metrics"""
        alerts = []
        
        # CPU
        if "cpu_percent" in metrics:
            value = metrics["cpu_percent"]
            if value > self._thresholds.cpu_percent:
                alerts.append(Alert(
                    severity=self._get_severity(value, self._thresholds.cpu_percent),
                    alert_type="high_cpu",
                    message=f"High CPU: {value:.1f}% (threshold: {self._thresholds.cpu_percent}%)",
                    value=value,
                    threshold=self._thresholds.cpu_percent,
                    source="system"
                ))
        
        # Memory
        if "memory_percent" in metrics:
            value = metrics["memory_percent"]
            if value > self._thresholds.memory_percent:
                alerts.append(Alert(
                    severity=self._get_severity(value, self._thresholds.memory_percent),
                    alert_type="high_memory",
                    message=f"High memory: {value:.1f}% (threshold: {self._thresholds.memory_percent}%)",
                    value=value,
                    threshold=self._thresholds.memory_percent,
                    source="system"
                ))
        
        return alerts
    
    def _get_severity(self, value: float, threshold: float) -> Severity:
        """Determine severity based on how much threshold is exceeded"""
        ratio = value / threshold
        
        if ratio >= 1.5:
            return Severity.CRITICAL
        elif ratio >= 1.2:
            return Severity.WARNING
        else:
            return Severity.INFO
    
    def should_alert(self, alert_type: str) -> bool:
        """Check if we should alert (respect suppression period)"""
        config = get_config()
        suppression = config.alerts.suppression_seconds
        
        now = datetime.now()
        
        if alert_type in self._last_alert_time:
            last_time = self._last_alert_time[alert_type]
            if (now - last_time).total_seconds() < suppression:
                return False
        
        self._last_alert_time[alert_type] = now
        return True
    
    def reset_suppression(self) -> None:
        """Reset all suppression timers"""
        self._last_alert_time.clear()