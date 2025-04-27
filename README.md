# Aerofly FS4 IGC Recorder

Connect Aerofly FS4 Flight Simulator (Copyright (C) IPACS) and generate IGC flight logs.

Initially designed by Anthropic Claude Sonnet 3.7, with subsequent code improvements developed using Claude 3.5 Sonnet in Cursor IDE.

## Overview

Aerofly FS4 IGC Recorder is a Python application that captures flight data from the Aerofly FS4 flight simulator and records it in the IGC (International Gliding Commission) file format. This allows pilots to analyze their simulated flights with standard IGC-compatible flight analysis tools.

## Features

- Captures live flight data from Aerofly FS4 via UDP
- Records flight data in standard IGC format
- Modern and intuitive graphical user interface
- Customizable settings for pilot name, glider type, etc.
- Built-in glider configuration management
- Automatic file naming and organization

## Requirements

- Python 3.8 or higher
- Aerofly FS4 with ForeFlight output enabled
- Required Python packages:
  - tkinter (for GUI)
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

1. Start the application:
   ```
   python main.py
   ```

2. Configure your pilot details and glider settings
3. Click "Start Recording" to begin recording flight data
4. Fly in Aerofly FS4
5. Click "Stop Recording" when finished

## Configuration

The application settings can be configured through the GUI and are stored in:
- Windows: `%APPDATA%\AeroflyIGCRecorder\settings.json`
- Linux/Mac: `~/.config/aerofly-igc-recorder/settings.json`

## Glider Configuration

The application includes a glider selection system that allows you to:
- Select from available glider models in Aerofly FS4
- View detailed glider information and specifications
- Automatically include the selected glider information in IGC files

## Setup in Aerofly FS4

1. Start Aerofly FS4
2. Configuration in Aerofly FS4 "Miscellaneous settings":
- "Broadcast flight info to IP address" must be set ON
- Configure the Broadcast IP Address to your subnet's directed broadcast address, typically in the format 'xxx.xxx.xxx.255' for standard /24 networks (e.g., 192.168.1.255)
- "Broadcast IP Port" must be set us "49002" (default)
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
- [UDP Protocol](https://support.foreflight.com/hc/en-us/articles/204115005-Flight-Simulator-GPS-Integration-UDP-Protocol) Flight Simulator GPS Integration (UDP Protocol)
- Original development by Juan Luis Gabriel
