import uuid
import time # Import time for default value if needed, though None is better
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Task:
    """Represents a single command task."""
    # Using default_factory to ensure a unique ID is generated for new tasks
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    command: str = ""
    cwd: str = "~"  # Default to home directory
    description: Optional[str] = "" # Optional description
    # --- NEW: Store last run time as Unix timestamp ---
    last_run_timestamp: Optional[float] = None # None means never run

    def __post_init__(self):
        # Basic validation or normalization could go here if needed
        if not self.name:
            raise ValueError("Task name cannot be empty.")
        if not self.command:
            raise ValueError("Task command cannot be empty.")
        if not self.cwd:
            self.cwd = "./" # Ensure cwd is at least "~"
