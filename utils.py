"""
Utility functions shared across the Likable project.
"""

import os


def load_file(path):
    """Load the contents of a file and return as string.

    Args:
        path: Path to the file to load

    Returns:
        str: File contents, or empty string if path is None or file doesn't exist
    """
    if path is None:
        return ""

    # Check if file exists first
    if not os.path.exists(path):
        return ""

    # path is a string like "subdir/example.py"
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""
