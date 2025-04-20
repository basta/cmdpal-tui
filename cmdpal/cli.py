import argparse
import sys
from typing import List, Optional

from .models import Task
# Import LoadResult type hint if needed, though not strictly necessary here
from .storage import load_tasks, save_tasks, find_task_by_id, find_tasks_by_name

# --- Helper to handle resave after load ---
def _load_and_resave_if_needed() -> List[Task]:
    """Loads tasks and resaves immediately if any IDs were generated."""
    tasks, needs_resave = load_tasks()
    if needs_resave:
        print(f"Info: Resaving tasks file with newly generated IDs...")
        if not save_tasks(tasks):
            print(f"Warning: Failed to resave tasks file after generating IDs.", file=sys.stderr)
            # Decide if we should exit or continue with in-memory IDs
    return tasks

# --- Command Functions ---

def list_tasks_cli(args: argparse.Namespace):
    """Handles the 'list' CLI command."""
    # Load tasks (and resave if IDs were generated)
    tasks = _load_and_resave_if_needed()

    if not tasks:
        print("No tasks defined yet.")
        return

    print(f"{'ID':<38} {'Name':<25} {'CWD':<30} {'Description'}")
    print("-" * 120)
    for task in tasks:
        desc = (task.description or "")[:40] # Truncate long descriptions
        if len(task.description or "") > 40:
            desc += "..."
        print(f"{task.id:<38} {task.name:<25} {task.cwd:<30} {desc}")

def add_task_cli(args: argparse.Namespace):
    """Handles the 'add' CLI command."""
    # Load tasks (and resave if IDs were generated)
    tasks = _load_and_resave_if_needed()

    try:
        new_task = Task(
            name=args.name,
            command=args.cmd,
            cwd=args.cwd or "~", # Use default if not provided
            description=args.desc
        )
        # Check for duplicate name before adding (optional, but good practice)
        existing_names = [t.name for t in tasks]
        if new_task.name in existing_names:
            print(f"Warning: Task with name '{new_task.name}' already exists. Adding anyway.", file=sys.stderr)

        tasks.append(new_task)
        # Save *after* adding the new task
        if save_tasks(tasks):
            print(f"Task '{new_task.name}' added successfully with ID: {new_task.id}")
        else:
            print("Failed to save new task.", file=sys.stderr)
            sys.exit(1)
    except ValueError as e:
        print(f"Error adding task: {e}", file=sys.stderr)
        sys.exit(1)


def edit_task_cli(args: argparse.Namespace):
    """Handles the 'edit' CLI command."""
    # Load tasks (and resave if IDs were generated)
    tasks = _load_and_resave_if_needed()

    identifier = args.identifier
    task_to_edit: Optional[Task] = None

    # Try finding by ID first
    task_to_edit = find_task_by_id(identifier, tasks)

    # If not found by ID, try finding by name
    if not task_to_edit:
        matching_tasks = find_tasks_by_name(identifier, tasks)
        if len(matching_tasks) == 1:
            task_to_edit = matching_tasks[0]
        elif len(matching_tasks) > 1:
            print(f"Error: Multiple tasks found with name '{identifier}'. Please use the unique ID.", file=sys.stderr)
            print("Matching IDs:")
            for t in matching_tasks:
                print(f"- {t.id}")
            sys.exit(1)

    if not task_to_edit:
        print(f"Error: Task not found with identifier '{identifier}'.", file=sys.stderr)
        sys.exit(1)

    # Update fields if provided
    updated = False
    if args.name is not None:
        # Optional: Check if new name conflicts with another existing task's name
        if any(t.name == args.name and t.id != task_to_edit.id for t in tasks):
             print(f"Warning: Another task already exists with the name '{args.name}'.", file=sys.stderr)
        task_to_edit.name = args.name
        updated = True
    if args.cmd is not None:
        task_to_edit.command = args.cmd
        updated = True
    if args.cwd is not None:
        task_to_edit.cwd = args.cwd
        updated = True
    if args.desc is not None:
        task_to_edit.description = args.desc
        updated = True

    if updated:
        # Save *after* editing the task
        if save_tasks(tasks):
            print(f"Task '{identifier}' updated successfully.")
        else:
            print("Failed to save updated tasks.", file=sys.stderr)
            sys.exit(1)
    else:
        print("No changes specified for the task.")


def delete_task_cli(args: argparse.Namespace):
    """Handles the 'delete' CLI command."""
    # Load tasks (and resave if IDs were generated)
    tasks = _load_and_resave_if_needed()

    identifier = args.identifier
    task_to_delete: Optional[Task] = None
    task_index: Optional[int] = None

    # Try finding by ID first
    for i, task in enumerate(tasks):
        if task.id == identifier:
            task_to_delete = task
            task_index = i
            break

    # If not found by ID, try finding by name
    if task_to_delete is None:
        matching_tasks = []
        matching_indices = []
        for i, task in enumerate(tasks):
             if task.name == identifier:
                 matching_tasks.append(task)
                 matching_indices.append(i)

        if len(matching_tasks) == 1:
            task_to_delete = matching_tasks[0]
            task_index = matching_indices[0]
        elif len(matching_tasks) > 1:
            print(f"Error: Multiple tasks found with name '{identifier}'. Please use the unique ID.", file=sys.stderr)
            print("Matching IDs:")
            for t in matching_tasks:
                print(f"- {t.id}")
            sys.exit(1)

    if task_to_delete is None or task_index is None:
        print(f"Error: Task not found with identifier '{identifier}'.", file=sys.stderr)
        sys.exit(1)

    # Confirmation
    confirm = input(f"Are you sure you want to delete task '{task_to_delete.name}' (ID: {task_to_delete.id})? [y/N]: ")
    if confirm.lower() != 'y':
        print("Deletion cancelled.")
        return

    # Delete the task
    del tasks[task_index]

    # Save *after* deleting the task
    if save_tasks(tasks):
        print(f"Task '{identifier}' deleted successfully.")
    else:
        print("Failed to save tasks after deletion.", file=sys.stderr)
        sys.exit(1)


# --- Argument Parser Setup ---

def setup_cli_parsers(parser: argparse.ArgumentParser):
    """Configures subparsers for CLI commands."""
    subparsers = parser.add_subparsers(dest='command', help='Sub-command help')
    subparsers.required = False # Make subcommands optional (so running without args launches TUI)

    # List command
    parser_list = subparsers.add_parser('list', help='List all defined tasks')
    parser_list.set_defaults(func=list_tasks_cli)

    # Add command
    parser_add = subparsers.add_parser('add', help='Add a new task')
    parser_add.add_argument('--name', required=True, help='Name of the task')
    parser_add.add_argument('--cmd', required=True, help='Command string to execute')
    parser_add.add_argument('--cwd', default='~', help='Working directory (default: home)')
    parser_add.add_argument('--desc', help='Optional description for the task')
    parser_add.set_defaults(func=add_task_cli)

    # Edit command
    parser_edit = subparsers.add_parser('edit', help='Edit an existing task by ID or unique name')
    parser_edit.add_argument('identifier', help='ID or unique name of the task to edit')
    parser_edit.add_argument('--name', help='New name for the task')
    parser_edit.add_argument('--cmd', help='New command string')
    parser_edit.add_argument('--cwd', help='New working directory')
    parser_edit.add_argument('--desc', help='New description')
    parser_edit.set_defaults(func=edit_task_cli)

    # Delete command
    parser_delete = subparsers.add_parser('delete', help='Delete a task by ID or unique name')
    parser_delete.add_argument('identifier', help='ID or unique name of the task to delete')
    # Could add a --force flag to skip confirmation later
    parser_delete.set_defaults(func=delete_task_cli)
