#!/usr/bin/env python3

"""
Aerofly FS4 to IGC Recorder - Main entry point
Developed to connect Aerofly FS4 Flight Simulator and generate IGC flight logs
"""

import sys


def main():
    """Main function that starts the application"""
    print("Aerofly FS4 to IGC Recorder")
    print("Initializing...")

    # To be implemented: logic to determine whether to use GUI or CLI
    if "--cli" in sys.argv:
        print("Starting in CLI mode...")
        # TODO: Start CLI
    else:
        print("Starting graphical interface...")
        # TODO: Start GUI


if __name__ == "__main__":
    main()