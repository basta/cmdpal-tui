import os
from pathlib import Path

# Application Name
APP_NAME = "cmdpal"

# Determine base directory for configuration using XDG Base Directory Spec if possible
XDG_CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME')
if XDG_CONFIG_HOME:
    APP_DIR = Path(XDG_CONFIG_HOME) / APP_NAME
else:
    # Fallback to default ~/.config/appname
    APP_DIR = Path.home() / ".config" / APP_NAME

# Define the path to the tasks JSON file
TASKS_FILE = APP_DIR / "tasks.json"

# --- NEW: History File Configuration ---
HISTORY_FILE = APP_DIR / "history.json"
HISTORY_MAX_SIZE = 200 # Max number of history entries to keep
# --- END NEW ---

# TUI Configuration (example)
DEFAULT_SCORE_CUTOFF = 60 # Minimum score for fuzzy search results
RECOMMENDATIONS_COUNT = 5 # Number of CWD-specific recommendations to show
