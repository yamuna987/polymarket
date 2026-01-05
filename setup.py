#!/usr/bin/env python3
"""
Setup script for Polymarket Signal Detector
"""

from setuptools import setup, find_packages

setup(
    name="polymarket-signal-detector",
    version="1.0.0",
    description="Real-time trading signal detection for Polymarket",
    author="yamuna987",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "aiohttp>=3.9.0",
        "websockets>=12.0",
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.13.0",
        "cachetools>=5.3.0",
        "asyncio-throttle>=1.0.0",
        "python-dateutil>=2.8.2",
        "pytz>=2024.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.12.0",
            "flake8>=6.1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "polymarket-detect=main:main",
        ],
    },
)
