"""Trend analysis for metrics"""
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TrendResult:
    """Result of trend analysis"""
    metric: str
    direction: str  # "increasing", "decreasing", "stable"
    change_percent: float
    is_anomalous: bool
    prediction: Optional[str]


class TrendAnalyzer:
    """Analyze trends in metrics data"""
    
    def __init__(self, window_size: int = 20):
        self.window_size = window_size
        self._history: Dict[str, deque] = {}
    
    def add_data_point(self, metric: str, value: float) -> None:
        """Add a data point for trend analysis"""
        if metric not in self._history:
            self._history[metric] = deque(maxlen=self.window_size)
        
        self._history[metric].append({
            "value": value,
            "timestamp": datetime.now()
        })
    
    def analyze_trend(self, metric: str) -> Optional[TrendResult]:
        """Analyze trend for a specific metric"""
        if metric not in self._history:
            return None
        
        history = self._history[metric]
        if len(history) < 5:
            return None
        
        values = [h["value"] for h in history]
        
        # Calculate trend direction
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        if avg_first == 0:
            return None
        
        change_percent = ((avg_second - avg_first) / avg_first) * 100
        
        if change_percent > 10:
            direction = "increasing"
        elif change_percent < -10:
            direction = "decreasing"
        else:
            direction = "stable"
        
        # Detect anomalies
        is_anomalous = self._detect_anomaly(values)
        
        # Make prediction
        prediction = self._predict(values)
        
        return TrendResult(
            metric=metric,
            direction=direction,
            change_percent=change_percent,
            is_anomalous=is_anomalous,
            prediction=prediction
        )
    
    def _detect_anomaly(self, values: List[float]) -> bool:
        """Detect if there's an anomaly in recent values"""
        if len(values) < 3:
            return False
        
        # Check for sudden spikes
        recent = values[-3:]
        if len(recent) >= 2:
            for i in range(1, len(recent)):
                change = abs(recent[i] - recent[i-1]) / (recent[i-1] if recent[i-1] != 0 else 1)
                if change > 0.5:  # 50% change
                    return True
        
        return False
    
    def _predict(self, values: List[float]) -> Optional[str]:
        """Make a simple prediction based on trend"""
        if len(values) < 10:
            return None
        
        # Check for memory leak pattern (gradual increase)
        if self._is_monotonic_increase(values):
            return "potential_memory_leak"
        
        # Check for resource degradation
        if values[-1] < values[0] * 0.8:
            return "resource_degradation"
        
        return None
    
    def _is_monotonic_increase(self, values: List[float]) -> bool:
        """Check if values are monotonically increasing"""
        if len(values) < 5:
            return False
        
        increases = 0
        for i in range(1, len(values)):
            if values[i] > values[i-1]:
                increases += 1
        
        return increases > len(values) * 0.7
    
    def get_all_trends(self) -> Dict[str, TrendResult]:
        """Get trend analysis for all tracked metrics"""
        results = {}
        
        for metric in self._history.keys():
            result = self.analyze_trend(metric)
            if result:
                results[metric] = result
        
        return results
    
    def clear_history(self, metric: Optional[str] = None) -> None:
        """Clear history for a metric or all metrics"""
        if metric:
            if metric in self._history:
                self._history[metric].clear()
        else:
            for m in self._history:
                self._history[m].clear()