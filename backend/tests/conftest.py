import sys
import os

# Add the backend directory to sys.path so 'app' can be imported in tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
