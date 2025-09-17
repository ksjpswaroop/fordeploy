import os
import sys

def setup_project():
    """Create necessary directories for the project."""
    # Define the directories to create
    directories = [
        "app",
        "app/api",
        "app/models",
        "app/services",
        "app/db",
        "app/utils",
    ]
    
    # Get the base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create each directory if it doesn't exist
    for directory in directories:
        dir_path = os.path.join(base_dir, directory)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"Created directory: {dir_path}")
    
    # Create necessary __init__.py files
    for directory in directories:
        init_file = os.path.join(base_dir, directory, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write("# Package initialization\n")
            print(f"Created file: {init_file}")
    
    print("\nProject setup complete! You can now run the application with:")
    print("uvicorn app.main:app --reload")

if __name__ == "__main__":
    setup_project()
