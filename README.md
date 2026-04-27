# Stream Health Monitor

Standalone Python-based stream health monitoring tool that tracks OBS stream quality, system resources, network metrics, and platform analytics. Can optionally integrate with StreamerAI via shared SQLite database for coordinated alerts and control.

## Features

- **OBS WebSocket Integration**: Real-time FPS, bitrate, dropped frames, CPU/memory monitoring
- **System Metrics**: CPU, memory, disk I/O, network interfaces via psutil
- **Threshold Alerts**: Configurable thresholds with INFO/WARNING/CRITICAL severity
- **Multiple Notification Channels**: Console, file logs, Discord/Slack webhooks
- **Trend Analysis**: Moving averages, anomaly detection, issue prediction
- **Optional Platform Integration**: Douyin and Bilibili viewer metrics
- **StreamerAI Integration**: Coordinate AI behavior during stream issues

## Installation

```bash
# Clone the repository
cd StreamHealthMonitor

# Install dependencies with Poetry
poetry install

# Or with pip
pip install -e .
```

## Quick Start

### With Poetry
```bash
poetry install
poetry run stream-monitor
poetry run stream-monitor-dashboard
```

### With pip
```bash
pip install -e .
python -m stream_monitor.main
python -m stream_monitor.ui.cli_dashboard
```

### Using a custom config file
```bash
python -m stream_monitor.main config.yaml
```

## Configuration

Copy `config.yaml.example` to `config.yaml` and modify as needed:

```yaml
obs:
  host: "localhost"
  port: 4455
  password: ""

alerts:
  thresholds:
    dropped_frames_percent: 5
    cpu_percent: 85
    memory_percent: 90

notifications:
  console:
    enabled: true
  webhook:
    enabled: true
    url: "https://discord.com/api/webhooks/..."
```

## Architecture

```
stream_monitor/
├── collectors/       # Data collectors (OBS, system, platform)
├── storage/         # Database and aggregation
├── alerting/        # Threshold checking and notifications
├── integration/     # StreamerAI bridge
└── ui/              # CLI and web dashboards
```

## Modes

1. **Standalone**: Monitor OBS + system metrics only
2. **Platform**: Add `--extras platform` for Douyin/Bili
3. **StreamerAI**: Add `--extras integration` for AI coordination

## License

MIT