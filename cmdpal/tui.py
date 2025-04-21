import os
import subprocess
import sys
import time
import typing
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from textual.app import App, ComposeResult, Binding
from textual.containers import Container, VerticalScroll, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Header, Footer, Input, DataTable, Static, Button, Label
from textual.widgets.data_table import CellDoesNotExist, RowKey
from textual.message import Message
from textual.coordinate import Coordinate
from textual.binding import BindingType
from textual.screen import Screen, ModalScreen

# Assuming Task model and storage functions are defined elsewhere
try:
    from .models import Task, TaskParameter
    from .storage import load_tasks, save_tasks, update_last_run_timestamp, update_last_param_values
    from .storage import load_history, add_history_entry, HistoryEntry
    from .utils import fuzzy_search_tasks
    from .config import DEFAULT_SCORE_CUTOFF, RECOMMENDATIONS_COUNT, TASKS_FILE
except ImportError:
    # Simple placeholders for standalone testing/viewing
    from dataclasses import dataclass, field
    @dataclass
    class TaskParameter: name: str; prompt: Optional[str] = None
    @dataclass
    class Task:
        id: str = ""; name: str = ""; command: str = ""; cwd: str = "~"; description: typing.Optional[str] = ""
        last_run_timestamp: Optional[float] = None; parameters: Optional[List[Dict[str, Any]]] = None
        last_param_values: Optional[Dict[str, str]] = None
        def get_parameter_definitions(self) -> List[TaskParameter]: return [TaskParameter(**p) for p in self.parameters] if self.parameters else []

    HistoryEntry = Dict[str, Any]
    LoadResult = typing.Tuple[typing.List[Task], bool]
    def load_tasks() -> LoadResult: return ([Task(id='1', name='Dummy Task', command='echo hello ${name}', parameters=[{"name":"name", "prompt":"Enter name:"}], last_param_values={"name":"World"})], False)
    def save_tasks(t: typing.List[Task]) -> bool: return True
    def update_last_run_timestamp(tid: str) -> bool: print(f"Simulating timestamp update for {tid}"); return True
    def update_last_param_values(tid: str, p: Dict[str, str]) -> bool: print(f"Simulating param update for {tid}: {p}"); return True
    def load_history() -> List[HistoryEntry]: return [{"timestamp": time.time() - 10, "task_id": "1", "directory": os.getcwd()}]
    def add_history_entry(tid: str, d:str) -> None: print(f"Simulating history add for {tid} in {d}")
    def fuzzy_search_tasks(q, t, **kw) -> typing.List[Task]: return t
    DEFAULT_SCORE_CUTOFF = 50
    RECOMMENDATIONS_COUNT = 3
    TASKS_FILE = Path("~/.config/cmdpal/tasks.json").expanduser()

# --- Parameter Input Screen ---
class ParameterScreen(ModalScreen[Optional[Dict[str, str]]]):
    """Screen to prompt user for task parameter values."""

    DEFAULT_CSS = """
    ParameterScreen {
        align: center middle;
    }
    #dialog {
        padding: 0 1;
        width: 60;
        max-width: 80%;
        height: auto;
        max-height: 80%;
        border: thick $accent;
        background: $surface;
    }
    #dialog Vertical {
        height: auto;
        padding-bottom: 1;
    }
    #dialog Label { margin-top: 1; }
    #dialog Input { width: 100%; }
    #buttons { width: 100%; align-horizontal: right; padding-top: 1; height: auto; }
    #buttons > Button { margin-left: 2; }
    """

    def __init__(self, parameters: List[TaskParameter], initial_values: Optional[Dict[str, str]] = None):
        super().__init__()
        self.parameters = parameters
        self.initial_values = initial_values or {}
        self._inputs: Dict[str, Input] = {}

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            with VerticalScroll():
                 with Vertical():
                    for param in self.parameters:
                        param_name = param.name
                        prompt = param.prompt or f"Enter value for '{param_name}':"
                        initial_value = self.initial_values.get(param_name, "")
                        yield Label(prompt, classes="param-label")
                        input_widget = Input(value=initial_value, id=f"param-input-{param_name}")
                        self._inputs[param_name] = input_widget
                        yield input_widget
            with Horizontal(id="buttons"):
                 yield Button("OK", variant="primary", id="ok")
                 yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        first_input = self.query(Input).first()
        if first_input: first_input.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            results = {name: input_widget.value for name, input_widget in self._inputs.items()}
            self.dismiss(result=results)
        elif event.button.id == "cancel":
            self.dismiss(result=None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        is_param_input = any(event.input == inp for inp in self._inputs.values())
        if is_param_input:
             results = {name: input_widget.value for name, input_widget in self._inputs.items()}
             self.dismiss(result=results)


# --- Main App ---
# Updated return type hint
class CmdPalApp(App[Optional[Tuple[Task, Optional[Dict[str, str]]]]]):
    """The main Textual TUI application for CmdPal."""

    TITLE = "CmdPal - Command Palette"
    SUB_TITLE = "Find and run your commands"

    # --- Use DEFAULT_CSS for layout ---
    DEFAULT_CSS = """
    /* Define layout for the main screen components */
    Screen {
        /* Arrange Header, Reco, Input, MainPane, Footer vertically */
        layout: vertical;
    }

    Header { dock: top; height: auto; }
    Footer { dock: bottom; height: auto; }
    Static#cwd-recommendations {
        dock: top; /* Dock recommendations below header */
        height: auto;
        padding: 0 1;
        /* margin-bottom: 1; */ /* REMOVED margin */
        color: $text-muted;
    }
    Input#filter-input {
        dock: top; /* Dock input below recommendations */
        width: 100%;
        /* margin-bottom: 1; */ /* REMOVED margin */
    }
    Horizontal#main-pane {
        /* This pane takes the remaining space */
        /* No explicit height needed, vertical layout handles it */
    }

    /* Style the side-by-side panes within Horizontal#main-pane */
    Horizontal#main-pane > Container#table-container {
        width: 3fr; /* Assign width using fractional units */
        border-right: thick $accent;
        padding-right: 1;
        height: 100%;
    }
    Horizontal#main-pane > VerticalScroll#preview-container {
        width: 2fr; /* Assign width using fractional units */
        padding-left: 2;
        height: 100%;
    }

    /* Optional: Add padding inside the preview pane itself */
    Static#preview-pane {
        padding: 1 2;
    }

    /* Ensure DataTable fills its container */
    DataTable {
        width: 100%;
        height: 100%; /* Allow table to fill vertical space */
    }
    """
    # --- END DEFAULT_CSS ---

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True, priority=True),
        Binding("escape", "quit", "Quit", show=True),
        Binding("enter", "select_task", "Run Task", show=False),
        Binding("up", "cursor_up", "Cursor Up", show=False, priority=True),
        Binding("down", "cursor_down", "Cursor Down", show=False, priority=True),
        Binding("pageup", "scroll_preview_up", "Preview Up", show=False, priority=True),
        Binding("pagedown", "scroll_preview_down", "Preview Down", show=False, priority=True),
    ]

    tasks: reactive[list[Task]] = reactive(list)
    history: reactive[list[HistoryEntry]] = reactive(list)

    def __init__(self, launch_cwd: str):
        super().__init__()
        self.launch_cwd = launch_cwd
        self._current_filter_query = ""

    def compose(self) -> ComposeResult:
        # Structure matches the vertical layout defined in CSS
        yield Header()
        yield Static(id="cwd-recommendations", markup=True, classes="recommendations")
        yield Input(id="filter-input", placeholder="Filter tasks by name or description...")
        # Use Horizontal layout for Table and Preview
        with Horizontal(id="main-pane"):
            with Container(id="table-container"): # Container for table
                 yield DataTable(id="task-table", cursor_type="row", zebra_stripes=True)
            with VerticalScroll(id="preview-container"): # Container for preview (scrollable)
                yield Static(id="preview-pane", expand=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        loaded_tasks, needs_task_resave = load_tasks()
        self.tasks = loaded_tasks
        if needs_task_resave:
             self.log.info(f"Resaving tasks file ({TASKS_FILE}) with newly generated IDs...")
             if not save_tasks(self.tasks): self.log.warning("Failed to resave tasks file after generating IDs.")
        self.history = load_history()
        self._update_recommendations()
        table = self.query_one(DataTable)
        table.add_column("Name", key="name"); table.add_column("Description", key="description"); table.add_column("CWD", key="cwd")
        self._update_table()
        self.query_one("#filter-input", Input).focus()

    # --- Event Handlers ---
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self._current_filter_query = event.value
            self._update_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-input":
            self.action_select_task()

    def on_data_table_row_highlighted(self, event) -> None:
        if event.row_key is not None:
            try:
                task_id = str(event.row_key.value)
                selected_task = next((t for t in self.tasks if t.id == task_id), None)
                self._update_preview_pane(selected_task)
            except Exception as e: self.log.error(f"Error finding task for preview: {e}"); self._update_preview_pane(None)
        else: self._update_preview_pane(None)

    def on_data_table_row_selected(self, event) -> None:
        # Handles Enter press on the table
        self.action_select_task()

    # --- Actions ---
    def action_select_task(self) -> None:
        table = self.query_one(DataTable)
        if not table.is_valid_row_index(table.cursor_row): return
        try:
            cell_key = table.coordinate_to_cell_key(table.cursor_coordinate)
            row_key = cell_key.row_key
            if row_key is None: return
            task_id = str(row_key.value)
            selected_task = next((t for t in self.tasks if t.id == task_id), None)
            if not selected_task: return
            parameters = selected_task.get_parameter_definitions()
            last_values = selected_task.last_param_values
            if parameters:
                def handle_parameter_results(results: Optional[Dict[str, str]]):
                    if results is not None: self.exit(result=(selected_task, results))
                self.push_screen(ParameterScreen(parameters=parameters, initial_values=last_values), handle_parameter_results)
            else: self.exit(result=(selected_task, None))
        except CellDoesNotExist: self.log.error(f"CellDoesNotExist at cursor {table.cursor_coordinate} during selection")
        except Exception as e: self.log.error(f"Error during task selection: {e}")

    def action_quit_app(self) -> None: self.exit(result=None)
    def action_cursor_up(self) -> None:
        table = self.query_one(DataTable);
        if table.row_count > 0: table.move_cursor(row=max(0, table.cursor_row - 1))
    def action_cursor_down(self) -> None:
        table = self.query_one(DataTable);
        if table.row_count > 0: table.move_cursor(row=min(table.row_count - 1, table.cursor_row + 1))
    def action_scroll_preview_up(self) -> None:
        try: self.query_one("#preview-container", VerticalScroll).scroll_page_up(animate=False)
        except Exception as e: self.log.error(f"Error scrolling preview up: {e}")
    def action_scroll_preview_down(self) -> None:
        try: self.query_one("#preview-container", VerticalScroll).scroll_page_down(animate=False)
        except Exception as e: self.log.error(f"Error scrolling preview down: {e}")

    # --- Helper Methods (Condensed for brevity) ---
    def _update_table(self) -> None:
        table = self.query_one(DataTable); query = self._current_filter_query
        tasks_to_display: List[Task]
        if not query: tasks_to_display = sorted(self.tasks, key=lambda t: t.last_run_timestamp or 0, reverse=True)
        else: tasks_to_display = fuzzy_search_tasks(query, self.tasks, score_cutoff=DEFAULT_SCORE_CUTOFF)
        current_cursor_row = table.cursor_row if table.is_valid_row_index(table.cursor_row) else 0
        current_row_key: Optional[RowKey] = None
        if table.is_valid_coordinate(Coordinate(row=current_cursor_row, column=0)):
            try: current_cell_key = table.coordinate_to_cell_key(Coordinate(row=current_cursor_row, column=0)); current_row_key = current_cell_key.row_key
            except CellDoesNotExist: current_row_key = None
        table.clear(); new_row_keys_values = []
        for task in tasks_to_display:
            desc = (task.description or "")[:50]; desc += "..." if len(task.description or "") > 50 else ""
            table.add_row(task.name, desc, task.cwd, key=task.id); new_row_keys_values.append(task.id)
        if table.row_count > 0:
            target_row = 0
            if current_row_key is not None and current_row_key.value in new_row_keys_values:
                try: target_row = new_row_keys_values.index(current_row_key.value)
                except ValueError: target_row = 0
            else: target_row = max(0, min(current_cursor_row, table.row_count - 1))
            table.move_cursor(row=target_row)
        task_at_cursor = None
        if table.is_valid_coordinate(table.cursor_coordinate):
             try:
                 cursor_cell_key = table.coordinate_to_cell_key(table.cursor_coordinate); cursor_row_key = cursor_cell_key.row_key
                 if cursor_row_key is not None: task_id = str(cursor_row_key.value); task_at_cursor = next((t for t in self.tasks if t.id == task_id), None)
             except CellDoesNotExist: task_at_cursor = None
        self._update_preview_pane(task_at_cursor)

    def _update_recommendations(self) -> None:
        try:
            reco_widget = self.query_one("#cwd-recommendations", Static)
            cwd_history = [e for e in self.history if e.get("directory") == self.launch_cwd]
            cwd_history.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            recent_task_ids_in_cwd, seen_ids = [], set()
            for entry in cwd_history:
                task_id = entry.get("task_id");
                if task_id and task_id not in seen_ids: recent_task_ids_in_cwd.append(task_id); seen_ids.add(task_id)
                if len(recent_task_ids_in_cwd) >= RECOMMENDATIONS_COUNT: break
            if not recent_task_ids_in_cwd: reco_widget.update("[dim]No recent tasks recorded in this directory.[/dim]"); reco_widget.display = False; return
            task_lookup = {task.id: task.name for task in self.tasks}
            reco_names = [task_lookup.get(tid, f"Unknown:{tid[:6]}..") for tid in recent_task_ids_in_cwd]
            reco_parts = [f"[dim]{i+1}.[/dim] {name}" for i, name in enumerate(reco_names)]
            reco_text = "[b]Recent here:[/b] " + "  ".join(reco_parts)
            reco_widget.display = True; reco_widget.update(reco_text)
        except Exception as e:
            self.log.error(f"Failed to update recommendations: {e}")
            try: self.query_one("#cwd-recommendations", Static).update(""); self.query_one("#cwd-recommendations", Static).display = False
            except Exception: pass

    def _update_preview_pane(self, task: Optional[Task]) -> None:
        try:
            preview_pane = self.query_one("#preview-pane", Static)
            if task:
                escaped_command = task.command.replace("`", "\\`")
                preview_content = f"**Command:**\n```sh\n{escaped_command}\n```\n\n**Directory:**\n`{task.cwd}`"
                preview_pane.update(preview_content)
            else: preview_pane.update("[dim]Select a task to see details...[/dim]")
        except Exception as e: self.log.error(f"Failed to update preview pane: {e}")

# --- Command Execution Function ---
def run_task(task: Task, param_values: Optional[Dict[str, str]], launch_cwd: str) -> None:
    if not task: print("No task selected to run."); return
    if not update_last_run_timestamp(task.id): print("Warning: Failed to update run timestamp.", file=sys.stderr)
    add_history_entry(task.id, launch_cwd)
    command = task.command
    if param_values:
        substituted_command = command
        try:
            for name, value in param_values.items(): placeholder = f"${{{name}}}"; substituted_command = substituted_command.replace(placeholder, value)
            command = substituted_command
        except Exception as e: print(f"Error substituting parameters: {e}", file=sys.stderr); command = substituted_command
    run_cwd = os.path.expanduser(task.cwd)
    print(f"\n--- Running Task: {task.name} ---"); print(f"Directory: {run_cwd}"); print(f"Command:   {command}"); print("-" * (len(f"--- Running Task: {task.name} ---")))
    try:
        if not Path(run_cwd).is_dir(): print(f"\nError: Working directory not found: {run_cwd}", file=sys.stderr); return
        process = subprocess.run(command, shell=True, cwd=run_cwd, check=False)
        if process.returncode != 0: print(f"\nWarning: Task exited with non-zero status: {process.returncode}", file=sys.stderr)
        else: print(f"\nTask '{task.name}' appears to have completed.")
    except FileNotFoundError: cmd_base = command.split()[0] if command else ""; print(f"\nError: Command '{cmd_base}' not found. Is it installed and in your PATH?", file=sys.stderr)
    except Exception as e: print(f"\nAn error occurred while trying to run the task: {e}", file=sys.stderr)
