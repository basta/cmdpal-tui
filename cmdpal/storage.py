import json
import os
import sys # Import sys for stderr
import time # Import time for timestamping
import typing
import uuid # Import uuid
from dataclasses import asdict
from typing import List, Dict, Any # Use specific types

# Import config variables
from .config import TASKS_FILE, HISTORY_FILE, HISTORY_MAX_SIZE, APP_DIR
from .models import Task

# Define return type for load_tasks
LoadResult = typing.Tuple[typing.List[Task], bool]
HistoryEntry = Dict[str, Any] # Type alias for history entries

# --- Task Loading/Saving ---

def load_tasks() -> LoadResult:
    """
    Loads tasks from the JSON storage file.
    If a task dictionary lacks a valid 'id', a new UUID is generated.
    Handles missing 'last_run_timestamp' field gracefully.

    Returns:
        A tuple containing:
            - list[Task]: The list of loaded/updated Task objects.
            - bool: True if any IDs were generated (file needs resaving), False otherwise.
    """
    if not TASKS_FILE.exists():
        return ([], False) # Return empty list and False for needs_resave

    tasks_objects: typing.List[Task] = []
    needs_resave = False # Flag to track if IDs were generated

    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            # Handle empty file case
            content = f.read()
            if not content:
                return ([], False)
            tasks_data_list = json.loads(content) # Use loads after reading

            if not isinstance(tasks_data_list, list):
                 print(f"Warning: Invalid format in {TASKS_FILE}. Expected a list.", file=sys.stderr)
                 return ([], False)

            for task_data in tasks_data_list:
                if not isinstance(task_data, dict):
                    print(f"Warning: Skipping invalid task entry (not a dictionary): {task_data}", file=sys.stderr)
                    continue

                task_id = task_data.get("id")
                task_name_for_log = task_data.get('name', 'Unnamed') # For logging

                # Ensure last_run_timestamp exists, default to None if missing
                if "last_run_timestamp" not in task_data:
                    task_data["last_run_timestamp"] = None

                # Check if ID is missing or invalid (None or empty string)
                if not task_id:
                    # ID is missing/invalid, generate a new one
                    new_id = str(uuid.uuid4())
                    task_data['id'] = new_id # Add the new ID to the dictionary
                    needs_resave = True # Mark that we need to save back
                    # Don't print info here, let caller handle confirmation if needed
                    try:
                        # Create Task object using the updated dict (with new ID)
                        task = Task(**task_data)
                        tasks_objects.append(task)
                    except (TypeError, ValueError) as task_create_err:
                         print(f"Warning: Skipping task '{task_name_for_log}' due to creation error after ID generation: {task_create_err} - Data: {task_data}", file=sys.stderr)

                else:
                    # ID exists and is not empty, create Task object normally
                    try:
                        task = Task(**task_data)
                        tasks_objects.append(task)
                    except (TypeError, ValueError) as task_create_err:
                         print(f"Warning: Skipping task '{task_name_for_log}' due to creation error: {task_create_err} - Data: {task_data}", file=sys.stderr)


    except (json.JSONDecodeError, IOError, TypeError) as e:
        # Handle potential errors during file reading or data conversion
        print(f"Error loading tasks from {TASKS_FILE}: {e}", file=sys.stderr)
        return ([], False)
    except Exception as e: # Catch unexpected errors during processing
        print(f"Unexpected error processing tasks file {TASKS_FILE}: {e}", file=sys.stderr)
        return ([], False)

    # Return the list of tasks and the flag indicating if resave is needed
    return (tasks_objects, needs_resave)

def save_tasks(tasks: typing.List[Task]) -> bool:
    """Saves the list of tasks to the JSON storage file."""
    try:
        # Ensure the application config directory exists
        APP_DIR.mkdir(parents=True, exist_ok=True)

        # Convert list of Task objects to list of dictionaries
        tasks_data = [asdict(task) for task in tasks]

        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, indent=2) # Use indent for readability
        return True
    except (IOError, TypeError) as e:
        print(f"Error saving tasks to {TASKS_FILE}: {e}", file=sys.stderr)
        return False
    except Exception as e: # Catch unexpected errors during saving
        print(f"Unexpected error saving tasks file {TASKS_FILE}: {e}", file=sys.stderr)
        return False

def update_last_run_timestamp(task_id_to_update: str) -> bool:
    """Updates the last_run_timestamp for a specific task and saves the tasks file."""
    tasks, _ = load_tasks() # Load current tasks (ignore needs_resave flag here)
    task_found = False
    for task in tasks:
        if task.id == task_id_to_update:
            task.last_run_timestamp = time.time() # Set to current Unix timestamp
            task_found = True
            break

    if task_found:
        # Save the entire list back with the updated timestamp
        if save_tasks(tasks):
            return True
        else:
            print(f"Error: Failed to save updated timestamp for task ID {task_id_to_update}", file=sys.stderr)
            return False
    else:
        # Don't print warning if task not found, might happen if task was deleted
        # print(f"Warning: Could not find task with ID {task_id_to_update} to update timestamp.", file=sys.stderr)
        return False


def find_task_by_id(task_id: str, tasks: typing.List[Task]) -> typing.Optional[Task]:
    """Finds a task by its unique ID."""
    for task in tasks:
        if task.id == task_id:
            return task
    return None

def find_tasks_by_name(name: str, tasks: typing.List[Task]) -> typing.List[Task]:
    """Finds tasks by name (case-sensitive)."""
    return [task for task in tasks if task.name == name]


# --- NEW: History Functions ---

def load_history() -> List[HistoryEntry]:
    """Loads the execution history from the JSON file."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                return []
            history_data = json.loads(content)
            if isinstance(history_data, list):
                # Basic validation could be added here if needed
                return history_data
            else:
                print(f"Warning: Invalid format in {HISTORY_FILE}. Expected a list.", file=sys.stderr)
                return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading history from {HISTORY_FILE}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Unexpected error loading history file {HISTORY_FILE}: {e}", file=sys.stderr)
        return []


def save_history(history: List[HistoryEntry]) -> bool:
    """Saves the execution history list to the JSON file."""
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
        return True
    except (IOError, TypeError) as e:
        print(f"Error saving history to {HISTORY_FILE}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error saving history file {HISTORY_FILE}: {e}", file=sys.stderr)
        return False

def add_history_entry(task_id: str, directory: str) -> None:
    """Adds a new entry to the history file and prunes old entries."""
    if not task_id or not directory:
        print("Warning: Attempted to add history entry with missing task_id or directory.", file=sys.stderr)
        return

    history = load_history()
    timestamp = time.time()

    new_entry: HistoryEntry = {
        "timestamp": timestamp,
        "task_id": task_id,
        "directory": directory # Store the directory where it was run
    }

    history.append(new_entry)

    # Prune history if it exceeds max size
    if len(history) > HISTORY_MAX_SIZE:
        history = history[-HISTORY_MAX_SIZE:]

    if not save_history(history):
        print("Error: Failed to save updated history.", file=sys.stderr)

# --- END NEW ---
