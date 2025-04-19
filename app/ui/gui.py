"""
Graphical user interface for Aerofly FS4 IGC Recorder.
Provides a Tkinter-based GUI for controlling the application.
"""

import logging
import asyncio
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font as tkfont
import threading
import sys
import os
from typing import Dict, Any, Optional, List, Tuple, Union, Callable
import datetime
import time
import queue

from ..core.bridge import AeroflyBridge, create_bridge
from ..utils.events import EventType, Event, event_bus, publish_event
from ..config.constants import (
    METERS_TO_FEET, MPS_TO_KTS, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    GUI_REFRESH_RATE_MS, GUI_FONT_FAMILY, GUI_FONT_SIZE, APP_NAME, APP_VERSION
)
from ..config.settings import settings
from ..io.files import open_file_or_directory, get_igc_directory, list_igc_files

# Configure logger
logger = logging.getLogger("aerofly_igc_recorder.ui.gui")


class AsyncTkinterLoop:
    """
    Helper class to integrate asyncio with Tkinter.
    Allows running asyncio tasks in a Tkinter application.
    """

    def __init__(self, root):
        """
        Initialize the AsyncTkinterLoop.

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Queue for callbacks from asyncio to Tkinter
        self.callback_queue = queue.Queue()

        # Start checking the queue
        self.schedule_check_queue()

    def schedule_check_queue(self) -> None:
        """Schedule the next queue check."""
        self.root.after(50, self.check_queue)

    def check_queue(self) -> None:
        """Process callbacks from asyncio thread to Tkinter thread."""
        try:
            # Process all callbacks in the queue
            while not self.callback_queue.empty():
                callback, args, kwargs = self.callback_queue.get_nowait()
                callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in callback queue: {e}")
        finally:
            # Schedule the next check
            self.schedule_check_queue()

    def start(self) -> None:
        """Start the asyncio event loop in a background thread."""
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self) -> None:
        """Run the asyncio event loop."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def stop(self) -> None:
        """Stop the asyncio event loop."""
        if hasattr(self, 'loop') and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)

    def create_task(self, coro) -> asyncio.Task:
        """
        Create an asyncio task in the event loop.

        Args:
            coro: Coroutine to run

        Returns:
            asyncio.Task: The created task
        """
        if hasattr(self, 'loop'):
            return asyncio.run_coroutine_threadsafe(coro, self.loop)
        else:
            raise RuntimeError("AsyncTkinterLoop not initialized")

    def call_soon_in_main_thread(self, callback, *args, **kwargs) -> None:
        """
        Schedule a callback to run in the main (Tkinter) thread.

        Args:
            callback: Function to call
            *args: Positional arguments for the callback
            **kwargs: Keyword arguments for the callback
        """
        self.callback_queue.put((callback, args, kwargs))


class GUI:
    """
    Graphical user interface for Aerofly FS4 IGC Recorder.
    Uses Tkinter for the UI components.
    """

    def __init__(self):
        """Initialize the GUI."""
        self.root = None
        self.bridge = None
        self.async_loop = None
        self.running = False

        # Tkinter variables for UI state
        self.tk_vars = {}

        # UI components
        self.components = {}

        # Event subscription tasks
        self.event_tasks = []

        logger.info("GUI initialized")

    async def run(self) -> None:
        """
        Run the GUI.
        This is the main entry point for the GUI.
        """
        # Create the Tkinter root window
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")

        # Initialize AsyncTkinterLoop to integrate asyncio with Tkinter
        self.async_loop = AsyncTkinterLoop(self.root)
        self.async_loop.start()

        # Create bridge
        self.bridge = create_bridge()

        # Set up Tkinter variables
        self._setup_tk_variables()

        # Set up the UI
        self._setup_ui()

        # Set up window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start the application
        self.async_loop.create_task(self._start_application())

        # Start Tkinter main loop
        self.running = True
        self.root.mainloop()

        # Clean up after main loop ends
        self.async_loop.create_task(self._cleanup())

        # Wait for cleanup to complete
        time.sleep(0.5)

        # Stop asyncio loop
        self.async_loop.stop()

        logger.info("GUI exited")

    def _setup_tk_variables(self) -> None:
        """Set up Tkinter variables for UI state."""
        # Connection status
        self.tk_vars['connection_status'] = tk.StringVar(self.root, "Disconnected")
        self.tk_vars['connection_color'] = tk.StringVar(self.root, "red")

        # Recording status
        self.tk_vars['recording_status'] = tk.StringVar(self.root, "Not Recording")
        self.tk_vars['recording_color'] = tk.StringVar(self.root, "gray")
        self.tk_vars['fix_count'] = tk.StringVar(self.root, "0")
        self.tk_vars['duration'] = tk.StringVar(self.root, "00:00:00")

        # Position data
        self.tk_vars['latitude'] = tk.StringVar(self.root, "0.000000")
        self.tk_vars['longitude'] = tk.StringVar(self.root, "0.000000")
        self.tk_vars['altitude'] = tk.StringVar(self.root, "0")
        self.tk_vars['speed'] = tk.StringVar(self.root, "0")
        self.tk_vars['track'] = tk.StringVar(self.root, "0")

        # Attitude data
        self.tk_vars['heading'] = tk.StringVar(self.root, "0")
        self.tk_vars['pitch'] = tk.StringVar(self.root, "0")
        self.tk_vars['roll'] = tk.StringVar(self.root, "0")

        # Flight details
        self.tk_vars['pilot_name'] = tk.StringVar(self.root, settings.get('default_pilot_name', "Simulator Pilot"))
        self.tk_vars['glider_type'] = tk.StringVar(self.root, settings.get('default_glider_type', "Aerofly FS4"))
        self.tk_vars['glider_id'] = tk.StringVar(self.root, settings.get('default_glider_id', "SIM"))

        # Status message
        self.tk_vars['status_message'] = tk.StringVar(self.root, "Initializing...")

    def _setup_ui(self) -> None:
        """Set up the user interface components."""
        # Configure grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # Create status bar at the top
        self._create_status_bar()

        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=1, column=0, sticky="nsew")
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, sticky="nsew")
        self.components['notebook'] = notebook

        # Create tabs
        self._create_main_tab(notebook)
        self._create_settings_tab(notebook)
        self._create_files_tab(notebook)
        self._create_about_tab(notebook)

        # Create control bar at the bottom
        self._create_control_bar()

    def _create_status_bar(self) -> None:
        """Create the status bar at the top of the window."""
        status_frame = ttk.Frame(self.root, padding="5")
        status_frame.grid(row=0, column=0, sticky="ew")
        status_frame.columnconfigure(1, weight=1)

        # Status label
        status_label = ttk.Label(
            status_frame,
            textvariable=self.tk_vars['status_message'],
            font=tkfont.Font(size=10)
        )
        status_label.grid(row=0, column=0, sticky="w", padx=5)

        # Center spacer
        spacer = ttk.Frame(status_frame)
        spacer.grid(row=0, column=1, sticky="ew")

        # Connection status
        connection_frame = ttk.Frame(status_frame)
        connection_frame.grid(row=0, column=2, sticky="e")

        ttk.Label(
            connection_frame,
            text="Connection:"
        ).pack(side="left", padx=(0, 5))

        connection_status = ttk.Label(
            connection_frame,
            textvariable=self.tk_vars['connection_status'],
            foreground="red",
            font=tkfont.Font(size=10, weight="bold")
        )
        connection_status.pack(side="right")
        self.components['connection_status'] = connection_status

        # Update the foreground color when it changes
        def update_connection_color(*args):
            color = self.tk_vars['connection_color'].get()
            connection_status.configure(foreground=color)

        self.tk_vars['connection_color'].trace_add('write', update_connection_color)

    def _create_main_tab(self, notebook) -> None:
        """Create the main tab with flight information."""
        main_frame = ttk.Frame(notebook, padding="10")
        notebook.add(main_frame, text="Flight")

        main_frame.columnconfigure(1, weight=1)

        # Flight info frame
        info_frame = ttk.LabelFrame(main_frame, text="Flight Information", padding="10")
        info_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)

        # Position data
        position_frame = ttk.LabelFrame(main_frame, text="Position Data", padding="10")
        position_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(0, 10))

        # Attitude data
        attitude_frame = ttk.LabelFrame(main_frame, text="Attitude Data", padding="10")
        attitude_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=(0, 10))

        # Recording section
        recording_frame = ttk.LabelFrame(main_frame, text="Recording", padding="10")
        recording_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        recording_frame.columnconfigure(1, weight=1)

        # Fill flight info frame
        row = 0

        # Recording status
        ttk.Label(info_frame, text="Status:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        recording_status = ttk.Label(
            info_frame,
            textvariable=self.tk_vars['recording_status'],
            foreground="gray",
            font=tkfont.Font(weight="bold")
        )
        recording_status.grid(row=row, column=1, sticky="w", padx=5, pady=2)
        self.components['recording_status'] = recording_status

        # Update the foreground color when it changes
        def update_recording_color(*args):
            color = self.tk_vars['recording_color'].get()
            recording_status.configure(foreground=color)

        self.tk_vars['recording_color'].trace_add('write', update_recording_color)

        row += 1

        # Duration
        ttk.Label(info_frame, text="Duration:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(
            info_frame,
            textvariable=self.tk_vars['duration'],
            font=tkfont.Font(family="Courier", size=10)
        ).grid(row=row, column=1, sticky="w", padx=5, pady=2)

        row += 1

        # Fix count
        ttk.Label(info_frame, text="Fixes (Tracking Points):").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(
            info_frame,
            textvariable=self.tk_vars['fix_count']
        ).grid(row=row, column=1, sticky="w", padx=5, pady=2)

        # Fill position frame
        row = 0

        # Latitude
        ttk.Label(position_frame, text="Latitude:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(
            position_frame,
            textvariable=self.tk_vars['latitude'],
            width=12
        ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(position_frame, text="°").grid(row=row, column=2, sticky="w", pady=2)

        row += 1

        # Longitude
        ttk.Label(position_frame, text="Longitude:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(
            position_frame,
            textvariable=self.tk_vars['longitude'],
            width=12
        ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(position_frame, text="°").grid(row=row, column=2, sticky="w", pady=2)

        row += 1

        # Altitude
        ttk.Label(position_frame, text="Altitude:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(
            position_frame,
            textvariable=self.tk_vars['altitude'],
            width=8
        ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(position_frame, text="ft").grid(row=row, column=2, sticky="w", pady=2)

        row += 1

        # Speed
        ttk.Label(position_frame, text="Speed:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(
            position_frame,
            textvariable=self.tk_vars['speed'],
            width=8
        ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(position_frame, text="kts").grid(row=row, column=2, sticky="w", pady=2)

        row += 1

        # Track
        ttk.Label(position_frame, text="Track:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(
            position_frame,
            textvariable=self.tk_vars['track'],
            width=8
        ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(position_frame, text="°").grid(row=row, column=2, sticky="w", pady=2)

        # Fill attitude frame
        row = 0

        # Heading
        ttk.Label(attitude_frame, text="Heading:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(
            attitude_frame,
            textvariable=self.tk_vars['heading'],
            width=8
        ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(attitude_frame, text="°").grid(row=row, column=2, sticky="w", pady=2)

        row += 1

        # Pitch
        ttk.Label(attitude_frame, text="Pitch:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(
            attitude_frame,
            textvariable=self.tk_vars['pitch'],
            width=8
        ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(attitude_frame, text="°").grid(row=row, column=2, sticky="w", pady=2)

        row += 1

        # Roll
        ttk.Label(attitude_frame, text="Roll:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(
            attitude_frame,
            textvariable=self.tk_vars['roll'],
            width=8
        ).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(attitude_frame, text="°").grid(row=row, column=2, sticky="w", pady=2)

        # Fill recording frame
        row = 0

        # Pilot name
        ttk.Label(recording_frame, text="Pilot Name:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(
            recording_frame,
            textvariable=self.tk_vars['pilot_name'],
            width=30
        ).grid(row=row, column=1, sticky="ew", padx=5, pady=2)

        row += 1

        # Glider type
        ttk.Label(recording_frame, text="Aircraft Type:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(
            recording_frame,
            textvariable=self.tk_vars['glider_type'],
            width=30
        ).grid(row=row, column=1, sticky="ew", padx=5, pady=2)

        row += 1

        # Registration
        ttk.Label(recording_frame, text="Registration:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(
            recording_frame,
            textvariable=self.tk_vars['glider_id'],
            width=30
        ).grid(row=row, column=1, sticky="ew", padx=5, pady=2)

    def _create_settings_tab(self, notebook) -> None:
        """Create the settings tab."""
        settings_frame = ttk.Frame(notebook, padding="10")
        notebook.add(settings_frame, text="Settings")

        settings_frame.columnconfigure(1, weight=1)

        # UDP settings
        udp_frame = ttk.LabelFrame(settings_frame, text="UDP Settings", padding="10")
        udp_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        udp_frame.columnconfigure(1, weight=1)

        # UDP port
        ttk.Label(udp_frame, text="UDP Port:").grid(row=0, column=0, sticky="w", padx=5, pady=2)

        # Create a StringVar for the port
        port_var = tk.StringVar(self.root, str(settings.get('udp_port')))
        self.tk_vars['udp_port'] = port_var

        port_entry = ttk.Entry(
            udp_frame,
            textvariable=port_var,
            width=10
        )
        port_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        # Button to save port
        ttk.Button(
            udp_frame,
            text="Change Port",
            command=self._change_udp_port
        ).grid(row=0, column=2, padx=5, pady=2)

        # File settings
        file_frame = ttk.LabelFrame(settings_frame, text="File Settings", padding="10")
        file_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        # IGC directory
        ttk.Label(file_frame, text="IGC Directory:").grid(row=0, column=0, sticky="w", padx=5, pady=2)

        # Create a StringVar for the directory
        dir_var = tk.StringVar(self.root, settings.get('igc_directory'))
        self.tk_vars['igc_directory'] = dir_var

        # Directory display (read-only)
        dir_entry = ttk.Entry(
            file_frame,
            textvariable=dir_var,
            width=40,
            state="readonly"
        )
        dir_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        # Button to browse for directory
        ttk.Button(
            file_frame,
            text="Browse...",
            command=self._browse_igc_directory_settings
        ).grid(row=0, column=2, padx=5, pady=2)

        # Recording settings
        rec_frame = ttk.LabelFrame(settings_frame, text="Recording Settings", padding="10")
        rec_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        rec_frame.columnconfigure(1, weight=1)

        # Recording interval
        ttk.Label(rec_frame, text="Recording Interval:").grid(row=0, column=0, sticky="w", padx=5, pady=2)

        # Create a StringVar for the interval
        interval_var = tk.StringVar(self.root, str(settings.get('recording_interval')))
        self.tk_vars['recording_interval'] = interval_var

        interval_entry = ttk.Entry(
            rec_frame,
            textvariable=interval_var,
            width=10
        )
        interval_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(rec_frame, text="seconds").grid(row=0, column=2, sticky="w", pady=2)

        # Save settings button
        ttk.Button(
            settings_frame,
            text="Save Settings",
            command=self._save_settings
        ).grid(row=3, column=0, columnspan=2, pady=10)

    def _create_files_tab(self, notebook) -> None:
        """Create the files tab with IGC file listing."""
        files_frame = ttk.Frame(notebook, padding="10")
        notebook.add(files_frame, text="Files")

        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(1, weight=1)

        # Header
        header_frame = ttk.Frame(files_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        header_frame.columnconfigure(0, weight=1)

        ttk.Label(
            header_frame,
            text="IGC Files:",
            font=tkfont.Font(size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        # Refresh button
        ttk.Button(
            header_frame,
            text="Refresh",
            command=self._refresh_file_list
        ).grid(row=0, column=1, padx=5)

        # File list
        file_frame = ttk.Frame(files_frame, relief="sunken", borderwidth=1)
        file_frame.grid(row=1, column=0, sticky="nsew")
        file_frame.columnconfigure(0, weight=1)
        file_frame.rowconfigure(0, weight=1)

        # Create a treeview for the file list
        columns = ("filename", "date", "size")
        file_tree = ttk.Treeview(file_frame, columns=columns, show="headings")
        file_tree.grid(row=0, column=0, sticky="nsew")
        self.components['file_tree'] = file_tree

        # Set up scrollbar
        scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=file_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        file_tree.configure(yscrollcommand=scrollbar.set)

        # Set up columns
        file_tree.heading("filename", text="Filename")
        file_tree.heading("date", text="Date")
        file_tree.heading("size", text="Size")

        file_tree.column("filename", width=250)
        file_tree.column("date", width=150)
        file_tree.column("size", width=100)

        # Bind double-click to open file
        file_tree.bind("<Double-1>", self._on_file_double_click)

        # Button frame
        button_frame = ttk.Frame(files_frame)
        button_frame.grid(row=2, column=0, sticky="ew", pady=5)

        # Open file button
        ttk.Button(
            button_frame,
            text="Open",
            command=self._open_selected_file
        ).pack(side="left", padx=5)

        # Open directory button
        ttk.Button(
            button_frame,
            text="Open Directory",
            command=self._open_igc_directory
        ).pack(side="left", padx=5)

    def _create_about_tab(self, notebook) -> None:
        """Create the about tab with application information."""
        about_frame = ttk.Frame(notebook, padding="20")
        notebook.add(about_frame, text="About")

        about_frame.columnconfigure(0, weight=1)

        # App name
        ttk.Label(
            about_frame,
            text=APP_NAME,
            font=tkfont.Font(size=16, weight="bold")
        ).grid(row=0, column=0, pady=(0, 5))

        # Version
        ttk.Label(
            about_frame,
            text=f"Version {APP_VERSION}"
        ).grid(row=1, column=0, pady=(0, 20))

        # Description
        ttk.Label(
            about_frame,
            text="Tool to connect Aerofly FS4 Flight Simulator and generate IGC flight logs.",
            wraplength=400
        ).grid(row=2, column=0, pady=(0, 20))

        # Copyright
        ttk.Label(
            about_frame,
            text="Copyright © 2025 Juan Luis Gabriel"
        ).grid(row=3, column=0, pady=(0, 5))

        # License
        ttk.Label(
            about_frame,
            text="Released under the MIT License"
        ).grid(row=4, column=0, pady=(0, 20))

        # Website
        website_frame = ttk.Frame(about_frame)
        website_frame.grid(row=5, column=0, pady=(0, 20))

        ttk.Label(
            website_frame,
            text="Website:"
        ).pack(side="left")

        website_link = ttk.Label(
            website_frame,
            text="GitHub Repository",
            foreground="blue",
            cursor="hand2"
        )
        website_link.pack(side="left", padx=5)

        # Bind click event to open website
        website_link.bind("<Button-1>", lambda e: self._open_website())

        # Separator
        ttk.Separator(about_frame, orient="horizontal").grid(
            row=6, column=0, sticky="ew", pady=10
        )

        # Instructions
        ttk.Label(
            about_frame,
            text="Instructions",
            font=tkfont.Font(size=12, weight="bold")
        ).grid(row=7, column=0, pady=(0, 10))

        instructions = (
            "1. Start Aerofly FS4\n"
            "2. Enable 'Output data to ForeFlight' in settings\n"
            "3. Verify connection status in the top-right corner\n"
            "4. Enter flight details and click 'Start Recording'\n"
            "5. Fly your aircraft in the simulator\n"
            "6. Click 'Stop Recording' when finished\n"
            "7. View your IGC files in the 'Files' tab"
        )

        ttk.Label(
            about_frame,
            text=instructions,
            justify="left",
            wraplength=400
        ).grid(row=8, column=0, pady=(0, 10))

    def _create_control_bar(self) -> None:
        """Create the control bar at the bottom of the window."""
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.grid(row=2, column=0, sticky="ew")

        # Start Recording button
        self.start_button = ttk.Button(
            control_frame,
            text="Start Recording",
            command=self._start_recording
        )
        self.start_button.pack(side="left", padx=5)
        self.components['start_button'] = self.start_button

        # Stop Recording button
        self.stop_button = ttk.Button(
            control_frame,
            text="Stop Recording",
            command=self._stop_recording,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)
        self.components['stop_button'] = self.stop_button

        # Open IGC Folder button
        self.open_folder_button = ttk.Button(
            control_frame,
            text="Open IGC Folder",
            command=self._open_igc_directory
        )
        self.open_folder_button.pack(side="right", padx=5)

        # Exit button
        self.exit_button = ttk.Button(
            control_frame,
            text="Exit",
            command=self._on_close
        )
        self.exit_button.pack(side="right", padx=5)

    async def _start_application(self) -> None:
        """Start the application and initialize all components."""
        try:
            # Update status
            self.tk_vars['status_message'].set("Starting bridge...")

            # Start the bridge
            if not await self.bridge.start():
                self.tk_vars['status_message'].set("Failed to start bridge")
                messagebox.showerror(
                    "Error",
                    "Failed to start the bridge. Please check the logs for details."
                )
                return

            # Update status
            self.tk_vars['status_message'].set("Bridge started")

            # Subscribe to events
            await self._subscribe_to_events()

            # Start status update
            self.event_tasks.append(
                self.async_loop.create_task(self._status_update_loop())
            )

            # Refresh file list
            self._refresh_file_list()

            # Set running flag
            self.running = True

            # Set initial focus to main tab
            self.components['notebook'].select(0)

            logger.info("Application started successfully")
        except Exception as e:
            logger.error(f"Error starting application: {e}")
            self.tk_vars['status_message'].set(f"Error: {str(e)}")
            messagebox.showerror(
                "Error",
                f"Error starting application: {str(e)}"
            )

    async def _cleanup(self) -> None:
        """Clean up resources before exiting."""
        try:
            # Set status
            if hasattr(self, 'tk_vars') and 'status_message' in self.tk_vars:
                self.tk_vars['status_message'].set("Shutting down...")

            # Stop recording if active
            if (hasattr(self, 'bridge') and self.bridge and
                    self.bridge.get_recording_status().get('recording', {}).get('recording', False)):
                await self.bridge.stop_recording()

            # Cancel all tasks
            for task in self.event_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        # Wait with a timeout
                        await asyncio.wait_for(task, 0.5)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass

            # Clear tasks list
            self.event_tasks.clear()

            # Stop the bridge
            if hasattr(self, 'bridge') and self.bridge:
                await self.bridge.stop()

            logger.info("Application cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _on_close(self) -> None:
        """Handle the window close event."""
        # Check if recording is in progress
        if (hasattr(self, 'bridge') and self.bridge and
                self.bridge.get_recording_status().get('recording', {}).get('recording', False)):
            # Ask for confirmation
            if not messagebox.askyesno(
                    "Recording in Progress",
                    "A recording is currently in progress. Stop the recording and exit?"
            ):
                return

        # Set running flag to false
        self.running = False

        # Destroy the root window
        if hasattr(self, 'root') and self.root:
            self.root.destroy()

        logger.info("Application closed by user")

    async def _subscribe_to_events(self) -> None:
        """Subscribe to events from the event bus."""
        try:
            # Subscribe to connection events
            await event_bus.subscribe(
                EventType.CONNECTION_ESTABLISHED,
                self._handle_connection_established
            )

            await event_bus.subscribe(
                EventType.CONNECTION_LOST,
                self._handle_connection_lost
            )

            # Subscribe to recording events
            await event_bus.subscribe(
                EventType.RECORDING_STARTED,
                self._handle_recording_started
            )

            await event_bus.subscribe(
                EventType.RECORDING_STOPPED,
                self._handle_recording_stopped
            )

            await event_bus.subscribe(
                EventType.POSITION_ADDED,
                self._handle_position_added
            )

            # Subscribe to data events
            await event_bus.subscribe(
                EventType.DATA_RECEIVED,
                self._handle_data_received
            )

            # Subscribe to error events
            await event_bus.subscribe(
                EventType.ERROR_OCCURRED,
                self._handle_error
            )

            logger.debug("Subscribed to events")
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            raise

    async def _status_update_loop(self) -> None:
        """
        Background task that periodically updates the UI status.
        Updates connection status, position data, and recording status.
        """
        try:
            while self.running:
                try:
                    # Update connection status
                    self._update_connection_status()

                    # Update recording status
                    if self.bridge.running:
                        self._update_recording_status()

                    # Sleep for a short time
                    await asyncio.sleep(GUI_REFRESH_RATE_MS / 1000)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in status update loop: {e}")
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.debug("Status update loop cancelled")

    def _update_connection_status(self) -> None:
        """Update the connection status display."""
        if not self.bridge:
            return

        # Get connection status
        status = self.bridge.get_connection_status()

        # Update connection status indicator
        has_connection = status.get('has_connection', False)

        if has_connection:
            self.tk_vars['connection_status'].set("Connected")
            self.tk_vars['connection_color'].set("green")
        else:
            self.tk_vars['connection_status'].set("Disconnected")
            self.tk_vars['connection_color'].set("red")

        # Update position and attitude data if available
        if has_connection:
            # Update position data
            if status.get('has_gps_data', False):
                pos = status.get('latest_position', {})
                self.tk_vars['latitude'].set(f"{pos.get('latitude', 0):.6f}")
                self.tk_vars['longitude'].set(f"{pos.get('longitude', 0):.6f}")
                self.tk_vars['altitude'].set(f"{pos.get('altitude', 0) * METERS_TO_FEET:.0f}")
                self.tk_vars['speed'].set(f"{pos.get('speed', 0) * MPS_TO_KTS:.1f}")
                self.tk_vars['track'].set(f"{pos.get('track', 0):.0f}")

            # Update attitude data
            if status.get('has_attitude_data', False):
                att = status.get('latest_attitude', {})
                self.tk_vars['heading'].set(f"{att.get('heading', 0):.0f}")
                self.tk_vars['pitch'].set(f"{att.get('pitch', 0):.0f}")
                self.tk_vars['roll'].set(f"{att.get('roll', 0):.0f}")

    def _update_recording_status(self) -> None:
        """Update the recording status display."""
        if not self.bridge:
            return

        # Get recording status
        status = self.bridge.get_recording_status()

        # Get recording info
        recording_info = status.get('recording', {})
        is_recording = recording_info.get('recording', False)

        # Update recording status
        if is_recording:
            self.tk_vars['recording_status'].set("Recording")
            self.tk_vars['recording_color'].set("green")
            self.tk_vars['fix_count'].set(str(recording_info.get('fix_count', 0)))
            self.tk_vars['duration'].set(recording_info.get('duration_formatted', "00:00:00"))

            # Update button states
            self.components['start_button'].config(state="disabled")
            self.components['stop_button'].config(state="normal")

            # Update status message
            self.tk_vars['status_message'].set(
                f"Recording to {os.path.basename(recording_info.get('filename', ''))}"
            )
        else:
            self.tk_vars['recording_status'].set("Not Recording")
            self.tk_vars['recording_color'].set("gray")

            # Update button states
            self.components['start_button'].config(state="normal")
            self.components['stop_button'].config(state="disabled")

    async def _handle_connection_established(self, event: Event) -> None:
        """Handle connection established event."""
        if not event.data:
            return

        # Update status
        self.async_loop.call_soon_in_main_thread(
            self.tk_vars['status_message'].set,
            "Connected to Aerofly FS4"
        )

        # Update connection status immediately
        self.async_loop.call_soon_in_main_thread(
            self._update_connection_status
        )

        logger.info("Connection established with Aerofly FS4")

    async def _handle_connection_lost(self, event: Event) -> None:
        """Handle connection lost event."""
        if not event.data:
            return

        # Update status
        self.async_loop.call_soon_in_main_thread(
            self.tk_vars['status_message'].set,
            "Connection with Aerofly FS4 lost"
        )

        # Update connection status immediately
        self.async_loop.call_soon_in_main_thread(
            self._update_connection_status
        )

        logger.info("Connection with Aerofly FS4 lost")

    async def _handle_recording_started(self, event: Event) -> None:
        """Handle recording started event."""
        if not event.data:
            return

        # Get filename
        filename = event.data.get('filename', 'Unknown')

        # Update status
        self.async_loop.call_soon_in_main_thread(
            self.tk_vars['status_message'].set,
            f"Recording to {os.path.basename(filename)}"
        )

        # Update recording status immediately
        self.async_loop.call_soon_in_main_thread(
            self._update_recording_status
        )

        logger.info(f"Recording started: {filename}")

    async def _handle_recording_stopped(self, event: Event) -> None:
        """Handle recording stopped event."""
        if not event.data:
            return

        # Get filename and fix count
        filename = event.data.get('filename')
        fix_count = event.data.get('fix_count', 0)

        # Update status
        if filename:
            self.async_loop.call_soon_in_main_thread(
                self.tk_vars['status_message'].set,
                f"Recording stopped. Flight saved to {os.path.basename(filename)}"
            )

            # Show success message
            self.async_loop.call_soon_in_main_thread(
                messagebox.showinfo,
                "Recording Complete",
                f"Flight recorded and saved to:\n{filename}"
            )

            # Refresh file list
            self.async_loop.call_soon_in_main_thread(
                self._refresh_file_list
            )
        else:
            self.async_loop.call_soon_in_main_thread(
                self.tk_vars['status_message'].set,
                "Recording stopped. No flight data recorded"
            )

            # Show info message
            self.async_loop.call_soon_in_main_thread(
                messagebox.showinfo,
                "Recording Complete",
                "No flight data was recorded"
            )

        # Update recording status immediately
        self.async_loop.call_soon_in_main_thread(
            self._update_recording_status
        )

        if filename:
            logger.info(f"Recording stopped: {filename}, {fix_count} fixes")
        else:
            logger.info("Recording stopped. No data recorded")

    async def _handle_position_added(self, event: Event) -> None:
        """Handle position added event."""
        if not event.data:
            return

        # Get fix count
        fix_count = event.data.get('fix_count', 0)

        # Update fix count
        self.async_loop.call_soon_in_main_thread(
            self.tk_vars['fix_count'].set,
            str(fix_count)
        )

    async def _handle_data_received(self, event: Event) -> None:
        """Handle data received event."""
        # Update connection status on next refresh cycle
        pass

    async def _handle_error(self, event: Event) -> None:
        """Handle error event."""
        if not event.data:
            return

        # Get error message and component
        message = event.data.get('message', 'Unknown error')
        component = event.data.get('component', 'Unknown')

        # Log the error
        logger.error(f"Error in {component}: {message}")

        # Show error message for certain critical components
        critical_components = ['UDPServer', 'IGCWriter', 'AeroflyBridge']

        if component in critical_components:
            # Update status message
            self.async_loop.call_soon_in_main_thread(
                self.tk_vars['status_message'].set,
                f"Error in {component}: {message}"
            )

            # Show error dialog for serious errors
            if 'Failed to start' in message or 'Connection' in message:
                self.async_loop.call_soon_in_main_thread(
                    messagebox.showerror,
                    "Error",
                    f"Error in {component}:\n{message}"
                )

    def _start_recording(self) -> None:
        """Start recording a flight."""
        if not self.bridge:
            return

        # Check if already recording
        if self.bridge.get_recording_status().get('recording', {}).get('recording', False):
            messagebox.showinfo("Already Recording", "A recording is already in progress")
            return

        # Get values from UI
        pilot_name = self.tk_vars['pilot_name'].get()
        glider_type = self.tk_vars['glider_type'].get()
        glider_id = self.tk_vars['glider_id'].get()

        # Start recording
        self.async_loop.create_task(
            self.bridge.start_recording(
                pilot_name=pilot_name,
                glider_type=glider_type,
                glider_id=glider_id
            )
        )

        # Update status
        self.tk_vars['status_message'].set("Starting recording...")

    def _stop_recording(self) -> None:
        """Stop recording the current flight."""
        if not self.bridge:
            return

        # Check if recording
        if not self.bridge.get_recording_status().get('recording', {}).get('recording', False):
            messagebox.showinfo("Not Recording", "No recording is currently in progress")
            return

        # Stop recording
        self.async_loop.create_task(
            self.bridge.stop_recording()
        )

        # Update status
        self.tk_vars['status_message'].set("Stopping recording...")

    def _change_udp_port(self) -> None:
        """Change the UDP port."""
        try:
            # Get the port from the UI
            port_str = self.tk_vars['udp_port'].get()

            # Validate port
            port = int(port_str)
            if port < 1 or port > 65535:
                raise ValueError("Port must be between 1 and 65535")

            # Check if bridge is running
            if self.bridge and self.bridge.running:
                # Ask for confirmation
                if not messagebox.askyesno(
                        "Restart Required",
                        "Changing the UDP port requires restarting the bridge. Continue?"
                ):
                    return

                # Update settings
                settings.set('udp_port', port)
                settings.save_settings()

                # Restart the bridge
                self.async_loop.create_task(self._restart_bridge())
            else:
                # Just update settings
                settings.set('udp_port', port)
                settings.save_settings()

                # Show confirmation
                messagebox.showinfo(
                    "Port Changed",
                    f"UDP port changed to {port}. The change will take effect next time the application is started."
                )

        except ValueError:
            # Show error
            messagebox.showerror(
                "Invalid Port",
                "Please enter a valid port number between 1 and 65535."
            )

    async def _restart_bridge(self) -> None:
        """Restart the bridge with new settings."""
        try:
            # Update status
            self.tk_vars['status_message'].set("Restarting bridge...")

            # Stop the bridge
            await self.bridge.stop()

            # Create a new bridge
            self.bridge = create_bridge()

            # Start the bridge
            if not await self.bridge.start():
                self.tk_vars['status_message'].set("Failed to restart bridge")
                messagebox.showerror(
                    "Error",
                    "Failed to restart the bridge. Please check the logs for details."
                )
                return

            # Update status
            self.tk_vars['status_message'].set("Bridge restarted")

            # Update UI immediately
            self._update_connection_status()

            # Show confirmation
            messagebox.showinfo(
                "Bridge Restarted",
                f"Bridge restarted with UDP port {settings.get('udp_port')}."
            )
        except Exception as e:
            logger.error(f"Error restarting bridge: {e}")
            self.tk_vars['status_message'].set(f"Error restarting bridge: {str(e)}")
            messagebox.showerror(
                "Error",
                f"Error restarting bridge: {str(e)}"
            )

    def _browse_igc_directory_settings(self) -> None:
        """Browse for IGC directory in settings."""
        # Get the current directory
        current_dir = settings.get('igc_directory')

        # Open directory dialog
        new_dir = filedialog.askdirectory(
            initialdir=current_dir,
            title="Select IGC Directory"
        )

        # If a directory was selected
        if new_dir:
            # Update settings
            settings.set('igc_directory', new_dir)
            settings.save_settings()

            # Update UI
            self.tk_vars['igc_directory'].set(new_dir)

    def _save_settings(self) -> None:
        """Save settings."""
        try:
            # Get values from UI
            udp_port_str = self.tk_vars['udp_port'].get()
            recording_interval_str = self.tk_vars['recording_interval'].get()

            # Validate UDP port
            try:
                udp_port = int(udp_port_str)
                if udp_port < 1 or udp_port > 65535:
                    raise ValueError("Port must be between 1 and 65535")
            except ValueError:
                messagebox.showerror(
                    "Invalid Port",
                    "Please enter a valid port number between 1 and 65535."
                )
                return

            # Validate recording interval
            try:
                recording_interval = float(recording_interval_str)
                if recording_interval <= 0:
                    raise ValueError("Interval must be greater than 0")
            except ValueError:
                messagebox.showerror(
                    "Invalid Interval",
                    "Please enter a valid recording interval greater than 0."
                )
                return

            # Update settings
            settings.set('udp_port', udp_port)
            settings.set('recording_interval', recording_interval)

            # Save settings
            settings.save_settings()

            # Show confirmation
            messagebox.showinfo(
                "Settings Saved",
                "Settings have been saved successfully. Some changes may require a restart to take effect."
            )

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            messagebox.showerror(
                "Error",
                f"Error saving settings: {str(e)}"
            )

    def _refresh_file_list(self) -> None:
        """Refresh the IGC file list."""
        # Clear the current list
        file_tree = self.components['file_tree']
        for item in file_tree.get_children():
            file_tree.delete(item)

        try:
            # Get IGC directory
            igc_dir = get_igc_directory()

            # Get file list
            igc_files = list_igc_files(igc_dir)

            # Add files to treeview
            for file_path in igc_files:
                # Get file info
                from ..io.files import get_file_info
                info = get_file_info(file_path)

                # Format data
                filename = os.path.basename(file_path)
                date = info.get('modified', "")
                size = info.get('size_str', "")

                # Add to treeview
                file_tree.insert("", "end", values=(filename, date, size), tags=(file_path,))

        except Exception as e:
            logger.error(f"Error refreshing file list: {e}")

    def _open_selected_file(self) -> None:
        """Open the selected IGC file."""
        # Get selected item
        file_tree = self.components['file_tree']
        selection = file_tree.selection()

        if not selection:
            messagebox.showinfo(
                "No File Selected",
                "Please select a file to open."
            )
            return

        # Get file path
        item = selection[0]
        file_path = file_tree.item(item, "tags")[0]

        # Open file
        if open_file_or_directory(file_path):
            logger.info(f"Opened file: {file_path}")
        else:
            messagebox.showerror(
                "Error",
                f"Failed to open file: {file_path}"
            )

    def _on_file_double_click(self, event) -> None:
        """Handle double-click on file in treeview."""
        self._open_selected_file()

    def _open_igc_directory(self) -> None:
        """Open the IGC directory."""
        # Get IGC directory
        igc_dir = get_igc_directory()

        # Open directory
        if open_file_or_directory(igc_dir):
            logger.info(f"Opened directory: {igc_dir}")
        else:
            messagebox.showerror(
                "Error",
                f"Failed to open directory: {igc_dir}"
            )

    def _open_website(self) -> None:
        """Open the GitHub repository website."""
        url = "https://github.com/jlgabriel/aerofly-igc-recorder"

        # Open URL
        import webbrowser
        if webbrowser.open(url):
            logger.info(f"Opened website: {url}")
        else:
            messagebox.showerror(
                "Error",
                f"Failed to open website: {url}"
            )


# Factory function to create a GUI instance
def create_gui() -> GUI:
    """
    Create a new GUI instance.

    Returns:
        GUI: A new GUI instance
    """
    return GUI()
