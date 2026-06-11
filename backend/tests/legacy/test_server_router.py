"""Test server_router."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app.services.live_diagnostics.planners.server_router import (
    get_servers_for_intent, get_log_searches_for_intent, get_ssh_commands_for_intent, ServerRole
)

print("Servers for delete_equipment:", get_servers_for_intent("delete_equipment"))
print()
searches = get_log_searches_for_intent("delete_equipment", "DSROB362")
for s in searches:
    print(f"  [{s['server'].value}] {s['log_key']} -> {s['log_path']}")
    print(f"    patterns: {s['patterns']}")

print()
print("Servers for fix_ihm_blocked:", get_servers_for_intent("fix_ihm_blocked"))
searches = get_log_searches_for_intent("fix_ihm_blocked")
for s in searches:
    print(f"  [{s['server'].value}] {s['log_key']} -> {s['log_path']}")
    print(f"    patterns: {s['patterns']}")

print()
print("SSH commands for fix_ihm_blocked:", get_ssh_commands_for_intent("fix_ihm_blocked"))
print()
print("ALL OK")
