import http.server
import socketserver
from pathlib import Path
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess
import threading
import sys

# Configuration
PORT = 8000
DIRECTORY = "published"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if '.' not in self.path.split('/')[-1]:
            original_path = self.path
            self.path = f"{self.path}.html"
            
            if not Path(DIRECTORY + self.path).exists():
                self.path = original_path

        return super().do_GET()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

class SourceChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_build = 0
        self.build_cooldown = 2  # seconds

    def on_modified(self, event):
        # Skip if the change is in the published directory
        if DIRECTORY in event.src_path:
            return

        # Implement cooldown to prevent multiple rapid rebuilds
        current_time = time.time()
        if current_time - self.last_build < self.build_cooldown:
            return

        self.last_build = current_time
        print("\nChange detected in source files. Rebuilding...")
        try:
            # Use the same Python interpreter that's running this script
            subprocess.run([sys.executable, "scripts/build.py"], check=True)
            print("Rebuild complete. Ready for requests.")
        except subprocess.CalledProcessError as e:
            print(f"Error during rebuild: {e}")

def start_file_watcher():
    event_handler = SourceChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, "src", recursive=True)
    observer.start()
    return observer

def serve():
    # Ensure we're in the project root
    os.chdir(Path(__file__).parent.parent)
    
    # Check if published directory exists
    if not Path(DIRECTORY).exists():
        print(f"Error: {DIRECTORY} directory not found!")
        print("Please run the build script first: python scripts/build.py")
        return

    # Start file watcher in a separate thread
    observer = start_file_watcher()

    # Create server
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving files from /{DIRECTORY} at http://localhost:{PORT}")
        print("Watching for changes in /src directory...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            observer.stop()
            observer.join()
            httpd.shutdown()

if __name__ == "__main__":
    serve()