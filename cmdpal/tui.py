import os
import subprocess
import sys # Import sys for error handling in run_task
import time # Import time
import typing
from pathlib import Path
from typing import Optional, List, Dict, Any # Explicitly import Optional

from textual.app import App, ComposeResult, Binding # Import Binding
# Import Horizontal container for side-by-side layout
from textual.containers import Container, VerticalScroll, Horizontal
from textual.reactive import reactive
# Import specific DataTable components and exceptions
from textual.widgets import Header, Footer, Input, DataTable, Static
# Import CellDoesNotExist and RowKey, and event types
from textual.widgets.data_table import CellDoesNotExist, RowKey
from textual.message import Message # Import Message base class if creating custom messages
from textual.coordinate import Coordinate # Import Coordinate
from textual.binding import BindingType # For more complex bindings if needed

# Assuming Task model and storage functions are defined elsewhere
try:
    from .models import Task
    # Import save_tasks and the new history functions
    from .storage import load_tasks, save_tasks, update_last_run_timestamp
    from .storage import load_history, add_history_entry, HistoryEntry
    from .utils import fuzzy_search_tasks
    from .config import DEFAULT_SCORE_CUTOFF, RECOMMENDATIONS_COUNT, TASKS_FILE # Import new config
except ImportError:
    # Simple placeholders for standalone testing/viewing
    from dataclasses import dataclass
    @dataclass
    class Task: id: str = ""; name: str = ""; command: str = ""; cwd: str = "~"; description: typing.Optional[str] = ""; last_run_timestamp: Optional[float] = None
    HistoryEntry = Dict[str, Any]
    def load_tasks() -> typing.Tuple[typing.List[Task], bool]: return ([Task(id='1', name='Dummy Task', command='echo hello')], False)
    def save_tasks(t: typing.List[Task]) -> bool: return True
    def update_last_run_timestamp(tid: str) -> bool: print(f"Simulating timestamp update for {tid}"); return True # Placeholder
    def load_history() -> List[HistoryEntry]: return [{"timestamp": time.time() - 10, "task_id": "1", "directory": os.getcwd()}] # Placeholder
    def add_history_entry(tid: str, d:str) -> None: print(f"Simulating history add for {tid} in {d}") # Placeholder
    def fuzzy_search_tasks(q, t, **kw) -> typing.List[Task]: return t
    DEFAULT_SCORE_CUTOFF = 50
    RECOMMENDATIONS_COUNT = 3
    TASKS_FILE = Path("~/.config/cmdpal/tasks.json").expanduser()


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

    # CSS_PATH = "cmdpal.css" # Optional: Define CSS for sizing side-by-side panes

    # --- Reactive Variables ---
    tasks: reactive[list[Task]] = reactive(list) # Holds all loaded tasks
    history: reactive[list[HistoryEntry]] = reactive(list) # Holds execution history

    # --- App Setup ---

    def __init__(self, launch_cwd: str):
        super().__init__()
        self.launch_cwd = launch_cwd # Store the directory where cmdpal was launched
        self._current_filter_query = "" # Store current filter query

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Static(id="cwd-recommendations", markup=True, classes="recommendations")
        yield Input(placeholder="Filter tasks by name or description...")

        # Use Horizontal layout for Table and Preview
        with Horizontal(id="main-pane"):
            # Original table container (might adjust sizing with CSS later)
            with Container(id="table-container"):
                 yield DataTable(id="task-table", cursor_type="row", zebra_stripes=True)
            # Original preview container (might adjust sizing with CSS later)
            with VerticalScroll(id="preview-container"):
                yield Static(id="preview-pane", expand=True, markup=True)

        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is first mounted."""
        # Load tasks and check if resave is needed for generated IDs
        loaded_tasks, needs_task_resave = load_tasks()
        self.tasks = loaded_tasks # Assign to the reactive variable

        # If IDs were generated during load, save the file back immediately
        if needs_task_resave:
             self.log.info(f"Resaving tasks file ({TASKS_FILE}) with newly generated IDs...")
             if not save_tasks(self.tasks):
                  self.log.warning("Failed to resave tasks file after generating IDs.")

        # Load history and update recommendations
        self.history = load_history()
        self._update_recommendations()

        # Configure DataTable
        table = self.query_one(DataTable)
        table.add_column("Name", key="name")
        table.add_column("Description", key="description")
        table.add_column("CWD", key="cwd")
        # Initial population and sort
        self._update_table() # Populate the table with initial data (will sort by time)

        # Focus the input field initially
        self.query_one(Input).focus()

    # --- Event Handlers ---

    def on_input_changed(self, event: Input.Changed) -> None:
        """Called when the filter input text changes."""
        # Store the query and trigger table update
        self._current_filter_query = event.value
        self._update_table() # Update table content based on new filter

    # --- FIX: Renamed event handler to react to cursor movement ---
    def on_data_table_row_highlighted(self, event) -> None:
        """Called when a row is highlighted in the DataTable (e.g., by cursor move)."""
    # --- END FIX ---
        # The event.row_key *is* the RowKey object for the highlighted row
        if event.row_key is not None:
            try:
                task_id = str(event.row_key.value) # Assuming row key value is the task_id
                # Find task in the *original* list, not the potentially sorted/filtered one
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
                     # Find task in the *original* list
                     selected_task = next((t for t in self.tasks if t.id == task_id), None)
                     if selected_task:
                        # Timestamp update is now handled by run_task
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
        """
        Clears and repopulates the DataTable.
        Sorts by last_run_timestamp (desc) if filter is empty,
        otherwise uses fuzzy search results.
        """
        table = self.query_one(DataTable)
        query = self._current_filter_query

        # Determine which tasks to display and sort if necessary
        tasks_to_display: List[Task]
        if not query:
            # No filter: sort all tasks by timestamp (most recent first)
            # Treat None timestamp as 0 (oldest)
            tasks_to_display = sorted(
                self.tasks,
                key=lambda t: t.last_run_timestamp or 0,
                reverse=True
            )
        else:
            # Filter is active: use fuzzy search results (order by score)
            tasks_to_display = fuzzy_search_tasks(
                query,
                self.tasks,
                score_cutoff=DEFAULT_SCORE_CUTOFF
            )

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

        # Add rows from the processed list (sorted or filtered)
        new_row_keys_values = [] # Store just the values (IDs) for easy checking
        for task in tasks_to_display:
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
                     # Find task in the *original* list
                     task_at_cursor = next((t for t in self.tasks if t.id == task_id), None)
             except CellDoesNotExist:
                 # Handle case where cursor might be on an invalid cell after update
                 self.log.error(f"CellDoesNotExist at cursor {table.cursor_coordinate} updating preview")
                 task_at_cursor = None


        self._update_preview_pane(task_at_cursor)

    def _update_recommendations(self) -> None:
        """Updates the recommendations widget based on history for the current CWD."""
        try:
            reco_widget = self.query_one("#cwd-recommendations", Static)
            # Filter history for entries matching the launch directory
            cwd_history = [
                entry for entry in self.history
                if entry.get("directory") == self.launch_cwd
            ]
            # Sort by timestamp descending
            cwd_history.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

            # Get top N unique task IDs from this directory's history
            recent_task_ids_in_cwd = []
            seen_ids = set()
            for entry in cwd_history:
                task_id = entry.get("task_id")
                if task_id and task_id not in seen_ids:
                    recent_task_ids_in_cwd.append(task_id)
                    seen_ids.add(task_id)
                    if len(recent_task_ids_in_cwd) >= RECOMMENDATIONS_COUNT:
                        break

            if not recent_task_ids_in_cwd:
                reco_widget.update("[dim]No recent tasks recorded in this directory.[/dim]")
                reco_widget.display = False # Hide if no recommendations
                return

            # Look up task names (create a quick lookup dict for efficiency)
            task_lookup = {task.id: task.name for task in self.tasks}
            reco_names = [
                task_lookup.get(tid, f"Unknown Task ID: {tid[:8]}...")
                for tid in recent_task_ids_in_cwd
            ]

            # Format the recommendations string
            reco_parts = [f"[dim]{i+1}.[/dim] {name}" for i, name in enumerate(reco_names)]
            reco_text = "[b]Recent here:[/b] " + "  ".join(reco_parts)
            reco_widget.display = True # Ensure widget is visible
            reco_widget.update(reco_text)

        except Exception as e:
            self.log.error(f"Failed to update recommendations: {e}")
            try:
                 # Attempt to clear and hide the recommendations on error
                 reco_widget = self.query_one("#cwd-recommendations", Static)
                 reco_widget.update("")
                 reco_widget.display = False
            except Exception:
                 pass # Ignore if query fails
    # --- END NEW ---


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
# Needs launch_cwd to record history correctly

def run_task(task: Task, launch_cwd: str) -> None: # Added launch_cwd parameter
    """Updates timestamp and history, then executes the selected task's command."""
    if not task:
        print("No task selected to run.")
        return

    # --- Update timestamp AND add history entry before running ---
    # print(f"Updating timestamp & history for task: {task.name} ({task.id}) in {launch_cwd}")
    if not update_last_run_timestamp(task.id):
        print("Warning: Failed to update run timestamp.", file=sys.stderr)
    add_history_entry(task.id, launch_cwd) # Record execution history
    # ---

    command = task.command
    # The task should run in its *defined* cwd, not necessarily the launch_cwd
    run_cwd = os.path.expanduser(task.cwd) # Expand ~ from task definition

    print(f"\n--- Running Task: {task.name} ---")
    print(f"Directory: {run_cwd}") # Log the directory it WILL run in
    print(f"Command:   {command}")
    print("-" * (len(f"--- Running Task: {task.name} ---"))) # Match separator length

    try:
        # Ensure directory exists before trying to run command in it
        if not Path(run_cwd).is_dir():
             print(f"\nError: Working directory not found: {run_cwd}", file=sys.stderr)
             return

        # Execute the command using shell=True as per design doc v2
        process = subprocess.run(command, shell=True, cwd=run_cwd, check=False) # Use run_cwd

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
