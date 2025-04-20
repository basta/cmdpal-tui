# CmdPal 🚀

**CmdPal** (Command Palette / Command Pal) is a fast, keyboard-driven TUI (Terminal User Interface) application for efficiently managing and executing your frequently used shell commands and scripts.

Stop digging through history or notes! Define your tasks once – with names, commands, working directories, and descriptions – then find and run them instantly using an intuitive fuzzy search interface.

Built with Python and the modern [Textual](https://textual.textualize.io/) framework.

## Screenshot

\[\[Screenshot of CmdPal TUI in action\]\]
*(A brief visual overview of the main TUI interface)*

## Features ✨

* **TUI Launcher:** Interactive terminal interface for browsing, searching, and running tasks.
* **Fuzzy Search:** Quickly filter tasks by name or description as you type.
* **Keyboard Driven:** Designed for efficient keyboard navigation and execution (Up/Down, Enter, Esc).
* **Task Definition:** Define tasks with a name, the command string, a specific working directory (`cwd`), and an optional description.
* **Persistence:** Tasks are stored locally in a simple JSON file.
* **Automatic ID Generation:** Manually add tasks to the JSON without an `id`; CmdPal generates and persists one automatically.
* **Recency Sorting:** Displays tasks sorted by most recently run when the filter is empty.
* **CLI Management:** Add, list, edit, and delete tasks directly from the command line.
* **Cross-Platform:** Runs on Linux, macOS, and Windows (wherever Python and Textual are supported).

## Installation 📦

The recommended way to install CmdPal for global use is via `pipx`. This installs the application and its dependencies in an isolated environment while making the `cmdpal` command available system-wide.

1.  **Install `pipx`** (if you don't have it):
    ```bash
    # Using pip (ensure ~/.local/bin is on your PATH)
    python -m pip install --user pipx
    python -m pipx ensurepath

    # Or use your system package manager (e.g., apt, brew)
    # sudo apt install pipx
    # brew install pipx
    ```

2.  **Install CmdPal:**
    * Clone this repository:
        ```bash
        git clone [https://github.com/your_username/cmdpal-tui.git](https://github.com/your_username/cmdpal-tui.git) # Replace with actual URL
        cd cmdpal-tui
        ```
    * Install using `pipx`:
        ```bash
        pipx install .
        ```

Now you should be able to run `cmdpal` from anywhere!

## Usage 🚀

### Launching the TUI

Simply run the command in your terminal:

```bash
cmdpal
```

### Using the TUI

* **Filtering:** Start typing in the input box to filter tasks by name/description using fuzzy search.
* **Navigation:** Use the `Up` and `Down` arrow keys to highlight tasks in the list.
* **Preview:** The pane at the bottom shows the full command and working directory for the highlighted task.
* **Execution:** Press `Enter` on the highlighted task to execute its command. The TUI will close, and confirmation/execution details will print to your terminal.
* **Quitting:** Press `Escape` or `Ctrl+C` to exit the TUI without running a command.

### Using the CLI for Task Management

Manage your tasks directly without launching the TUI:

* **List Tasks:**
    ```bash
    cmdpal list
    ```
    *(Displays ID, Name, CWD, and Description for all tasks)*

* **Add Task:**
    ```bash
    cmdpal add --name "My Task Name" --cmd "echo 'Hello World'" --cwd "/path/to/run/in" --desc "A description"
    ```
    *(Requires `--name` and `--cmd`. `--cwd` defaults to `~`, `--desc` is optional)*

* **Edit Task:**
    ```bash
    # Identify by unique ID (recommended if names might clash)
    cmdpal edit <TASK_ID> --name "New Name" --cmd "new command"

    # Or identify by unique Name
    cmdpal edit "My Task Name" --cwd "/new/path"
    ```
    *(Specify only the arguments you want to change. Fails if the name matches multiple tasks.)*

* **Delete Task:**
    ```bash
    # Identify by unique ID (recommended)
    cmdpal delete <TASK_ID>

    # Or identify by unique Name
    cmdpal delete "My Task Name"
    ```
    *(Prompts for confirmation. Fails if the name matches multiple tasks.)*

* **Show Tasks File Path:**
    ```bash
    cmdpal --tasks-path
    ```
    *(Prints the full path to the `tasks.json` file and exits)*

## Configuration ⚙️

Tasks are stored in a JSON file located at:

* `$XDG_CONFIG_HOME/cmdpal/tasks.json` (if `XDG_CONFIG_HOME` is set)
* `~/.config/cmdpal/tasks.json` (default fallback)

You can manually edit this file (CmdPal will generate missing IDs on next run), but using the CLI commands is generally recommended.

## Development Setup 🛠️

Interested in contributing or modifying CmdPal?

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your_username/cmdpal-tui.git](https://github.com/your_username/cmdpal-tui.git) # Replace with actual URL
    cd cmdpal-tui
    ```
2.  **Create virtual environment using `uv`:**
    ```bash
    uv venv
    source .venv/bin/activate # Or equivalent for your shell
    ```
3.  **Install in editable mode with dev dependencies:**
    ```bash
    uv pip install -e ".[dev]"
    ```
4.  Now you can run `cmdpal` and your code changes will be reflected immediately. You can also run linters/tests (e.g., `ruff check .`, `pytest`).

## Contributing 🤝

Contributions are welcome! Please feel free to open an issue or submit a pull request.
## License 📄

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
