"""Compatibility shim for older pip versions that lack PEP 660 editable installs."""

from setuptools import find_packages, setup

setup(
    name="northwest-iot-observatory",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"iot_platform": ["web/*"]},
    install_requires=[
        "fastapi>=0.115,<1",
        "paho-mqtt>=2.1,<3",
        "uvicorn[standard]>=0.30,<1",
    ],
    extras_require={
        "dev": [
            "httpx>=0.27,<1",
            "pre-commit>=4,<5",
            "pytest>=8,<10",
            "pytest-cov>=5,<7",
            "ruff>=0.12,<1",
        ]
    },
    entry_points={
        "console_scripts": [
            "iot-server=iot_platform.main:run",
            "iot-simulator=iot_platform.simulator:main",
        ]
    },
    python_requires=">=3.9",
)
