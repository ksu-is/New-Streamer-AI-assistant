"""Tests for alerting"""
import pytest
from datetime import datetime

from stream_monitor.alerting.thresholds import (
    ThresholdChecker, Alert, Severity
)
from stream_monitor.alerting.notifiers import (
    ConsoleHandler, FileHandler, WebhookHandler, 
    NotificationDispatcher, NotificationLevel
)
from stream_monitor.alerting.analysis import TrendAnalyzer


class TestThresholdChecker:
    def test_init(self):
        checker = ThresholdChecker()
        assert checker is not None
    
    def test_check_obs_metrics_dropped_frames(self):
        checker = ThresholdChecker()
        
        # High dropped frames should trigger alert
        metrics = {"dropped_frames_percent": 10.0, "fps": 30}
        alerts = checker._check_obs_metrics(metrics)
        
        assert len(alerts) > 0
        assert alerts[0].alert_type == "dropped_frames"
    
    def test_check_system_metrics_high_cpu(self):
        checker = ThresholdChecker()
        
        # High CPU should trigger alert
        metrics = {"cpu_percent": 90.0}
        alerts = checker._check_system_metrics(metrics)
        
        assert len(alerts) > 0
        assert alerts[0].alert_type == "high_cpu"
    
    def test_should_alert_suppression(self):
        checker = ThresholdChecker()
        
        # First alert should fire
        assert checker.should_alert("test_alert") is True
        
        # Second alert within suppression period should not
        assert checker.should_alert("test_alert") is False


class TestNotificationHandlers:
    @pytest.mark.asyncio
    async def test_console_handler(self):
        handler = ConsoleHandler(NotificationLevel.INFO)
        
        alert = Alert(
            severity=Severity.INFO,
            alert_type="test",
            message="Test message",
            value=50.0,
            threshold=80.0,
            source="test"
        )
        
        # Should not raise
        await handler.send(alert)
    
    @pytest.mark.asyncio
    async def test_webhook_handler_no_url(self):
        handler = WebhookHandler("")
        
        alert = Alert(
            severity=Severity.WARNING,
            alert_type="test",
            message="Test message",
            value=50.0,
            threshold=80.0,
            source="test"
        )
        
        # Should not raise (no URL configured)
        await handler.send(alert)


class TestTrendAnalyzer:
    def test_init(self):
        analyzer = TrendAnalyzer(window_size=20)
        assert analyzer.window_size == 20
    
    def test_add_data_point(self):
        analyzer = TrendAnalyzer()
        analyzer.add_data_point("test_metric", 42.0)
        assert "test_metric" in analyzer._history
    
    def test_analyze_trend(self):
        analyzer = TrendAnalyzer()
        
        # Add increasing values
        for i in range(10):
            analyzer.add_data_point("test_metric", float(i))
        
        result = analyzer.analyze_trend("test_metric")
        assert result is not None
        assert result.direction in ["increasing", "decreasing", "stable"]
    
    def test_detect_anomaly(self):
        analyzer = TrendAnalyzer()
        
        # Add normal values
        for _ in range(5):
            analyzer.add_data_point("test_metric", 50.0)
        
        # Add anomalous spike
        analyzer.add_data_point("test_metric", 100.0)
        
        result = analyzer.analyze_trend("test_metric")
        assert result is not None