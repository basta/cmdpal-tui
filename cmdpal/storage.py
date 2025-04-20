import json
import os
import typing
import uuid # Import uuid
from dataclasses import asdict

from .config import TASKS_FILE, APP_DIR
from .models import Task

def load_tasks() -> typing.List[Task]:
    """
    Loads tasks from the JSON storage file.
    If a task dictionary lacks a valid 'id', a new UUID is generated.
    If any IDs were generated, the file is saved back immediately.
    """
    if not TASKS_FILE.exists():
        return [] # Return empty list if file doesn't exist

    tasks_objects: typing.List[Task] = []
    needs_resave = False # Flag to track if IDs were generated

    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            tasks_data_list = json.load(f)

            if not isinstance(tasks_data_list, list):
                 print(f"Warning: Invalid format in {TASKS_FILE}. Expected a list.", file=sys.stderr)
                 return []

            for task_data in tasks_data_list:
                if not isinstance(task_data, dict):
                    print(f"Warning: Skipping invalid task entry (not a dictionary): {task_data}", file=sys.stderr)
                    continue

                task_id = task_data.get("id")

                # Check if ID is missing or invalid (None or empty string)
                if not task_id:
                    # ID is missing/invalid, generate a new one
                    new_id = str(uuid.uuid4())
                    task_data['id'] = new_id # Add the new ID to the dictionary
                    needs_resave = True # Mark that we need to save back
                    print(f"Info: Generated new ID '{new_id}' for task '{task_data.get('name', 'Unnamed')}'")
                    try:
                        # Create Task object using the updated dict (with new ID)
                        task = Task(**task_data)
                        tasks_objects.append(task)
                    except (TypeError, ValueError) as task_create_err:
                         print(f"Warning: Skipping task due to creation error after ID generation: {task_create_err} - Data: {task_data}", file=sys.stderr)

                else:
                    # ID exists and is not empty, create Task object normally
                    try:
                        task = Task(**task_data)
                        tasks_objects.append(task)
                    except (TypeError, ValueError) as task_create_err:
                         print(f"Warning: Skipping task due to creation error: {task_create_err} - Data: {task_data}", file=sys.stderr)


    except (json.JSONDecodeError, IOError, TypeError) as e:
        # Handle potential errors during file reading or data conversion
        print(f"Error loading tasks from {TASKS_FILE}: {e}", file=sys.stderr)
        return []
    except Exception as e: # Catch unexpected errors during processing
        print(f"Unexpected error processing tasks file {TASKS_FILE}: {e}", file=sys.stderr)
        return []


    # If we generated any IDs, save the updated list back to the file
    if needs_resave:
        print(f"Info: Resaving tasks file ({TASKS_FILE}) with newly generated IDs...")
        if not save_tasks(tasks_objects):
             print(f"Warning: Failed to resave tasks file after generating IDs.", file=sys.stderr)
             # Continue with loaded tasks, but file won't have new IDs yet

    return tasks_objects

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


def find_task_by_id(task_id: str, tasks: typing.List[Task]) -> typing.Optional[Task]:
    """Finds a task by its unique ID."""
    for task in tasks:
        if task.id == task_id:
            return task
    return None

def find_tasks_by_name(name: str, tasks: typing.List[Task]) -> typing.List[Task]:
    """Finds tasks by name (case-sensitive)."""
    return [task for task in tasks if task.name == name]
