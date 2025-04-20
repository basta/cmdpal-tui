import os
import subprocess
import sys # Import sys for error handling in run_task
import typing
from pathlib import Path
from typing import Optional # Explicitly import Optional

from textual.app import App, ComposeResult, Binding # Import Binding
from textual.containers import Container, VerticalScroll
from textual.reactive import reactive
# Import specific DataTable components and exceptions
from textual.widgets import Header, Footer, Input, DataTable, Static
# Import CellDoesNotExist and RowKey
from textual.widgets.data_table import CellDoesNotExist, RowKey
from textual.message import Message # Import Message base class if creating custom messages
from textual.coordinate import Coordinate # Import Coordinate

# Assuming Task model and storage functions are defined elsewhere
try:
    from .models import Task
    from .storage import load_tasks, save_tasks # Import save_tasks
    from .utils import fuzzy_search_tasks
    from .config import DEFAULT_SCORE_CUTOFF
except ImportError:
    # Simple placeholders for standalone testing/viewing
    from dataclasses import dataclass
    @dataclass
    class Task: id: str = ""; name: str = ""; command: str = ""; cwd: str = "~"; description: typing.Optional[str] = ""
    def load_tasks() -> typing.Tuple[typing.List[Task], bool]: return ([Task(id='1', name='Dummy Task', command='echo hello')], False)
    def save_tasks(t: typing.List[Task]) -> bool: return True
    def fuzzy_search_tasks(q, t, **kw) -> typing.List[Task]: return t
    DEFAULT_SCORE_CUTOFF = 50


class CmdPalApp(App[Optional[Task]]):
    """The main Textual TUI application for CmdPal."""

    TITLE = "CmdPal - Command Palette"
    SUB_TITLE = "Find and run your commands"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True, priority=True),
        Binding("escape", "quit", "Quit", show=True),
        Binding("enter", "select_task", "Run Task", show=False, priority=True),
        Binding("up", "cursor_up", "Cursor Up", show=False, priority=True),
        Binding("down", "cursor_down", "Cursor Down", show=False, priority=True),
    ]

    # CSS_PATH = "cmdpal.css" # Optional: Define if you want external CSS

    # --- Reactive Variables ---
    tasks: reactive[list[Task]] = reactive(list) # Holds all loaded tasks
    filtered_tasks: reactive[list[Task]] = reactive(list) # Holds tasks matching filter

    # --- App Setup ---

    def __init__(self):
        super().__init__()
        # No need for _preview_content state variable anymore

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Input(placeholder="Filter tasks by name or description...")
        with Container(id="table-container"): # Container helps manage layout/scrolling
             yield DataTable(id="task-table", cursor_type="row", zebra_stripes=True) # Enable zebra stripes
        with VerticalScroll(id="preview-container"): # Make preview scrollable
            # Use Markdown for richer formatting potential in preview
            yield Static(id="preview-pane", expand=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        # Load tasks and check if resave is needed
        loaded_tasks, needs_resave = load_tasks()
        self.tasks = loaded_tasks
        self.filtered_tasks = self.tasks # Initially show all tasks

        # If IDs were generated during load, save the file back immediately
        if needs_resave:
             self.log.info(f"Resaving tasks file ({TASKS_FILE}) with newly generated IDs...")
             if not save_tasks(self.tasks):
                  self.log.warning("Failed to resave tasks file after generating IDs.")
                  # App continues with in-memory IDs, but file won't be updated

        # Configure DataTable
        table = self.query_one(DataTable)
        table.add_column("Name", key="name")
        table.add_column("Description", key="description")
        table.add_column("CWD", key="cwd")
        self._update_table() # Populate the table with initial data

        # Focus the input field initially
        self.query_one(Input).focus()

    # --- Event Handlers ---

    def on_input_changed(self, event: Input.Changed) -> None:
        """Called when the filter input text changes."""
        query = event.value
        self.filtered_tasks = fuzzy_search_tasks(
            query,
            self.tasks,
            score_cutoff=DEFAULT_SCORE_CUTOFF
        )
        self._update_table() # Update table content based on new filter

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Called when a row is highlighted in the DataTable (e.g., by cursor move)."""
        # The event.row_key *is* the RowKey object for the selected row
        if event.row_key is not None:
            try:
                task_id = str(event.row_key.value) # Assuming row key value is the task_id
                selected_task = next((t for t in self.tasks if t.id == task_id), None)
                self._update_preview_pane(selected_task) # Update preview using helper
            except Exception as e:
                self.log.error(f"Error finding task for preview: {e}")
                self._update_preview_pane(None)
        else:
             self._update_preview_pane(None) # Clear preview if no row selected


    # --- Actions ---

    def action_select_task(self) -> None:
        """Called when the user presses Enter to select a task."""
        table = self.query_one(DataTable)
        # Ensure cursor_row is a valid index before trying to get the key
        if table.is_valid_row_index(table.cursor_row):
            try:
                # Use coordinate_to_cell_key based on documentation
                cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
                row_key = cell_key.row_key # Extract the RowKey from the CellKey
                if row_key is not None:
                     task_id = str(row_key.value) # Assuming row key value is the task_id
                     selected_task = next((t for t in self.tasks if t.id == task_id), None)
                     if selected_task:
                        self.exit(result=selected_task) # Exit app, returning the selected task
            except CellDoesNotExist:
                # This might happen if the cursor is somehow on an invalid cell briefly
                self.log.error(f"CellDoesNotExist at cursor {table.cursor_coordinate} during selection")
                pass # Ignore selection if cell doesn't exist


    def action_quit_app(self) -> None:
        """Called when the user presses Escape or Ctrl+C."""
        self.exit(result=None)

    def action_cursor_up(self) -> None:
        """Move the DataTable cursor up."""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            # Decrement row, clamping at 0
            new_row = max(0, table.cursor_row - 1)
            table.move_cursor(row=new_row)

    def action_cursor_down(self) -> None:
        """Move the DataTable cursor down."""
        table = self.query_one(DataTable)
        if table.row_count > 0:
            # Increment row, clamping at max row index
            new_row = min(table.row_count - 1, table.cursor_row + 1)
            table.move_cursor(row=new_row)

    # --- Helper Methods ---

    def _update_table(self) -> None:
        """Clears and repopulates the DataTable with filtered tasks."""
        table = self.query_one(DataTable)
        # Store the current cursor row and key to try and restore it later
        current_cursor_row = table.cursor_row if table.is_valid_row_index(table.cursor_row) else 0
        current_row_key: Optional[RowKey] = None # Use Optional typing
        if table.is_valid_coordinate(Coordinate(row=current_cursor_row, column=0)): # Check coordinate validity
            try:
                 # Use coordinate_to_cell_key based on documentation
                 current_cell_key = table.coordinate_to_cell_key(Coordinate(row=current_cursor_row, column=0))
                 current_row_key = current_cell_key.row_key
            except CellDoesNotExist:
                 current_row_key = None # Handle case where coordinate is invalid

        table.clear() # Clear existing rows

        # Add rows from filtered_tasks
        # Use task.id as the row key to uniquely identify rows
        new_row_keys_values = [] # Store just the values (IDs) for easy checking
        for task in self.filtered_tasks:
            desc = (task.description or "")[:50] # Truncate description for table view
            if len(task.description or "") > 50:
                desc += "..."
            # Add row data corresponding to columns, use task.id as the key
            table.add_row(
                task.name,
                desc,
                task.cwd,
                key=task.id # Store task ID as the row key
            )
            new_row_keys_values.append(task.id)

        # Use move_cursor instead of direct assignment
        if table.row_count > 0:
            target_row = 0 # Default to the first row
            # Try to restore cursor position if the previously selected row still exists
            # Check current_row_key is not None before accessing its value
            if current_row_key is not None and current_row_key.value in new_row_keys_values:
                try:
                    # Find the new row index for the key's value.
                    target_row = new_row_keys_values.index(current_row_key.value)
                except ValueError:
                     # If key value not found
                     target_row = 0 # Reset to top
            else:
                 # If previous key not found or didn't exist, set to valid index
                 # Clamp target_row to ensure it's within bounds
                 target_row = max(0, min(current_cursor_row, table.row_count - 1))


            # Use move_cursor to set the cursor position
            table.move_cursor(row=target_row)


        # Update preview based on the final cursor position
        task_at_cursor = None
        # Check if the target cursor coordinate is valid before getting key
        if table.is_valid_coordinate(table.cursor_coordinate):
             try:
                 # Use coordinate_to_cell_key based on documentation
                 cursor_cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
                 cursor_row_key = cursor_cell_key.row_key
                 if cursor_row_key is not None:
                     task_id = str(cursor_row_key.value)
                     task_at_cursor = next((t for t in self.tasks if t.id == task_id), None)
             except CellDoesNotExist:
                 # Handle case where cursor might be on an invalid cell after update
                 self.log.error(f"CellDoesNotExist at cursor {table.cursor_coordinate} updating preview")
                 task_at_cursor = None


        self._update_preview_pane(task_at_cursor)


    def _update_preview_pane(self, task: Optional[Task]) -> None:
        """Updates the preview pane with the details of the given task."""
        try:
            preview_pane = self.query_one("#preview-pane", Static)
            if task:
                # Use Markdown formatting for clarity
                # Ensure command is escaped properly for markdown code block if needed
                escaped_command = task.command.replace("`", "\\`")
                preview_content = (
                    f"**Command:**\n```sh\n{escaped_command}\n```\n\n"
                    f"**Directory:**\n`{task.cwd}`"
                )
                preview_pane.update(preview_content)
            else:
                preview_pane.update("[dim]Select a task to see details...[/dim]")
        except Exception as e:
            # Log error if preview pane update fails unexpectedly
            self.log.error(f"Failed to update preview pane: {e}")


# --- Command Execution Function ---
# This might live elsewhere eventually, but put here for simplicity initially

def run_task(task: Task) -> None:
    """Executes the selected task's command."""
    if not task:
        print("No task selected to run.")
        return

    command = task.command
    cwd = os.path.expanduser(task.cwd) # Expand ~

    print(f"\n--- Running Task: {task.name} ---")
    print(f"Directory: {cwd}")
    print(f"Command:   {command}")
    print("-" * (len(f"--- Running Task: {task.name} ---"))) # Match separator length

    try:
        # Ensure directory exists before trying to run command in it
        if not Path(cwd).is_dir():
             print(f"\nError: Working directory not found: {cwd}", file=sys.stderr)
             return

        # Execute the command using shell=True as per design doc v2
        # This allows complex commands like pipelines to work easily
        # Note security implications if commands were from untrusted sources
        process = subprocess.run(command, shell=True, cwd=cwd, check=False) # check=False to report error manually

        if process.returncode != 0:
            print(f"\nWarning: Task exited with non-zero status: {process.returncode}", file=sys.stderr)
        else:
            print(f"\nTask '{task.name}' appears to have completed.")

    except FileNotFoundError:
         # Provide a more specific error if the command itself isn't found
         cmd_base = command.split()[0] if command else ""
         print(f"\nError: Command '{cmd_base}' not found. Is it installed and in your PATH?", file=sys.stderr)
    except Exception as e:
        print(f"\nAn error occurred while trying to run the task: {e}", file=sys.stderr)
