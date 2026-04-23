"""Time-series data aggregation"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class MetricsAggregator:
    """Aggregate metrics into different time buckets"""
    
    def __init__(self):
        self._raw_metrics: List[Dict[str, Any]] = []
        self._buckets = {
            5: defaultdict(list),   # 5-second buckets
            60: defaultdict(list),  # 1-minute buckets
            300: defaultdict(list), # 5-minute buckets
        }
    
    def add_metric(self, source: str, data: Dict[str, Any]) -> None:
        """Add a raw metric to be aggregated"""
        self._raw_metrics.append({
            "timestamp": datetime.now(),
            "source": source,
            "data": data
        })
        
        # Keep only last hour of raw data
        cutoff = datetime.now() - timedelta(hours=1)
        self._raw_metrics = [
            m for m in self._raw_metrics 
            if m["timestamp"] > cutoff
        ]
    
    def get_aggregated(
        self, 
        source: str, 
        window_seconds: int,
        minutes: int = 5
    ) -> List[Dict[str, Any]]:
        """Get aggregated metrics for a time window"""
        if window_seconds not in self._buckets:
            return []
        
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        # Filter metrics by source and time
        filtered = [
            m for m in self._raw_metrics
            if m["source"] == source and m["timestamp"] > cutoff
        ]
        
        if not filtered:
            return []
        
        # Group by time bucket
        buckets = defaultdict(list)
        for metric in filtered:
            bucket_time = (
                int(metric["timestamp"].timestamp()) // window_seconds
            ) * window_seconds
            buckets[bucket_time].append(metric)
        
        # Calculate aggregates for each bucket
        result = []
        for bucket_time in sorted(buckets.keys()):
            bucket_data = buckets[bucket_time]
            aggregated = self._aggregate_bucket(bucket_data)
            aggregated["timestamp"] = datetime.fromtimestamp(bucket_time)
            result.append(aggregated)
        
        return result
    
    def _aggregate_bucket(
        self, 
        bucket_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate data within a single bucket"""
        if not bucket_data:
            return {}
        
        # Collect all numeric values
        value_sets: Dict[str, List[float]] = defaultdict(list)
        
        for metric in bucket_data:
            for key, value in metric["data"].items():
                if isinstance(value, (int, float)):
                    value_sets[key].append(value)
        
        # Calculate aggregates
        result = {}
        for key, values in value_sets.items():
            if values:
                result[f"{key}_count"] = len(values)
                result[f"{key}_min"] = min(values)
                result[f"{key}_max"] = max(values)
                result[f"{key}_avg"] = sum(values) / len(values)
                
                # Calculate variance
                avg = result[f"{key}_avg"]
                variance = sum((v - avg) ** 2 for v in values) / len(values)
                result[f"{key}_std"] = variance ** 0.5
        
        return result
    
    def calculate_moving_average(
        self,
        source: str,
        metric: str,
        window_minutes: int = 1
    ) -> float:
        """Calculate moving average for a metric"""
        metrics = self.get_aggregated(source, window_minutes * 60, window_minutes)
        
        values = []
        for m in metrics:
            avg_key = f"{metric}_avg"
            if avg_key in m:
                values.append(m[avg_key])
        
        if not values:
            return 0.0
        
        return sum(values) / len(values)
    
    def detect_anomaly(
        self,
        source: str,
        metric: str,
        threshold_std: float = 2.0
    ) -> bool:
        """Detect if current value is anomalous"""
        metrics = self.get_aggregated(source, 60, 5)  # Last 5 minutes
        
        values = []
        for m in metrics:
            avg_key = f"{metric}_avg"
            if avg_key in m:
                values.append(m[avg_key])
        
        if len(values) < 3:
            return False
        
        # Calculate mean and std
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        
        if std == 0:
            return False
        
        # Check latest value
        latest = values[-1]
        z_score = abs(latest - mean) / std
        
        return z_score > threshold_std