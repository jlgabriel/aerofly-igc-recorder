"""
Glider tab UI components for Aerofly FS4 IGC Recorder.
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Dict, Any, Optional, Callable

from ..config.gliders_module import get_glider_list, get_glider_data

# Configure logger
logger = logging.getLogger("aerofly_igc_recorder.ui.glider_tab")

class GliderTab:
    """
    Tab for glider selection and information display.
    """

    def __init__(self, parent: ttk.Frame, on_glider_selected: Optional[Callable[[str], None]] = None):
        """
        Initialize the glider tab.
        
        Args:
            parent: Parent frame
            on_glider_selected: Callback for when a glider is selected
        """
        self.parent = parent
        self.on_glider_selected = on_glider_selected
        
        # Tkinter variables
        self.selected_glider = tk.StringVar()
        self.glider_info = {
            'manufacturer': tk.StringVar(),
            'model': tk.StringVar(),
            'wingspan': tk.StringVar(),
            'competition_class': tk.StringVar(),
            'igc_code': tk.StringVar(),
            'glider_id': tk.StringVar(),
            'description': tk.StringVar()
        }
        
        # Create UI components
        self._create_ui()
        
        # Load initial glider list
        self._load_gliders()

    def _create_ui(self) -> None:
        """Create the UI components."""
        # Configure grid
        self.parent.columnconfigure(0, weight=1)
        
        # Selection frame
        selection_frame = ttk.LabelFrame(self.parent, text="Glider Selection", padding="10")
        selection_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        selection_frame.columnconfigure(1, weight=1)
        
        # Glider dropdown
        ttk.Label(selection_frame, text="Select Glider:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.glider_combo = ttk.Combobox(
            selection_frame,
            textvariable=self.selected_glider,
            state="readonly",
            width=40
        )
        self.glider_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.glider_combo.bind('<<ComboboxSelected>>', self._on_glider_selected)
        
        # Information frame
        info_frame = ttk.LabelFrame(self.parent, text="Glider Information", padding="10")
        info_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        info_frame.columnconfigure(1, weight=1)
        
        # Information fields
        row = 0
        
        # Manufacturer
        ttk.Label(info_frame, text="Manufacturer:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.glider_info['manufacturer']).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        row += 1
        
        # Model
        ttk.Label(info_frame, text="Model:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.glider_info['model']).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        row += 1
        
        # Wingspan
        ttk.Label(info_frame, text="Wingspan:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        wingspan_frame = ttk.Frame(info_frame)
        wingspan_frame.grid(row=row, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(wingspan_frame, textvariable=self.glider_info['wingspan']).pack(side="left")
        ttk.Label(wingspan_frame, text=" meters").pack(side="left")
        row += 1
        
        # Competition Class
        ttk.Label(info_frame, text="Competition Class:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.glider_info['competition_class']).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        row += 1
        
        # IGC Code
        ttk.Label(info_frame, text="IGC Code:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.glider_info['igc_code']).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        row += 1
        
        # Glider ID
        ttk.Label(info_frame, text="Glider ID:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(info_frame, textvariable=self.glider_info['glider_id']).grid(row=row, column=1, sticky="w", padx=5, pady=2)
        row += 1
        
        # Description
        ttk.Label(info_frame, text="Description:").grid(row=row, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(
            info_frame, 
            textvariable=self.glider_info['description'],
            wraplength=400
        ).grid(row=row, column=1, sticky="w", padx=5, pady=2)

    def _load_gliders(self) -> None:
        """Load the list of available gliders."""
        try:
            # Get glider list
            gliders = get_glider_list()
            
            # Update combobox values
            self.glider_combo['values'] = gliders
            
            # Select first glider if available
            if gliders:
                self.glider_combo.set(gliders[0])
                self._update_glider_info(gliders[0])
                
        except Exception as e:
            logger.error(f"Error loading glider list: {e}")

    def _on_glider_selected(self, event) -> None:
        """Handle glider selection change."""
        selected = self.selected_glider.get()
        if selected:
            self._update_glider_info(selected)
            
            # Call callback if provided
            if self.on_glider_selected:
                self.on_glider_selected(selected)

    def _update_glider_info(self, glider_name: str) -> None:
        """Update the displayed glider information."""
        try:
            # Get glider data
            glider = get_glider_data(glider_name)
            
            if glider:
                # Update display variables
                self.glider_info['manufacturer'].set(glider['manufacturer'])
                self.glider_info['model'].set(glider['model'])
                self.glider_info['wingspan'].set(str(glider['wingspan']))
                self.glider_info['competition_class'].set(glider['competition_class'])
                self.glider_info['igc_code'].set(glider['igc_code'])
                self.glider_info['glider_id'].set(glider['glider_id'])
                self.glider_info['description'].set(glider['description'])
            else:
                # Clear all fields if glider not found
                for var in self.glider_info.values():
                    var.set("")
                    
        except Exception as e:
            logger.error(f"Error updating glider information: {e}")

    def get_selected_glider_info(self) -> Dict[str, Any]:
        """
        Get information about the currently selected glider.
        
        Returns:
            Dict[str, Any]: Selected glider information or empty dict if none selected
        """
        selected = self.selected_glider.get()
        if selected:
            return get_glider_data(selected) or {}
        return {} 