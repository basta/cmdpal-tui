import uuid
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any # Added List, Dict, Any

@dataclass
class TaskParameter:
    """Defines a parameter for a task command."""
    name: str # Name used in placeholder e.g., ${name}
    prompt: Optional[str] = None # Custom prompt for user input

    def __post_init__(self):
         if not self.name:
              raise ValueError("Parameter name cannot be empty.")
         if self.prompt is None:
              self.prompt = f"Enter value for '{self.name}':" # Default prompt


@dataclass
class Task:
    """Represents a single command task."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    command: str = ""
    cwd: str = "~"
    description: Optional[str] = ""
    last_run_timestamp: Optional[float] = None # Unix timestamp

    # --- NEW: Parameter fields ---
    # List of parameter definitions, e.g., [{"name": "file", "prompt": "Enter filename:"}]
    parameters: Optional[List[Dict[str, Any]]] = None
    # Dictionary storing the last values used for parameters, e.g., {"file": "input.txt"}
    last_param_values: Optional[Dict[str, str]] = None
    # --- END NEW ---

    def __post_init__(self):
        if not self.name:
            raise ValueError("Task name cannot be empty.")
        if not self.command:
            raise ValueError("Task command cannot be empty.")
        if not self.cwd:
            self.cwd = "~"
        # Ensure parameters and last_param_values are initialized if needed
        if self.parameters is None:
            self.parameters = [] # Default to empty list if None
        if self.last_param_values is None:
             self.last_param_values = {} # Default to empty dict if None

    # Helper to get parameter definitions as objects
    def get_parameter_definitions(self) -> List[TaskParameter]:
        if not self.parameters:
            return []
        try:
            # Validate and convert dicts to TaskParameter objects
            return [TaskParameter(**param_data) for param_data in self.parameters]
        except (TypeError, ValueError) as e:
            # Log or handle potential errors in parameter definition format
            print(f"Warning: Invalid parameter definition format for task '{self.name}': {e}")
            return []
