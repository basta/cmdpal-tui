import typing
from rapidfuzz import process, fuzz

# Assuming Task model is defined elsewhere, e.g., from .models import Task
# For standalone testing, define a placeholder:
try:
    from .models import Task
except ImportError:
    from dataclasses import dataclass
    @dataclass
    class Task:
        id: str = ""
        name: str = ""
        command: str = ""
        cwd: str = "~"
        description: typing.Optional[str] = ""
        last_run_timestamp: typing.Optional[float] = None # Keep model consistent


def fuzzy_search_tasks(
    query: str,
    tasks: typing.List[Task],
    limit: int = 50, # Limit number of results for performance
    score_cutoff: int = 50 # Adjust threshold as needed
) -> typing.List[Task]:
    """
    Performs fuzzy search on tasks based on name, description, AND command.

    Args:
        query: The search string entered by the user.
        tasks: The list of all Task objects.
        limit: The maximum number of results to return.
        score_cutoff: The minimum score (0-100) for a match to be included.

    Returns:
        A list of Task objects matching the query, ordered by relevance score.
    """
    if not query:
        # If query is empty, return tasks sorted by most recent timestamp (desc)
        # This matches the default sort order shown in the TUI when filter is empty
        return sorted(
            tasks,
            key=lambda t: t.last_run_timestamp or 0,
            reverse=True
        )

    # --- FIX: Create map from searchable string back to task ID ---
    # And create list of the strings themselves to search against
    search_map = {} # Map: "Name Desc Cmd" -> task_id
    search_choices = [] # List: ["Name1 Desc1 Cmd1", "Name2 Desc2 Cmd2", ...]
    for task in tasks:
        # Combine the fields into a single string for searching
        searchable_string = f"{task.name} {task.description or ''} {task.command}"
        search_choices.append(searchable_string)
        # Store mapping from this unique string back to the task ID
        # Note: If multiple tasks somehow produce the exact same combined string,
        # this map will only store the last one encountered. This is unlikely
        # given the inclusion of name/command/desc and unique IDs.
        search_map[searchable_string] = task.id
    # --- END FIX ---


    # --- FIX: Search against the combined strings directly ---
    # process.extract returns list of tuples: (matched_string, score, index_in_search_choices)
    results = process.extract(
        query,
        search_choices, # Search against the actual combined strings
        # No processor needed now, we search the strings directly
        scorer=fuzz.WRatio, # Weighted ratio often gives good results
        limit=limit,
        score_cutoff=score_cutoff
    )
    # --- END FIX ---

    # --- FIX: Map matched strings back to Task objects via task ID ---
    # Create a quick lookup dict for tasks by ID
    task_lookup = {task.id: task for task in tasks}
    matched_tasks = []
    seen_ids = set() # Ensure we don't add duplicate tasks if search yields odd results
    for result_tuple in results:
        matched_string = result_tuple[0]
        # Find the task ID associated with the matched string
        task_id = search_map.get(matched_string)
        if task_id and task_id not in seen_ids:
            task = task_lookup.get(task_id)
            if task:
                matched_tasks.append(task)
                seen_ids.add(task_id)
    # --- END FIX ---

    # The results from process.extract are already sorted by score (highest first)
    return matched_tasks
