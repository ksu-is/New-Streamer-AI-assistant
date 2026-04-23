"""System metrics collector using psutil"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import psutil

from .base import BaseCollector, CollectorMetrics
from ..config import get_config

logger = logging.getLogger(__name__)


class SystemCollector(BaseCollector):
    """Collector for system-wide and OBS-specific metrics"""
    
    def __init__(self, poll_interval: int = 5):
        super().__init__("system", poll_interval)
        self._config = get_config().system
        self._obs_process: Optional[psutil.Process] = None
    
    async def connect(self) -> bool:
        """Initialize system collector"""
        if self._config.obs_process_monitoring:
            self._find_obs_process()
        logger.info("System collector initialized")
        return True
    
    def _find_obs_process(self) -> None:
        """Find OBS Studio process"""
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info['name'].lower()
                if 'obs' in name and '64' in name:
                    self._obs_process = psutil.Process(proc.info['pid'])
                    logger.info(f"Found OBS process: PID {self._obs_process.pid}")
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        logger.debug("OBS process not found")
    
    async def disconnect(self) -> None:
        """Clean up system collector"""
        self._obs_process = None
    
    async def collect(self) -> CollectorMetrics:
        """Collect system metrics"""
        metrics: Dict[str, Any] = {}
        
        # CPU metrics
        metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        metrics["cpu_per_core"] = psutil.cpu_percent(interval=0.1, percpu=True)
        
        # Memory metrics
        mem = psutil.virtual_memory()
        metrics["memory_total"] = mem.total
        metrics["memory_available"] = mem.available
        metrics["memory_percent"] = mem.percent
        metrics["memory_used"] = mem.used
        
        # Disk I/O
        disk = psutil.disk_usage('/')
        metrics["disk_total"] = disk.total
        metrics["disk_used"] = disk.used
        metrics["disk_percent"] = disk.percent
        
        # Network interfaces
        net_io = psutil.net_io_counters()
        metrics["network_bytes_sent"] = net_io.bytes_sent
        metrics["network_bytes_recv"] = net_io.bytes_recv
        metrics["network_packets_sent"] = net_io.packets_sent
        metrics["network_packets_recv"] = net_io.packets_recv
        metrics["network_errin"] = net_io.errin
        metrics["network_errout"] = net_io.errout
        
        # OBS-specific metrics if available
        if self._obs_process:
            try:
                obs_mem = self._obs_process.memory_info()
                metrics["obs_memory_rss"] = obs_mem.rss
                metrics["obs_memory_vms"] = obs_mem.vms
                metrics["obs_cpu_percent"] = self._obs_process.cpu_percent()
                metrics["obs_num_threads"] = self._obs_process.num_threads()
                metrics["obs_status"] = self._obs_process.status()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                logger.debug("OBS process no longer accessible")
                self._obs_process = None
                metrics["obs_status"] = "not_found"
        else:
            metrics["obs_status"] = "not_running"
        
        return CollectorMetrics(
            timestamp=datetime.now(),
            source="system",
            data=metrics
        )
    
    async def health_check(self) -> bool:
        """Check if system collector is healthy"""
        try:
            psutil.cpu_percent(interval=0.1)
            return True
        except Exception as e:
            self._set_error(f"System health check failed: {e}")
            return False
    
    async def get_network_latency(self) -> int:
        """Get network latency to common endpoints"""
        import socket
        
        try:
            # Simple latency check to Google's DNS
            start = datetime.now()
            socket.create_connection(("8.8.8.8", 53), timeout=1)
            latency = (datetime.now() - start).total_seconds() * 1000
            return int(latency)
        except Exception:
            return -1