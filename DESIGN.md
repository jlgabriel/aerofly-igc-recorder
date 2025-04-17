# Aerofly FS4 to IGC Recorder - Architecture Design

## Overview
This document describes the architecture of the Aerofly FS4 to IGC Recorder software, a program that connects the Aerofly FS4 flight simulator with an IGC file recording system to register simulated flights.

## Layered Architecture
The application is organized following a layered architecture that clearly separates concerns:

### Data Layer
- Definition of data models and structures
- Conversion between different data formats
- Data validation

### I/O Layer
- Communication with external sources (UDP, files)
- Abstraction over specific protocols
- Handling of connection and format errors

### Business Logic Layer
- Flight data processing
- IGC record generation
- Coordinating data flows between components

### Presentation Layer
- User interfaces (GUI and CLI)
- Data and state presentation
- User event handling

## Directory Structure
aerofly-igc-recorder/
├── app/                    # Main application code

│   ├── config/             # Centralized configuration

│   ├── core/               # Core application logic

│   ├── data/               # Data models and parsers

│   ├── io/                 # Input/output (UDP, files)

│   ├── ui/                 # User interfaces

│   └── utils/              # Common utilities

├── tests/                  # Unit and integration tests

└── main.py                 # Main entry point

## Main Components

### app/config/
Centralizes application configuration, allowing customization without modifying code.
- `settings.py` - Configurable values with defaults
- `constants.py` - Constants used throughout the application

### app/data/
Contains the representation of data within the application.
- `models.py` - Dataclasses representing the main entities
- `parsers.py` - Converters between external and internal formats

### app/io/
Handles communication with external systems.
- `udp_server.py` - UDP server to receive ForeFlight data
- `file_manager.py` - IGC file management

### app/core/
Implements the main application logic.
- `recorder.py` - Flight data recording to IGC format
- `bridge.py` - Orchestration between components

### app/ui/
User interfaces and presentation.
- `gui.py` - Graphical interface based on tkinter
- `cli.py` - Command-line interface

### app/utils/
Common utilities used across different components.
- `events.py` - Inter-component event system
- `converters.py` - Unit conversions and formatting
- `logging.py` - Centralized logging system

## Design Patterns

### Observer Pattern
Used for communication between components, especially for updating the UI when data changes.

### Dependency Injection
Components receive their dependencies instead of creating them directly, facilitating testing and flexibility.

### Facade Pattern
`AeroflyToIGCBridge` acts as a facade, providing a simplified API over the internal complexity.

## Future Extension System
A plugin system is planned to allow:
- Support for different flight simulators
- Additional output formats
- Custom visualizations