"""
Command-line interface for Aerofly FS4 IGC Recorder.
Provides a text-based interface for controlling the application.
"""

import logging
import asyncio
import sys
import os
from typing import Dict, Any, Optional, List, Tuple
import time
import signal

from ..core.bridge import AeroflyBridge, create_bridge
from ..utils.events import EventType, Event, event_bus, publish_event
from ..config.constants import METERS_TO_FEET, MPS_TO_KTS
from ..config.settings import settings
from ..io.files import open_file_or_directory, get_igc_directory, list_igc_files, get_file_info

# Configure logger
logger = logging.getLogger("aerofly_igc_recorder.ui.cli")


class CLI:
    """
    Command-line interface for Aerofly FS4 IGC Recorder.
    Provides an interactive text-based interface.
    """

    def __init__(self):
        """Initialize the CLI."""
        self.bridge = create_bridge()
        self.running = False
        self.status_task = None
        
        # Register signal handlers for clean shutdown
        self._setup_signal_handlers()
        
        logger.info("CLI initialized")

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        # Handle SIGINT (Ctrl+C) and SIGTERM
        for sig in [signal.SIGINT, signal.SIGTERM]:
            try:
                signal.signal(sig, self._signal_handler)
            except (ValueError, RuntimeError):
                # Signal handler can't be set in this context (e.g., in a thread)
                pass

    def _signal_handler(self, signum, frame) -> None:
        """Handle signals for graceful shutdown."""
        print("\nShutdown requested, cleaning up...")
        # Request shutdown via event
        asyncio.create_task(publish_event(
            EventType.SHUTDOWN_REQUESTED,
            {'signal': signum},
            'CLI'
        ))

    async def run(self) -> None:
        """
        Run the CLI interface.
        This is the main entry point for the CLI.
        """
        print("\n===== Aerofly FS4 IGC Recorder CLI =====\n")
        print("Starting bridge...")

        # Start the bridge
        if not await self.bridge.start():
            print("Failed to start the bridge. Exiting.")
            return

        self.running = True
        print("Bridge started successfully.")
        
        # Start status update task
        self.status_task = asyncio.create_task(self._status_update_loop())
        
        # Subscribe to events
        await event_bus.subscribe(
            EventType.RECORDING_STARTED,
            self._handle_recording_started
        )
        
        await event_bus.subscribe(
            EventType.RECORDING_STOPPED,
            self._handle_recording_stopped
        )
        
        await event_bus.subscribe(
            EventType.ERROR_OCCURRED,
            self._handle_error
        )
        
        await event_bus.subscribe(
            EventType.SHUTDOWN_REQUESTED,
            self._handle_shutdown
        )
        
        # Show help
        self._print_help()
        
        # Main command loop
        try:
            while self.running:
                # Print prompt
                print("\n> ", end="", flush=True)
                
                # Get command from user
                command = await asyncio.get_event_loop().run_in_executor(None, input)
                command = command.strip().lower()
                
                # Process command
                if command == "help" or command == "?":
                    self._print_help()
                    
                elif command == "status":
                    await self._print_status()
                    
                elif command == "start":
                    await self._start_recording()
                    
                elif command == "stop":
                    await self._stop_recording()
                    
                elif command == "dir" or command == "ls":
                    await self._list_igc_files()
                    
                elif command == "open":
                    await self._open_igc_directory()
                    
                elif command == "exit" or command == "quit":
                    print("Exiting...")
                    break
                    
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands.")
        
        except asyncio.CancelledError:
            print("CLI cancelled.")
        except Exception as e:
            logger.error(f"Error in CLI command loop: {e}")
            print(f"Error: {e}")
        finally:
            # Clean up
            await self._cleanup()
            print("CLI exited.")

    async def _status_update_loop(self) -> None:
        """Background task that periodically updates status."""
        try:
            last_status_time = 0
            last_connection_status = False
            
            while self.running:
                try:
                    # Get current time
                    current_time = time.time()
                    
                    # Get status
                    connection_status = self.bridge.get_connection_status()
                    has_connection = connection_status.get('has_connection', False)
                    
                    # Print status update if connection status changes
                    if has_connection != last_connection_status:
                        if has_connection:
                            print("\nConnection with Aerofly FS4 established!")
                        else:
                            print("\nConnection with Aerofly FS4 lost. Make sure the simulator is running.")
                        
                        # Print prompt again
                        print("> ", end="", flush=True)
                        
                    # Update last status
                    last_connection_status = has_connection
                    
                    # Wait before next update
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error in status update loop: {e}")
                    await asyncio.sleep(5)  # Wait longer after error
                    
        except asyncio.CancelledError:
            logger.debug("Status update task cancelled")
            raise

    async def _cleanup(self) -> None:
        """Clean up resources before exiting."""
        self.running = False
        
        # Cancel status task
        if self.status_task:
            self.status_task.cancel()
            try:
                await self.status_task
            except asyncio.CancelledError:
                pass
            
        # Stop the bridge
        if self.bridge:
            await self.bridge.stop()
            
        logger.info("CLI cleanup completed")

    def _print_help(self) -> None:
        """Print help information."""
        print("\nAvailable commands:")
        print("  help       - Show this help")
        print("  status     - Show current status")
        print("  start      - Start recording a flight")
        print("  stop       - Stop recording the current flight")
        print("  dir, ls    - List IGC files")
        print("  open       - Open IGC directory")
        print("  exit, quit - Exit the program")
        print("\nPress Ctrl+C to exit at any time.")

    async def _print_status(self) -> None:
        """Print the current status."""
        try:
            # Get connection status
            connection = self.bridge.get_connection_status()
            
            print("\n----- Connection Status -----")
            if connection.get('has_connection', False):
                print("Connected to Aerofly FS4: YES")
                print(f"Last data received: {connection.get('last_data_seconds_ago', 0):.1f} seconds ago")
                
                # Print latest position if available
                if connection.get('has_gps_data', False):
                    pos = connection.get('latest_position', {})
                    print(f"  Lat: {pos.get('latitude', 0):.6f}° Lon: {pos.get('longitude', 0):.6f}°")
                    print(f"  Alt: {pos.get('altitude', 0) * METERS_TO_FEET:.0f} ft")
                    print(f"  Speed: {pos.get('speed', 0) * MPS_TO_KTS:.1f} kts")
                    
                # Print latest attitude if available
                if connection.get('has_attitude_data', False):
                    att = connection.get('latest_attitude', {})
                    print(f"  Heading: {att.get('heading', 0):.1f}° Pitch: {att.get('pitch', 0):.1f}° Roll: {att.get('roll', 0):.1f}°")
            else:
                print("Connected to Aerofly FS4: NO")
                print("Make sure Aerofly FS4 is running with ForeFlight output enabled")
                print(f"Listening on UDP port {connection.get('port', 49002)}")
                
            # Get recording status
            recording = self.bridge.get_recording_status()
            
            print("\n----- Recording Status -----")
            if recording.get('recording', {}).get('recording', False):
                rec_info = recording.get('recording', {})
                print("Recording: YES")
                print(f"File: {os.path.basename(rec_info.get('filename', ''))}")
                print(f"Duration: {rec_info.get('duration_formatted', '00:00:00')}")
                print(f"Fixes recorded: {rec_info.get('fix_count', 0)}")
            else:
                print("Recording: NO")
                
        except Exception as e:
            logger.error(f"Error displaying status: {e}")
            print(f"Error getting status: {e}")

    async def _start_recording(self) -> None:
        """Start recording a flight."""
        # Check if already recording
        if self.bridge.get_recording_status().get('recording', {}).get('recording', False):
            print("Already recording. Stop the current recording first.")
            return
            
        try:
            # Get pilot info
            print("\nEnter flight details (or press Enter for defaults):")
            pilot_name = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("Pilot name [Simulator Pilot]: ") or "Simulator Pilot"
            )
            
            glider_type = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("Aircraft type [Aerofly FS4]: ") or "Aerofly FS4"
            )
            
            glider_id = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("Registration [SIM]: ") or "SIM"
            )
            
            # Start recording
            print("Starting recording...")
            result = await self.bridge.start_recording(
                pilot_name=pilot_name,
                glider_type=glider_type,
                glider_id=glider_id
            )
            
            if result:
                print(f"Recording started: {os.path.basename(result)}")
            else:
                print("Failed to start recording")
                
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            print(f"Error: {e}")

    async def _stop_recording(self) -> None:
        """Stop recording the current flight."""
        # Check if recording
        if not self.bridge.get_recording_status().get('recording', {}).get('recording', False):
            print("Not recording.")
            return
            
        try:
            print("Stopping recording...")
            result = await self.bridge.stop_recording()
            
            if result:
                print(f"Recording stopped. Flight saved to: {os.path.basename(result)}")
                
                # Ask if user wants to open the directory
                open_it = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("Open IGC directory? (y/n): ").lower().startswith('y')
                )
                
                if open_it:
                    await self._open_igc_directory()
            else:
                print("No flight data was recorded")
                
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            print(f"Error: {e}")

    async def _list_igc_files(self) -> None:
        """List all IGC files in the output directory."""
        try:
            # Get the IGC directory
            igc_dir = get_igc_directory()
            print(f"\nIGC files in {igc_dir}:")
            
            # List files
            igc_files = list_igc_files(igc_dir)
            
            if not igc_files:
                print("No IGC files found")
                return
                
            # Print files
            for i, file in enumerate(igc_files):
                # Get file info
                info = get_file_info(file)
                
                # Format output
                filename = os.path.basename(file)
                size = info.get('size_str', 'Unknown size')
                date = info.get('modified', 'Unknown date')
                
                try:
                    # Try to make the date more readable
                    date_obj = datetime.datetime.fromisoformat(date)
                    date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    pass
                    
                print(f"{i+1}: {filename} ({size}, {date})")
                
        except Exception as e:
            logger.error(f"Error listing IGC files: {e}")
            print(f"Error: {e}")

    async def _open_igc_directory(self) -> None:
        """Open the IGC directory in the system's file explorer."""
        try:
            # Get the IGC directory
            igc_dir = get_igc_directory()
            
            # Open it
            if open_file_or_directory(igc_dir):
                print(f"Opened directory: {igc_dir}")
            else:
                print(f"Failed to open directory: {igc_dir}")
                
        except Exception as e:
            logger.error(f"Error opening IGC directory: {e}")
            print(f"Error: {e}")

    async def _handle_recording_started(self, event: Event) -> None:
        """Handle recording started events."""
        if not event.data:
            return
            
        filename = event.data.get('filename', 'Unknown')
        print(f"\nRecording started: {os.path.basename(filename)}")
        
        # Print prompt again
        print("> ", end="", flush=True)

    async def _handle_recording_stopped(self, event: Event) -> None:
        """Handle recording stopped events."""
        if not event.data:
            return
            
        filename = event.data.get('filename')
        
        if filename:
            print(f"\nRecording stopped. Flight saved to: {os.path.basename(filename)}")
        else:
            print("\nRecording stopped. No flight data was recorded.")
            
        # Print prompt again
        print("> ", end="", flush=True)

    async def _handle_error(self, event: Event) -> None:
        """Handle error events."""
        if not event.data:
            return
            
        message = event.data.get('message', 'Unknown error')
        component = event.data.get('component', 'Unknown')
        
        # Only print errors from certain components to avoid noise
        important_components = ['UDPServer', 'IGCWriter', 'FlightRecorder', 'AeroflyBridge']
        
        if component in important_components:
            print(f"\nError in {component}: {message}")
            
            # Print prompt again
            print("> ", end="", flush=True)

    async def _handle_shutdown(self, event: Event) -> None:
        """Handle shutdown request events."""
        print("\nShutdown requested, exiting...")
        self.running = False


# Factory function to create a CLI instance
def create_cli() -> CLI:
    """
    Create a new CLI instance.
    
    Returns:
        CLI: A new CLI instance
    """
    return CLI()
