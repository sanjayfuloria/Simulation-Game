"""
Decision Theory Simulation Game
Entry point for Streamlit Cloud deployment
"""
import sys
from pathlib import Path

# Add app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir.parent))

# Import and run the main app
from app.main import main

if __name__ == "__main__":
    main()
