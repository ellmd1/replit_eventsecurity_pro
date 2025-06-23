import os
import subprocess
import sys

def main():
    """
    Finds and runs all 'add_*.py' scripts in the current directory,
    excluding itself.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)
    
    print("Searching for data seeding scripts...")

    for filename in sorted(os.listdir(current_dir)):
        if filename.startswith("add_") and filename.endswith(".py") and filename != script_name:
            script_path = os.path.join(current_dir, filename)
            print(f"--- Running {filename} ---")
            try:
                # Using sys.executable to ensure the same python interpreter is used
                result = subprocess.run(
                    [sys.executable, script_path],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(result.stdout)
                if result.stderr:
                    print("Error:")
                    print(result.stderr)
            except subprocess.CalledProcessError as e:
                print(f"Error running {filename}:")
                print(e.stderr)
            except FileNotFoundError:
                print(f"Error: Could not find {filename}. Make sure it's in the same directory.")
            print("-" * (len(filename) + 12))
            print()

if __name__ == "__main__":
    main() 