from setuptools import setup, find_packages

setup(
    name="aerofly-igc-recorder",
    version="0.1.0",
    description="Aerofly FS4 IGC Recorder - Connects to Aerofly FS4 Flight Simulator and generates IGC flight logs",
    author="Juan Luis Gabriel",
    url="https://github.com/jlgabriel/aerofly-igc-recorder",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "aerofiles",  # For IGC file handling
    ],
    entry_points={
        'console_scripts': [
            'aerofly-igc-recorder=main:main',
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Games/Entertainment :: Simulation",
        "Environment :: X11 Applications :: Qt",
        "Operating System :: OS Independent",
    ],
) 