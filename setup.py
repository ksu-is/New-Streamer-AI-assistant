"""Setup configuration for pip installation"""
from setuptools import setup, find_packages

setup(
    name="stream-health-monitor",
    version="0.1.0",
    description="Standalone Stream Health Monitoring Tool",
    author="StreamerAI Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "peewee>=3.17.0",
        "psutil>=5.9.0",
        "obsws-python>=1.7.0",
        "rich>=13.7.0",
        "pyyaml>=6.0.0",
        "aiohttp>=3.9.0",
    ],
    extras_require={
        "platform": ["playwright", "blivedm"],
        "dev": ["pytest>=7.4.0", "pytest-asyncio>=0.21.0", "pytest-cov>=4.1.0"],
    },
    entry_points={
        "console_scripts": [
            "stream-monitor=stream_monitor.main:main",
            "stream-monitor-dashboard=stream_monitor.ui.cli_dashboard:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)