#!/usr/bin/env python3
"""
Migration script to add attached_file column to chat_messages table
"""

import os
import sys
from sqlalchemy import text

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_lib.db import get_db
from app_lib.models import db

def migrate_chat_attachments():
    """Add attached_file column to chat_messages table if it doesn't exist"""
    try:
        # Check if column already exists
        result = db.engine.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'chat_messages' 
            AND column_name = 'attached_file'
        """)).fetchone()
        
        if result:
            print("✓ attached_file column already exists in chat_messages table")
            return
        
        # Add the column
        db.engine.execute(text("""
            ALTER TABLE chat_messages 
            ADD COLUMN attached_file VARCHAR(255)
        """))
        
        print("✓ Successfully added attached_file column to chat_messages table")
        
    except Exception as e:
        print(f"✗ Error adding attached_file column: {e}")
        raise

if __name__ == "__main__":
    print("Starting chat attachments migration...")
    migrate_chat_attachments()
    print("Migration completed successfully!")
