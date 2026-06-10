#!/bin/bash
# Demo recording script for Serbian Data MCP Server
# This script creates an asciinema recording and converts it to MP4

set -e

DEMO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DEMO_DIR/.venv"
export PATH="$HOME/.local/bin:$PATH"

echo "🎬 Setting up demo recording..."

# Create the demo script
cat > "$DEMO_DIR/.demo_session.sh" << 'DEMO_EOF'
#!/bin/bash
export PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]$ '
clear

cat << 'BANNER'
╔══════════════════════════════════════════════════════════════════════╗
║  🇷🇸  Serbian Data MCP Server — Interactive Demo                   ║
║  Access 3400+ open datasets from data.gov.rs                         ║
╚══════════════════════════════════════════════════════════════════════╝
BANNER

sleep 1.5

echo "━━━ 1️⃣  Searching for population datasets ━━━"
echo "$ python demo_driver.py search stanovništvo"
sleep 0.5
cd /home/nistrator/Documents/github/amplifier/serbian-data-mcp
.venv/bin/python demo_driver.py search "stanovništvo"
echo ""
sleep 2

echo "━━━ 2️⃣  Getting dataset details ━━━"
echo "$ python demo_driver.py dataset 5fbf76d87de2727637f02829"
sleep 0.5
.venv/bin/python demo_driver.py dataset 5fbf76d87de2727637f02829
echo ""
sleep 2

echo "━━━ 3️⃣  Downloading resource data ━━━"
echo "$ python demo_driver.py download 00164470-f369-3f24-aaf7-29ddb4e7d1c2"
sleep 0.5
.venv/bin/python demo_driver.py download 00164470-f369-3f24-aaf7-29ddb4e7d1c2
echo ""
sleep 2

echo "━━━ 4️⃣  Data profiling — understanding the structure ━━━"
echo "$ python demo_driver.py profile"
sleep 0.5
.venv/bin/python demo_driver.py profile
echo ""
sleep 2

echo "━━━ 5️⃣  Filtering data ━━━"
echo "$ python demo_driver.py filter"
sleep 0.5
.venv/bin/python demo_driver.py filter
echo ""
sleep 2

echo "━━━ 6️⃣  Creating a visualization ━━━"
echo "$ python demo_driver.py visualize"
sleep 0.5
.venv/bin/python demo_driver.py visualize
echo ""
sleep 2

echo "━━━ 7️⃣  Browsing organizations ━━━"
echo "$ python demo_driver.py orgs"
sleep 0.5
.venv/bin/python demo_driver.py orgs
echo ""
sleep 2

echo "━━━ 8️⃣  Checking portal statistics ━━━"
echo "$ python demo_driver.py stats"
sleep 0.5
.venv/bin/python demo_driver.py stats
echo ""
sleep 2

echo ""
cat << 'OUTRO'
╔══════════════════════════════════════════════════════════════════════╗
║  ✅ Demo complete!                                                    ║
║                                                                      ║
║  The MCP server provides 22 tools, 6 resources, and 8 prompts       ║
║  for accessing 3400+ Serbian government datasets.                    ║
║                                                                      ║
║  Use with Claude Desktop, or any MCP-compatible client.               ║
║  Docs: https://github.com/acailic/serbian-data-mcp                  ║
╚══════════════════════════════════════════════════════════════════════╝
OUTRO

sleep 1
DEMO_EOF

chmod +x "$DEMO_DIR/.demo_session.sh"

# Record with asciinema
RECORDING="$DEMO_DIR/demo_recording.cast"
echo "🔴 Recording session to $RECORDING ..."
echo ""

asciinema rec -t "Serbian Data MCP Server Demo" -c "bash $DEMO_DIR/.demo_session.sh" "$RECORDING"

echo ""
echo "✅ Recording saved to: $RECORDING"
echo ""
