#!/usr/bin/env python3

"""
Entry point script that launches the GUI interface.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Aerofly FS4 IGC Recorder'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    return parser.parse_args()

async def main():
    """Main entry point."""
    args = parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Import GUI module
        from app.ui.gui import GUI
        
        # Create and run GUI interface
        gui = GUI()
        await gui.run()
        
    except ImportError:
        logger.error("GUI module not found")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running GUI: {e}")
        sys.exit(1)

if __name__ == '__main__':
    if sys.platform == 'win32':
        # Set event loop policy for Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run main function
    asyncio.run(main())