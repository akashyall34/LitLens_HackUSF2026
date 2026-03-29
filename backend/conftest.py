"""Pytest configuration — prevents real DB/Redis connections during CI."""
import os
import sys

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
