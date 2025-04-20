import argparse
import sys
from typing import Optional

# Assuming Task model and other modules are defined
try:
    from .models import Task
    from .cli import setup_cli_parsers
    from .tui import CmdPalApp, run_task # Import run_task from tui for now
    from .config import TASKS_FILE # Import the tasks file path
except ImportError as e:
    print(f"Error importing CmdPal modules: {e}", file=sys.stderr)
    print("Ensure you are running this from the project root or have installed the package.", file=sys.stderr)
    sys.exit(1)


def main():
    """Main entry point for the CmdPal application."""
    parser = argparse.ArgumentParser(
        description="CmdPal: Manage and run command-line tasks via TUI or CLI.",
        prog="cmdpal" # Set the program name for help messages
    )

    # --- Add argument to show tasks file path ---
    parser.add_argument(
        '--tasks-path',
        action='store_true', # Make it a flag
        help='Show the path to the tasks JSON file and exit'
    )
    # --- End argument addition ---

    # Setup subparsers for CLI commands (list, add, edit, delete)
    # Do this *after* defining top-level args like --tasks-path
    setup_cli_parsers(parser)

    # Parse the arguments
    args = parser.parse_args()

    # --- Handle --tasks-path argument first ---
    if args.tasks_path:
        print(TASKS_FILE)
        sys.exit(0) # Exit successfully after printing the path
    # --- End handling --tasks-path ---

    # Check if a CLI command function was specified by a subparser
    if hasattr(args, 'func') and args.func:
        # Execute the specified CLI command function
        args.func(args)
    else:
        # No CLI command given (and --tasks-path wasn't used), launch the TUI
        try:
            app = CmdPalApp()
            selected_task: Optional[Task] = app.run() # Run the TUI app

            # If the TUI exited with a selected task, run it
            if selected_task:
                run_task(selected_task) # Call the execution function

        except Exception as e:
            # Catch potential errors during TUI execution
            print(f"\nAn error occurred running the TUI: {e}", file=sys.stderr)
            # Consider more specific error handling or logging
            sys.exit(1)

if __name__ == "__main__":
    main()
