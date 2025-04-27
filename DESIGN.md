# Aerofly FS4 IGC Recorder - Design Document

## Architecture Overview

The Aerofly FS4 IGC Recorder follows a modular, layered architecture based on the Model-View-Controller (MVC) pattern, with some adaptations for an event-driven system. The application is designed to be maintainable, extensible, and provides a modern graphical user interface.

## Architectural Layers

### 1. Data Layer (Model)

**Location**: `app/data/`

This layer contains the data models and parsers that represent the core data structures used throughout the application:

- **Data Models** (`models.py`): Defines classes for different types of data:
  - `XGPSData`: Position data (latitude, longitude, altitude, etc.)
  - `XATTData`: Attitude data (heading, pitch, roll)
  - `GliderData`: Glider configuration data
  - `UnknownData`: Fallback for unparsed data

- **Data Parsers** (`parser.py`): Converts raw input data to typed objects:
  - `ForeFlightParser`: Parses ForeFlight-compatible data from Aerofly FS4

### 2. I/O Layer

**Location**: `app/io/`

Handles all input/output operations:

- **UDP Receiver** (`udp.py`): Listens for UDP packets from Aerofly FS4
- **IGC Writer** (`igc.py`): Handles writing flight data to IGC files
- **File Management** (`files.py`): Handles file operations, directory creation, etc.

### 3. Core Layer (Controller)

**Location**: `app/core/`

Contains the main business logic:

- **IGC Recorder** (`recorder.py`): Records flight data to IGC files
- **Bridge** (`bridge.py`): Orchestrates the communication between UDP server and IGC recorder
- **Flight Manager** (`flight.py`): Manages flight sessions and related metadata

### 4. UI Layer (View)

**Location**: `app/ui/`

Provides the graphical user interface:

- **Main Window** (`gui.py`): Main application window and core UI functionality
- **Glider Configuration** (`glider_tab.py`): Glider management interface
- **Common Widgets** (`widgets.py`): Reusable UI components

### 5. Utility Layer

**Location**: `app/utils/`

Provides common utilities:

- **Event System** (`events.py`): Observer pattern implementation for component communication
- **Logging** (`logging.py`): Centralized logging functionality
- **Conversion Utilities** (`conversion.py`): Unit conversion helpers

### 6. Configuration Layer

**Location**: `app/config/`

Centralizes application configuration:

- **Constants** (`constants.py`): System-wide constants
- **Settings** (`settings.py`): User-configurable settings
- **Glider Module** (`gliders_module.py`): Glider configuration management

## Communication Flow

1. UDP data is received from Aerofly FS4 via `ForeFlightUDPServer`
2. Data is parsed by `ForeFlightParser` into typed objects
3. An event is published via `EventBus` notifying of new data
4. `IGCRecorder` subscribes to these events and records data to IGC files
5. UI components display status and allow user control

## Event-Driven Communication

The application uses an event bus to facilitate loose coupling between components:

1. Components subscribe to events they are interested in
2. When an event occurs, the event bus notifies all subscribers
3. Subscribers react to events independently

This pattern allows components to be added, removed, or modified without affecting other parts of the system.

## Error Handling Strategy

1. **Defensive Programming**: Each component validates its inputs
2. **Centralized Logging**: All errors are logged with appropriate context
3. **Graceful Degradation**: Components attempt to continue functioning when possible
4. **User Feedback**: Errors relevant to the user experience are displayed in the UI

## Testing Strategy

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test interactions between components
3. **End-to-End Tests**: Test full application workflows

## Design Patterns Used

1. **Singleton**: Used for global services (EventBus, Settings)
2. **Observer**: Used for event-based communication
3. **Factory**: Used for creating data objects
4. **MVC**: Overall architectural pattern
5. **Repository**: Used for data access abstraction