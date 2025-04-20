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


def fuzzy_search_tasks(
    query: str,
    tasks: typing.List[Task],
    limit: int = 50, # Limit number of results for performance
    score_cutoff: int = 50 # Adjust threshold as needed
) -> typing.List[Task]:
    """
    Performs fuzzy search on tasks based on name and description.

    Args:
        query: The search string entered by the user.
        tasks: The list of all Task objects.
        limit: The maximum number of results to return.
        score_cutoff: The minimum score (0-100) for a match to be included.

    Returns:
        A list of Task objects matching the query.
    """
    if not query:
        return tasks # Return all tasks if query is empty

    # Create a list of choices for fuzzy matching, combining name and description
    # Also store a mapping back to the original Task object
    choices_map = {
        f"{i}: {task.name} {task.description or ''}": task
        for i, task in enumerate(tasks)
    }
    choices = list(choices_map.keys())

    # Use rapidfuzz to find the best matches
    # process.extract returns tuples of (choice, score, index)
    results = process.extract(
        query,
        choices,
        scorer=fuzz.WRatio, # Weighted ratio often gives good results
        limit=limit,
        score_cutoff=score_cutoff
    )

    # Extract the corresponding Task objects from the results
    matched_tasks = [choices_map[result[0]] for result in results]

    return matched_tasks
