#!/usr/bin/env python3
"""Initialize the database with TimescaleDB extensions"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import asyncpg


async def init_database():
    """Initialize TimescaleDB extensions and schema"""
    
    # Default connection parameters
    conn = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="myome",
        password="myome",
        database="myome",
    )
    
    try:
        print("Enabling TimescaleDB extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        
        print("Enabling uuid-ossp extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
        
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(init_database())
