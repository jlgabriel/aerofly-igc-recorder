from setuptools import setup, find_packages

setup(
    name="aerofly-igc-recorder",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "tkinter",  # Usually comes with Python
        "asyncio",
        "logging",
    ],
    entry_points={
        'console_scripts': [
            'aerofly-igc-recorder=main:main',
        ],
    },
) 