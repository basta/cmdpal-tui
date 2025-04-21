import argparse
import sys
import os # Import os to get CWD
from typing import Optional, Tuple, Dict # Import Tuple, Dict

# Assuming Task model and other modules are defined
try:
    from .models import Task
    from .cli import setup_cli_parsers
    # Import run_task from tui module where it's defined now
    from .tui import CmdPalApp, run_task
    from .config import TASKS_FILE # Import the tasks file path
    # Import storage function to save last params
    from .storage import update_last_param_values
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

    # Add argument to show tasks file path
    parser.add_argument(
        '--tasks-path',
        action='store_true', # Make it a flag
        help='Show the path to the tasks JSON file and exit'
    )

    # Setup subparsers for CLI commands (list, add, edit, delete)
    setup_cli_parsers(parser)

    # Parse the arguments
    args = parser.parse_args()

    # Handle --tasks-path argument first
    if args.tasks_path:
        print(TASKS_FILE)
        sys.exit(0) # Exit successfully after printing the path

    # Check if a CLI command function was specified by a subparser
    if hasattr(args, 'func') and args.func:
        # Execute the specified CLI command function
        args.func(args)
    else:
        # No CLI command given (and --tasks-path wasn't used), launch the TUI
        try:
            launch_cwd = os.getcwd()
        except OSError as e:
            print(f"Error getting current working directory: {e}", file=sys.stderr)
            sys.exit(1)

        selected_task: Optional[Task] = None
        param_values: Optional[Dict[str, str]] = None

        try:
            app = CmdPalApp(launch_cwd=launch_cwd)
            # --- MODIFIED: Reverted to default fullscreen run ---
            result: Optional[Tuple[Task, Optional[Dict[str, str]]]] = app.run() # Removed inline=True
            # --- END MODIFIED ---

            if result:
                selected_task, param_values = result

                # Update last param values *after* TUI exits
                if param_values is not None:
                    if not update_last_param_values(selected_task.id, param_values):
                         # Log or print warning if saving last values failed
                         print("Warning: Failed to save last used parameter values.", file=sys.stderr)

        except Exception as e:
            # Catch potential errors during TUI execution
            print(f"\nAn error occurred running the TUI: {e}", file=sys.stderr)
            sys.exit(1) # Exit if TUI crashes
        # --- REMOVED finally block for cursor restoration (not needed for fullscreen) ---


        # If the TUI exited with a selected task, run it
        # This now happens *after* the TUI block and potential param saving
        if selected_task:
            run_task(selected_task, param_values, launch_cwd)


if __name__ == "__main__":
    main()
