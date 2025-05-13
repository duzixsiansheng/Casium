#!/usr/bin/env python3
import os
import sys
import pytest

# Ensure project root is in PYTHONPATH for imports
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)
# If your code lives under 'src/', uncomment the next two lines:
# src_path = os.path.join(project_root, 'src')
# sys.path.insert(0, src_path)

if __name__ == '__main__':
    # Run pytest with desired arguments
    sys.exit(pytest.main([
        '--maxfail=1',        # Stop after first failure
        '--disable-warnings',  # Hide warnings
        '-q'                   # Quiet mode
    ]))
