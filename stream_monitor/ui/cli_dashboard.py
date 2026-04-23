"""CLI dashboard using Rich"""
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..config import get_config
from ..collectors.base import CollectorMetrics
from ..alerting.thresholds import Alert

logger = logging.getLogger(__name__)


class CLIDashboard:
    """Rich-based CLI dashboard for real-time metrics"""
    
    def __init__(self):
        self.console = Console()
        self._running = False
        self._last_metrics: Dict[str, CollectorMetrics] = {}
        self._last_alerts: List[Alert] = []
    
    async def start(self) -> None:
        """Start the dashboard"""
        self._running = True
        self.console.print("[bold green]Stream Health Monitor Dashboard[/bold green]")
        self.console.print("Press Ctrl+C to stop\n")
    
    async def stop(self) -> None:
        """Stop the dashboard"""
        self._running = False
        self.console.print("\n[bold red]Dashboard stopped[/bold red]")
    
    def update_metrics(self, metrics: CollectorMetrics) -> None:
        """Update with new metrics"""
        self._last_metrics[metrics.source] = metrics
    
    def update_alerts(self, alerts: List[Alert]) -> None:
        """Update with new alerts"""
        self._last_alerts = alerts
    
    def render(self) -> None:
        """Render the dashboard"""
        self.console.clear()
        
        # Header
        self.console.print(Panel(
            "[bold cyan]Stream Health Monitor[/bold cyan]",
            border_style="cyan"
        ))
        
        # OBS Metrics
        if "obs" in self._last_metrics:
            self._render_obs_metrics()
        
        # System Metrics
        if "system" in self._last_metrics:
            self._render_system_metrics()
        
        # Alerts
        if self._last_alerts:
            self._render_alerts()
        
        # Footer
        self.console.print(f"\n[dim]Last update: {datetime.now().strftime('%H:%M:%S')}[/dim]")
    
    def _render_obs_metrics(self) -> None:
        """Render OBS metrics table"""
        metrics = self._last_metrics["obs"].data
        
        table = Table(title="OBS Metrics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status", justify="center")
        
        # FPS
        fps = metrics.get("fps", 0)
        status = self._get_status(fps, 30, 25)
        table.add_row("FPS", f"{fps:.1f}", status)
        
        # Dropped frames
        dropped = metrics.get("dropped_frames_percent", 0)
        status = self._get_status(dropped, 0, 5, invert=True)
        table.add_row("Dropped Frames", f"{dropped:.1f}%", status)
        
        # CPU
        cpu = metrics.get("cpu_usage", 0)
        status = self._get_status(cpu, 50, 80, invert=True)
        table.add_row("CPU Usage", f"{cpu:.1f}%", status)
        
        # Memory
        mem = metrics.get("memory_usage", 0)
        status = self._get_status(mem, 50, 80, invert=True)
        table.add_row("Memory Usage", f"{mem:.1f}%", status)
        
        # Streaming status
        streaming = "🔴 LIVE" if metrics.get("is_streaming") else "⚫ Offline"
        table.add_row("Stream Status", streaming, "[green]●[/green]")
        
        self.console.print(table)
    
    def _render_system_metrics(self) -> None:
        """Render system metrics table"""
        metrics = self._last_metrics["system"].data
        
        table = Table(title="System Metrics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status", justify="center")
        
        # CPU
        cpu = metrics.get("cpu_percent", 0)
        status = self._get_status(cpu, 50, 85, invert=True)
        table.add_row("System CPU", f"{cpu:.1f}%", status)
        
        # Memory
        mem = metrics.get("memory_percent", 0)
        status = self._get_status(mem, 50, 90, invert=True)
        table.add_row("System Memory", f"{mem:.1f}%", status)
        
        # OBS process
        obs_status = metrics.get("obs_status", "not_found")
        if obs_status == "not_found":
            table.add_row("OBS Process", "Not Running", "[yellow]●[/yellow]")
        else:
            obs_cpu = metrics.get("obs_cpu_percent", 0)
            status = self._get_status(obs_cpu, 30, 60, invert=True)
            table.add_row("OBS CPU", f"{obs_cpu:.1f}%", status)
        
        # Network
        sent = metrics.get("network_bytes_sent", 0)
        recv = metrics.get("network_bytes_recv", 0)
        table.add_row("Network TX", self._format_bytes(sent), "[green]●[/green]")
        table.add_row("Network RX", self._format_bytes(recv), "[green]●[/green]")
        
        self.console.print(table)
    
    def _render_alerts(self) -> None:
        """Render active alerts"""
        table = Table(title="Active Alerts", show_header=True, header_style="bold red")
        table.add_column("Severity", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Message", style="white")
        
        for alert in self._last_alerts[-5:]:  # Show last 5
            severity_style = {
                "INFO": "[blue]",
                "WARNING": "[yellow]",
                "CRITICAL": "[red bold]",
            }
            style = severity_style.get(alert.severity.value, "")
            table.add_row(
                f"{style}{alert.severity.value}[/]",
                alert.alert_type,
                alert.message
            )
        
        self.console.print(table)
    
    def _get_status(
        self, 
        value: float, 
        good_threshold: float, 
        bad_threshold: float,
        invert: bool = False
    ) -> str:
        """Get status indicator"""
        if invert:
            good, bad = bad_threshold, good_threshold
        else:
            good, bad = good_threshold, bad_threshold
        
        if value <= good:
            return "[green]●[/green]"
        elif value <= bad:
            return "[yellow]●[/yellow]"
        else:
            return "[red]●[/red]"
    
    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human readable"""
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} TB"


async def main():
    """CLI dashboard entry point"""
    dashboard = CLIDashboard()
    await dashboard.start()
    
    try:
        while dashboard._running:
            dashboard.render()
            await asyncio.sleep(2)
    except KeyboardInterrupt:
        await dashboard.stop()


if __name__ == "__main__":
    asyncio.run(main())