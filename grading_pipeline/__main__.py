"""Allow running the package directly: ``python -m grading_pipeline``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
