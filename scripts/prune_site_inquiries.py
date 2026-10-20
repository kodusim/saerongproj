"""Daily retention cleanup for the new inquiry inbox only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.inquiries import connection

if __name__ == '__main__':
    with connection():
        pass
