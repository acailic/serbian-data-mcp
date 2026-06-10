#!/bin/bash
export PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]$ '
clear

echo '╔══════════════════════════════════════════════════════════════════════╗'
echo '║  🇷🇸  Serbian Data MCP Server — Live Demo                         ║'
echo '║  Access 3400+ open datasets from data.gov.rs                       ║'
echo '╚══════════════════════════════════════════════════════════════════════╝'
sleep 2

echo ''
echo '━━━ 1️⃣  Searching for air quality datasets ━━━'
echo '$ python demo_driver.py search vazduh'
sleep 0.8
.venv/bin/python demo_driver.py search 'vazduh'
sleep 3

echo '━━━ 2️⃣  Searching for population datasets ━━━'
echo '$ python demo_driver.py search stanovništvo'
sleep 0.8
.venv/bin/python demo_driver.py search 'stanovništvo'
sleep 3

echo '━━━ 3️⃣  Getting portal statistics ━━━'
echo '$ python demo_driver.py stats'
sleep 0.8
.venv/bin/python demo_driver.py stats
sleep 3

echo '━━━ 4️⃣  Browsing organizations ━━━'
echo '$ python demo_driver.py orgs'
sleep 0.8
.venv/bin/python demo_driver.py orgs
sleep 3

echo '━━━ 5️⃣  Getting dataset details ━━━'
echo '$ python demo_driver.py dataset 5fbf76d87de2727637f02829'
sleep 0.8
.venv/bin/python demo_driver.py dataset 5fbf76d87de2727637f02829
sleep 3

echo '━━━ 6️⃣  Downloading resource data ━━━'
echo '$ python demo_driver.py download 00164470-f369-3f24-aaf7-29ddb4e7d1c2'
sleep 0.8
.venv/bin/python demo_driver.py download 00164470-f369-3f24-aaf7-29ddb4e7d1c2
sleep 3

echo '━━━ 7️⃣  Profiling downloaded data ━━━'
echo '$ python demo_driver.py profile'
sleep 0.8
.venv/bin/python demo_driver.py profile
sleep 3

echo '━━━ 8️⃣  Filtering data ━━━'
echo '$ python demo_driver.py filter'
sleep 0.8
.venv/bin/python demo_driver.py filter
sleep 3

echo '━━━ 9️⃣  Creating a visualization ━━━'
echo '$ python demo_driver.py visualize'
sleep 0.8
.venv/bin/python demo_driver.py visualize
sleep 3

echo ''
echo '╔══════════════════════════════════════════════════════════════════════╗'
echo '║  ✅ Demo complete!                                                ║'
echo '║                                                                  ║'
echo '║  22 MCP tools  •  6 resources  •  8 prompts                       ║'
echo '║  292 tests passing  •  Caching  •  Full API coverage             ║'
echo '║                                                                  ║'
echo '║  https://github.com/acailic/serbian-data-mcp                    ║'
echo '╚══════════════════════════════════════════════════════════════════════╝'
sleep 2
