# app/gliders.py

"""
This module defines the data of the different gliders available
to be used in the Aerofly IGC recorder.

The information provided here is used both for display in the GUI
and for inclusion in the generated IGC files.
"""

# Dictionary with information of gliders available in Aerofly FS4
GLIDERS = {
    "ASK 21": {
        "manufacturer": "Alexander Schleicher",
        "model": "ASK 21",
        "wingspan": 17.0,  # meters
        "competition_class": "Two-Seater",
        "igc_code": "ASK21",
        "glider_id": "ASK21",
        "description": "Training glider with excellent handling characteristics"
    },
    "Antares 21E": {
        "manufacturer": "Lange Aviation",
        "model": "Antares 21E",
        "wingspan": 21.0,  # meters
        "competition_class": "Open",
        "igc_code": "ANTAR21E",
        "glider_id": "ANTAR21E",
        "description": "Self-launch electric glider with high performance"
    },
    "ASG 29": {
        "manufacturer": "Alexander Schleicher",
        "model": "ASG 29",
        "wingspan": 18.0,  # meters
        "competition_class": "18-Meter",
        "igc_code": "ASG29",
        "glider_id": "ASG29",
        "description": "High-performance competition glider"
    },
    "Swift S1": {
        "manufacturer": "Marganski",
        "model": "Swift S1",
        "wingspan": 13.3,  # meters
        "competition_class": "Aerobatic",
        "igc_code": "SWIFTS1",
        "glider_id": "SWIFTS1",
        "description": "Aerobatic glider with excellent maneuverability"
    },
}

def get_glider_list():
    """Returns a list of glider names sorted alphabetically."""
    return sorted(GLIDERS.keys())

def get_glider_data(glider_name):
    """
    Gets the data of a specific glider.
    
    Args:
        glider_name (str): Name of the glider
        
    Returns:
        dict: Glider data or None if it doesn't exist
    """
    return GLIDERS.get(glider_name)

def get_igc_glider_info(glider_name):
    """
    Gets the information formatted for the IGC file.
    
    Args:
        glider_name (str): Name of the glider
        
    Returns:
        dict: Glider information for the IGC file
    """
    glider = get_glider_data(glider_name)
    if not glider:
        return {
            "manufacturer": "UNKNOWN",
            "model": "UNKNOWN",
            "igc_code": "UNKNOWN",
            "glider_id": "UNKNOWN",
            "competition_class": "UNKNOWN"
        }
    
    return {
        "manufacturer": glider["manufacturer"],
        "model": glider["model"],
        "igc_code": glider["igc_code"],
        "glider_id": glider["glider_id"],
        "competition_class": glider["competition_class"]
    }

def add_custom_glider(name, manufacturer, model, wingspan, competition_class, igc_code, glider_id, description=""):
    """
    Adds a custom glider to the list of available gliders.
    
    Args:
        name (str): Display name of the glider
        manufacturer (str): Manufacturer of the glider
        model (str): Model of the glider
        wingspan (float): Wingspan in meters
        competition_class (str): Competition class
        igc_code (str): IGC code of the glider
        glider_id (str): Glider ID
        description (str, optional): Additional description
        
    Returns:
        bool: True if added successfully, False if it already existed
    """
    if name in GLIDERS:
        return False
    
    GLIDERS[name] = {
        "manufacturer": manufacturer,
        "model": model,
        "wingspan": float(wingspan),
        "competition_class": competition_class,
        "igc_code": igc_code,
        "glider_id": glider_id,
        "description": description
    }
    
    return True
