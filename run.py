"""개발용 실행 / PyInstaller 진입점."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from dongwon_check.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
