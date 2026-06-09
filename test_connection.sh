#!/bin/bash
# Test connection to Serbian Data Portal API
# This script verifies the server can connect to data.gov.rs

set -e

echo "🔍 Testing Serbian Data Portal Connection"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the serbian-data-mcp directory"
    exit 1
fi

# Create a test script
cat > /tmp/test_connection.py << 'EOPYTHON'
#!/usr/bin/env python3
"""Test connection to Serbian Data Portal API."""

import sys
import asyncio
import httpx
from pathlib import Path

# Add src to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def test_connection():
    """Test basic API connectivity."""
    api_base = "https://data.gov.rs"

    print(f"📡 Testing connection to {api_base}...")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Test basic API endpoint
            response = await client.get(f"{api_base}/api/1/datasets/", params={"rows": 1})

            if response.status_code == 200:
                print("   ✅ API is reachable")
                data = response.json()

                # Check if we got valid data
                if "data" in data:
                    print(f"   ✅ Received valid data format")
                    print(f"   ℹ️  Total datasets available: {data.get('total', 'unknown')}")
                    return True
                else:
                    print("   ⚠️  Unexpected data format")
                    return False
            else:
                print(f"   ❌ HTTP error: {response.status_code}")
                return False

    except httpx.TimeoutException:
        print("   ❌ Connection timed out")
        return False
    except httpx.ConnectError:
        print("   ❌ Connection failed - check internet connection")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
EOPYTHON

# Run the test
python3 /tmp/test_connection.py
TEST_RESULT=$?

echo ""
if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ Connection test passed!"
    echo "   The server should be able to access Serbian open data."
else
    echo "❌ Connection test failed!"
    echo "   Please check your internet connection and try again."
    exit 1
fi

# Clean up
rm /tmp/test_connection.py

echo ""
echo "💡 Tip: You can also test specific datasets:"
echo "   python -c 'from serbian_data_mcp.api.client import UDataClient; import asyncio; asyncio.run(UDataClient().search_datasets(\"population\"))'"
