import sys
import os

# Add the current directory to sys.path so we can import the cmdpal package
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from cmdpal.models import Task
    from cmdpal.storage import load_tasks, save_tasks
except ImportError as e:
    print(f"Error importing cmdpal modules: {e}")
    sys.exit(1)

def add_examples():
    tasks, _ = load_tasks()
    
    example_tasks = [
        {
            "name": "Git Status",
            "command": "git status",
            "cwd": ".",
            "description": "Show the working tree status"
        },
        {
            "name": "Python Version",
            "command": "python --version",
            "cwd": "~",
            "description": "Check the installed Python version"
        },
        {
            "name": "List Files (Current Dir)",
            "command": "dir" if os.name == 'nt' else "ls -F",
            "cwd": ".",
            "description": "List files and folders in the current directory"
        },
        {
            "name": "Echo Message",
            "command": "echo ${message}",
            "cwd": ".",
            "description": "Echo a custom message to the console",
            "parameters": [
                {
                    "name": "message",
                    "prompt": "Enter message to echo:"
                }
            ]
        },
        {
            "name": "Pro GIF Maker (FFmpeg)",
            "command": "ffmpeg -i ${input} -vf \"fps=${fps},scale=${width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse\" -loop 0 ${output}",
            "cwd": ".",
            "description": "Convert video to high-quality GIF with custom FPS and scale",
            "parameters": [
                {"name": "input", "prompt": "Input video file:"},
                {"name": "output", "prompt": "Output GIF filename:"},
                {"name": "fps", "prompt": "Frames per second (e.g., 15):"},
                {"name": "width", "prompt": "Width in pixels (e.g., 480):"}
            ]
        },
        {
            "name": "Docker Dev Env",
            "command": "docker run --rm -it -p ${host_port}:${container_port} -v ${local_path}:${container_path} -w ${container_path} ${image} ${cmd}",
            "cwd": ".",
            "description": "Launch a disposable Docker container with volume and port mapping",
            "parameters": [
                {"name": "image", "prompt": "Docker image (e.g., python:3.11-slim):"},
                {"name": "host_port", "prompt": "Host port to expose:"},
                {"name": "container_port", "prompt": "Container port to map:"},
                {"name": "local_path", "prompt": "Local directory (absolute path):"},
                {"name": "container_path", "prompt": "Container mount point (e.g., /app):"},
                {"name": "cmd", "prompt": "Command to run (e.g., bash):"}
            ]
        },
        {
            "name": "Ping Host",
            "command": "ping ${host}",
            "cwd": ".",
            "description": "Ping a remote host",
            "parameters": [
                {
                    "name": "host",
                    "prompt": "Enter hostname or IP:"
                }
            ]
        }
    ]
    
    added_count = 0
    existing_names = [t.name for t in tasks]
    
    for task_data in example_tasks:
        if task_data["name"] not in existing_names:
            try:
                new_task = Task(**task_data)
                tasks.append(new_task)
                added_count += 1
            except Exception as e:
                print(f"Error creating task {task_data['name']}: {e}")
        else:
            print(f"Task '{task_data['name']}' already exists, skipping.")
            
    if added_count > 0:
        if save_tasks(tasks):
            print(f"Successfully added {added_count} example tasks.")
        else:
            print("Failed to save tasks.")
    else:
        print("No new example tasks were added.")

if __name__ == "__main__":
    add_examples()
