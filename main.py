#!/usr/bin/env python3

"""
Aerofly FS4 IGC Recorder
Connects Aerofly FS4 Flight Simulator and generates IGC flight logs.

Entry point script that launches either the GUI or CLI interface.
"""

import sys
import argparse
import asyncio
import logging
from app import __version__, APP_NAME
from app.config.settings import settings

# Set up logger
logger = logging.getLogger("aerofly_igc_recorder.main")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description=APP_NAME)

    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    parser.add_argument(
        '--cli',
        action='store_true',
        help='Run in command-line interface mode (no GUI)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=settings.get('udp_port'),
        help=f'UDP port to listen on (default: {settings.get("udp_port")})'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default=settings.get('igc_directory'),
        help=f'Directory to save IGC files (default: {settings.get("igc_directory")})'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=settings.get('log_level', 'INFO'),
        help='Set the logging level'
    )

    return parser.parse_args()


async def main():
    """Main entry point function"""
    # Parse command line arguments
    args = parse_arguments()

    # Configure logging based on arguments
    log_level = getattr(logging, args.log_level)
    logging.getLogger("aerofly_igc_recorder").setLevel(log_level)

    # Update settings from command line arguments
    settings.set('udp_port', args.port)
    settings.set('igc_directory', args.output_dir)
    settings.set('log_level', args.log_level)

    # Log startup information
    logger.info(f"Starting {APP_NAME} v{__version__}")
    logger.info(f"UDP Port: {settings.get('udp_port')}")
    logger.info(f"IGC Directory: {settings.get('igc_directory')}")

    # Import UI modules only when needed
    if args.cli:
        try:
            # Import CLI module
            from app.ui.cli import CLI

            # Create and run CLI interface
            cli = CLI()
            await cli.run()

        except ImportError:
            logger.error("CLI module not found")
            return 1
        except Exception as e:
            logger.error(f"Error running CLI: {e}")
            return 1
    else:
        try:
            # Import GUI module
            from app.ui.gui import GUI

            # Create and run GUI interface
            gui = GUI()
            await gui.run()

        except ImportError:
            logger.error("GUI module not found. Falling back to CLI mode.")
            try:
                # Try CLI as fallback
                from app.ui.cli import CLI
                cli = CLI()
                await cli.run()
            except ImportError:
                logger.error("CLI module not found")
                return 1
        except Exception as e:
            logger.error(f"Error running GUI: {e}")
            return 1

    return 0


if __name__ == "__main__":
    try:
        # Run the main function using asyncio
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)