import sys
from pathlib import Path

# Make the `jobradar` package (which lives in dags/) importable in tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dags"))
