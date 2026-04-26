import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.experiments.analysis import analyze

if __name__ == "__main__":
    analyze()
