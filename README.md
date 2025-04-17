# Aerofly FS4 IGC Recorder

Connect Aerofly FS4 Flight Simulator and generate IGC flight logs.

## Overview

Aerofly FS4 IGC Recorder is a Python application that captures flight data from the Aerofly FS4 flight simulator and records it in the IGC (International Gliding Commission) file format. This allows pilots to analyze their simulated flights with standard IGC-compatible flight analysis tools.

## Features

- Captures live flight data from Aerofly FS4 via UDP
- Records flight data in standard IGC format
- Provides both GUI and CLI interfaces
- Customizable settings for pilot name, glider type, etc.
- Automatic file naming and organization

## Requirements

- Python 3.8 or higher
- Aerofly FS4 with ForeFlight output enabled
- Required Python packages:
  - tkinter (for GUI mode)
  - aerofiles (for IGC file handling)
  - asyncio

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/jlgabriel/aerofly-igc-recorder.git
   cd aerofly-igc-recorder
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### GUI Mode

1. Start the application:
   ```
   python main.py
   ```

2. Configure your pilot details
3. Click "Start Recording" to begin recording flight data
4. Fly in Aerofly FS4
5. Click "Stop Recording" when finished

### CLI Mode

1. Start the application in CLI mode:
   ```
   python main.py --cli
   ```

2. Use the following commands:
   - `start` - Start recording
   - `stop` - Stop recording
   - `status` - Show connection status
   - `exit` - Exit program

## Configuration

The application settings can be found in `~/.config/aerofly-igc-recorder/settings.json` (Linux/Mac) or `%APPDATA%\AeroflyIGCRecorder\settings.json` (Windows).

You can also specify settings via command-line arguments:

```
python main.py --port 49002 --output-dir ~/Documents/AeroflyIGC --log-level DEBUG
```

## Setup in Aerofly FS4

1. Start Aerofly FS4
2. Enable "Output data to ForeFlight" in settings
3. Make sure your firewall allows UDP on port 49002

## IGC File Output

IGC files are saved to:
- Windows: `Documents\AeroflyIGC\`
- Mac/Linux: `~/Documents/AeroflyIGC/`

## Development

The project structure follows a modular design:

```
aerofly-igc-recorder/
├── app/                    # Application code
│   ├── config/             # Configuration
│   ├── core/               # Core logic
│   ├── data/               # Data models
│   ├── io/                 # I/O operations
│   ├── ui/                 # User interfaces
│   └── utils/              # Utilities
├── tests/                  # Tests
└── main.py                 # Entry point
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Aerofly FS4](https://www.aerofly.com/) for the flight simulator
- [aerofiles](https://github.com/Turbo87/aerofiles) library for IGC file handling
- Original development by Juan Luis Gabriel