import os
import sys
import tempfile

# Use a throw-away database and make the project importable BEFORE the app loads
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["GOOGLE_API_KEY"] = "test-key"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))