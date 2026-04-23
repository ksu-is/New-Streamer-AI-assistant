"""Tests for storage"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from stream_monitor.storage.database import Database, HealthMetrics, StreamAlert
from stream_monitor.storage.aggregator import MetricsAggregator


class TestDatabase:
    @pytest.fixture
    def temp_db(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield db_path
    
    def test_init(self, temp_db):
        db = Database(temp_db)
        assert db._db_path == temp_db
    
    def test_save_metrics(self, temp_db):
        db = Database(temp_db)
        db.connect()
        
        db.save_metrics("test_source", {"metric1": 100, "metric2": 50.5})
        
        metrics = db.get_recent_metrics("test_source", minutes=5)
        assert len(metrics) > 0
        
        db.close()
    
    def test_create_alert(self, temp_db):
        db = Database(temp_db)
        db.connect()
        
        alert = db.create_alert(
            severity="WARNING",
            alert_type="test_alert",
            message="Test message",
            value=75.0,
            threshold=80.0
        )
        
        assert alert.severity == "WARNING"
        assert alert.alert_type == "test_alert"
        
        db.close()
    
    def test_cleanup_old_data(self, temp_db):
        db = Database(temp_db)
        db.connect()
        
        # Should not raise error
        deleted = db.cleanup_old_data(retention_hours=24)
        assert deleted >= 0
        
        db.close()


class TestMetricsAggregator:
    def test_init(self):
        aggregator = MetricsAggregator()
        assert aggregator is not None
    
    def test_add_metric(self):
        aggregator = MetricsAggregator()
        aggregator.add_metric("test", {"value": 42})
        assert len(aggregator._raw_metrics) > 0
    
    def test_calculate_moving_average(self):
        aggregator = MetricsAggregator()
        
        # Add some metrics
        for i in range(10):
            aggregator.add_metric("test", {"value": float(i)})
        
        avg = aggregator.calculate_moving_average("test", "value", window_minutes=1)
        assert avg >= 0