"""
Decision Theory Simulation Game
Entry point for Streamlit Cloud deployment
"""
import sys
import os
from pathlib import Path

# Get the directory containing this file
current_dir = Path(__file__).parent.resolve()

# Add the current directory to Python path
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Change to the directory containing the app
os.chdir(current_dir)

# Import and run the main app
from app.main import main

if __name__ == "__main__":
    main()
