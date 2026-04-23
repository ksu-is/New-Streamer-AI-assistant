"""Database models and storage layer using Peewee"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from peewee import (
    Model, AutoField, CharField, DateTimeField, DoubleField, 
    IntegerField, BooleanField, TextField, SQL
)
from playhouse.sqlite_ext import SqliteExtDatabase

from ..config import get_config

logger = logging.getLogger(__name__)


class HealthMetrics(Model):
    """Store health metrics from collectors"""
    id = AutoField()
    timestamp = DateTimeField(index=True)
    source = CharField(max_length=50)
    metric_type = CharField(max_length=100)
    value = DoubleField()
    unit = CharField(max_length=20, null=True)
    
    class Meta:
        table_name = "health_metrics"
        indexes = (
            (("timestamp", "source"), False),
        )


class StreamAlert(Model):
    """Store stream alerts"""
    id = AutoField()
    timestamp = DateTimeField(index=True)
    severity = CharField(max_length=20)  # INFO, WARNING, CRITICAL
    alert_type = CharField(max_length=100)
    message = TextField()
    value = DoubleField(null=True)
    threshold = DoubleField(null=True)
    is_active = BooleanField(default=True)
    resolved_at = DateTimeField(null=True)
    
    class Meta:
        table_name = "stream_alerts"
        indexes = (
            (("timestamp", "severity"), False),
        )


class StreamSession(Model):
    """Track stream sessions"""
    id = AutoField()
    start_time = DateTimeField()
    end_time = DateTimeField(null=True)
    platform = CharField(max_length=50, null=True)
    is_active = BooleanField(default=True)
    notes = TextField(null=True)
    
    class Meta:
        table_name = "stream_sessions"


class MonitorCommand(Model):
    """Commands from monitor to StreamerAI"""
    id = AutoField()
    timestamp = DateTimeField(default=datetime.now)
    command_type = CharField(max_length=50)  # PAUSE_AI, RESUME_AI, etc.
    status = CharField(max_length=20, default="pending")  # pending, processed, failed
    processed_at = DateTimeField(null=True)
    
    class Meta:
        table_name = "monitor_commands"


class Database:
    """Database manager for StreamHealthMonitor"""
    
    def __init__(self, db_path: Optional[str] = None):
        self._db: Optional[SqliteExtDatabase] = None
        self._db_path = db_path or get_config().storage.database_path
    
    def connect(self) -> None:
        """Initialize database connection"""
        # Create directory if needed
        db_file = Path(self._db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Enable WAL mode for concurrent access
        self._db = SqliteExtDatabase(
            self._db_path,
            pragmas={
                "journal_mode": "WAL",
                "foreign_keys": 1,
            }
        )
        
        # Bind models to database
        self._bind_models()
        
        # Create tables
        self._db.create_tables()
        
        logger.info(f"Database initialized at {self._db_path}")
    
    def _bind_models(self) -> None:
        """Bind Peewee models to database"""
        for model in [HealthMetrics, StreamAlert, StreamSession, MonitorCommand]:
            model._meta.database = self._db
    
    def close(self) -> None:
        """Close database connection"""
        if self._db:
            self._db.close()
            self._db = None
    
    def save_metrics(self, source: str, data: Dict[str, Any]) -> None:
        """Save metrics to database"""
        if not self._db:
            return
        
        timestamp = datetime.now()
        
        with self._db.atomic():
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    HealthMetrics.create(
                        timestamp=timestamp,
                        source=source,
                        metric_type=key,
                        value=float(value),
                        unit=self._get_unit(key)
                    )
    
    def _get_unit(self, metric_type: str) -> Optional[str]:
        """Get unit for metric type"""
        units = {
            "fps": "fps",
            "cpu_percent": "%",
            "memory_percent": "%",
            "dropped_frames_percent": "%",
            "network_latency_ms": "ms",
            "memory_used": "bytes",
            "obs_memory_rss": "bytes",
        }
        return units.get(metric_type)
    
    def get_recent_metrics(
        self, 
        source: str, 
        minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """Get recent metrics for a source"""
        if not self._db:
            return []
        
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        query = (
            HealthMetrics
            .select()
            .where(
                (HealthMetrics.source == source) &
                (HealthMetrics.timestamp >= cutoff)
            )
            .order_by(HealthMetrics.timestamp)
        )
        
        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "metric_type": m.metric_type,
                "value": m.value,
                "unit": m.unit
            }
            for m in query
        ]
    
    def create_alert(
        self,
        severity: str,
        alert_type: str,
        message: str,
        value: Optional[float] = None,
        threshold: Optional[float] = None
    ) -> StreamAlert:
        """Create a new alert"""
        return StreamAlert.create(
            timestamp=datetime.now(),
            severity=severity,
            alert_type=alert_type,
            message=message,
            value=value,
            threshold=threshold,
            is_active=True
        )
    
    def resolve_alert(self, alert_id: int) -> None:
        """Mark an alert as resolved"""
        StreamAlert.update(
            is_active=False,
            resolved_at=datetime.now()
        ).where(StreamAlert.id == alert_id).execute()
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts"""
        query = (
            StreamAlert
            .select()
            .where(StreamAlert.is_active == True)
            .order_by(StreamAlert.timestamp.desc())
        )
        
        return [
            {
                "id": a.id,
                "timestamp": a.timestamp.isoformat(),
                "severity": a.severity,
                "alert_type": a.alert_type,
                "message": a.message,
                "value": a.value,
                "threshold": a.threshold
            }
            for a in query
        ]
    
    def cleanup_old_data(self, retention_hours: int = 24) -> int:
        """Clean up metrics older than retention period"""
        if not self._db:
            return 0
        
        cutoff = datetime.now() - timedelta(hours=retention_hours)
        
        deleted = (
            HealthMetrics
            .delete()
            .where(HealthMetrics.timestamp < cutoff)
            .execute()
        )
        
        # Also clean up old resolved alerts
        StreamAlert.delete().where(
            (StreamAlert.resolved_at.is_null(False)) &
            (StreamAlert.resolved_at < cutoff)
        ).execute()
        
        logger.info(f"Cleaned up {deleted} old metrics")
        return deleted
    
    def write_command(self, command_type: str) -> MonitorCommand:
        """Write a command for StreamerAI"""
        return MonitorCommand.create(
            command_type=command_type,
            status="pending"
        )
    
    def get_pending_commands(self) -> List[Dict[str, Any]]:
        """Get pending commands for StreamerAI"""
        query = (
            MonitorCommand
            .select()
            .where(MonitorCommand.status == "pending")
            .order_by(MonitorCommand.timestamp)
        )
        
        return [
            {
                "id": c.id,
                "timestamp": c.timestamp.isoformat(),
                "command_type": c.command_type
            }
            for c in query
        ]
    
    def mark_command_processed(self, command_id: int) -> None:
        """Mark a command as processed"""
        MonitorCommand.update(
            status="processed",
            processed_at=datetime.now()
        ).where(MonitorCommand.id == command_id).execute()


# Global database instance
_db: Optional[Database] = None


def get_database() -> Database:
    """Get the global database instance"""
    global _db
    if _db is None:
        _db = Database()
        _db.connect()
    return _db


def close_database() -> None:
    """Close the global database"""
    global _db
    if _db:
        _db.close()
        _db = None