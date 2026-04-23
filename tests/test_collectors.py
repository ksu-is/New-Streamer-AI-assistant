"""Tests for collectors"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from stream_monitor.collectors.base import BaseCollector, CollectorMetrics
from stream_monitor.collectors.obs import OBSCollector
from stream_monitor.collectors.system import SystemCollector


class TestCollectorMetrics:
    def test_to_dict(self):
        from datetime import datetime
        metrics = CollectorMetrics(
            timestamp=datetime.now(),
            source="test",
            data={"value": 42}
        )
        result = metrics.to_dict()
        assert result["source"] == "test"
        assert result["data"]["value"] == 42


class TestOBSCollector:
    @pytest.mark.asyncio
    async def test_init(self):
        collector = OBSCollector(poll_interval=2)
        assert collector.name == "obs"
        assert collector.poll_interval == 2
    
    @pytest.mark.asyncio
    async def test_health_check_no_client(self):
        collector = OBSCollector()
        result = await collector.health_check()
        assert result is False


class TestSystemCollector:
    @pytest.mark.asyncio
    async def test_init(self):
        collector = SystemCollector(poll_interval=5)
        assert collector.name == "system"
        assert collector.poll_interval == 5
    
    @pytest.mark.asyncio
    async def test_collect(self):
        collector = SystemCollector()
        await collector.connect()
        metrics = await collector.collect()
        
        assert metrics.source == "system"
        assert "cpu_percent" in metrics.data
        assert "memory_percent" in metrics.data
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        collector = SystemCollector()
        await collector.connect()
        result = await collector.health_check()
        assert result is True