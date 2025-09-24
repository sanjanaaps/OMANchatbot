#!/usr/bin/env python3
"""
Test script to debug import issues
"""

import sys
import os

print("Current working directory:", os.getcwd())
print("Python path:")
for p in sys.path:
    print("  ", p)

print("\nChecking lib directory:")
print("lib exists:", os.path.exists('lib'))
print("lib/__init__.py exists:", os.path.exists('lib/__init__.py'))
print("lib/db.py exists:", os.path.exists('lib/db.py'))

print("\nContents of lib directory:")
if os.path.exists('lib'):
    for item in os.listdir('lib'):
        print("  ", item)

print("\nTrying to add current directory to path...")
sys.path.insert(0, os.getcwd())

print("\nTrying to import lib...")
try:
    import lib
    print("✓ lib imported successfully")
except Exception as e:
    print("✗ Error importing lib:", e)

print("\nTrying to import lib.db...")
try:
    import lib.db
    print("✓ lib.db imported successfully")
except Exception as e:
    print("✗ Error importing lib.db:", e)

print("\nTrying to import from lib.db...")
try:
    from lib.db import get_db
    print("✓ get_db imported successfully")
except Exception as e:
    print("✗ Error importing get_db:", e)
