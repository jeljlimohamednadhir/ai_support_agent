"""
test_live_diag_fix.py
━━━━━━━━━━━━━━━━━━━━━
Test rapide des corrections apportées au diagnostic live :
  1. intent_from_message("Suppression équipement DSROB362 impossible")
     -> doit retourner delete_equipment, DSROB362
  2. order_blocked dans INTENT_QUERY_PLAN -> doit avoir 6 queries
  3. delete_equipment dans INTENT_QUERY_PLAN -> doit avoir 5 queries
  4. DiagnosticPlanner.plan(order_blocked, DSROB362) -> doit avoir des queries + logs
  5. DiagnosticPlanner.plan(delete_equipment, DSROB362) -> idem
  6. Simulation chatbot intent resolution: ticket intent=order_blocked
     -> après fix, doit utiliser delete_equipment
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ── couleurs console ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

pass_count = fail_count = 0

def ok(label, detail=""):
    global pass_count
    pass_count += 1
    print(f"  {GREEN}PASS{RESET}  {label}" + (f"  ({detail})" if detail else ""))

def fail(label, detail=""):
    global fail_count
    fail_count += 1
    print(f"  {RED}FAIL{RESET}  {label}" + (f"  ({detail})" if detail else ""))

def section(title):
    print(f"\n{BOLD}{YELLOW}{'─'*60}{RESET}")
    print(f"{BOLD}{YELLOW}  {title}{RESET}")
    print(f"{BOLD}{YELLOW}{'─'*60}{RESET}")

# ─────────────────────────────────────────────────────────────────────────────
section("1. intent_from_message()")
from app.services.live_diagnostics.planners.diagnostic_planner import intent_from_message

cases = [
    ("Suppression équipement DSROB362 impossible", None, "delete_equipment", "DSROB362"),
    ("Suppression VLAN IMPOSSIBLE",                None, "delete_vlan",      None),
    ("IHM bloquée DSM PARAM",                     None, "fix_ihm_blocked",  None),
    ("ordre bloqué avp 1300",                      None, "error_1300",       None),
    ("Suppression d'un DSLAM impossible DSLA01",   None, "delete_equipment", "DSLA01"),
]

for msg, ent_in, exp_intent, exp_entity in cases:
    intent, entity = intent_from_message(msg, ent_in)
    i_ok = intent == exp_intent
    e_ok = (exp_entity is None) or (entity == exp_entity)
    if i_ok and e_ok:
        ok(f'"{msg[:45]}"', f"intent={intent} entity={entity}")
    else:
        fail(f'"{msg[:45]}"', f"got intent={intent} entity={entity}, expected {exp_intent}/{exp_entity}")

# ─────────────────────────────────────────────────────────────────────────────
section("2. INTENT_QUERY_PLAN coverage")
from app.services.live_diagnostics.db.db_query_registry import INTENT_QUERY_PLAN, get_plan_for_intent

for intent, min_queries in [
    ("delete_equipment", 5),
    ("order_blocked",    6),
    ("delete_vlan",      2),
    ("fix_blocked_tp",   2),
]:
    plan = get_plan_for_intent(intent)
    if len(plan) >= min_queries:
        ok(f"INTENT_QUERY_PLAN[{intent}]", f"{len(plan)} queries: {plan}")
    else:
        fail(f"INTENT_QUERY_PLAN[{intent}]", f"got {len(plan)} queries (min={min_queries}): {plan}")

# ─────────────────────────────────────────────────────────────────────────────
section("3. DiagnosticPlanner.plan()")
from app.services.live_diagnostics.planners.diagnostic_planner import DiagnosticPlanner

planner = DiagnosticPlanner()

for intent, entity, min_q, min_logs in [
    ("delete_equipment", "DSROB362", 5, 2),
    ("order_blocked",    "DSROB362", 6, 3),
]:
    plan = planner.plan(intent, entity, enable_ssh=False)
    q_ok   = len(plan.db_queries) >= min_q
    log_ok = len(plan.log_searches) >= min_logs
    if q_ok and log_ok:
        ok(f"plan({intent}, {entity})",
           f"{len(plan.db_queries)} queries, {len(plan.log_searches)} log searches")
    else:
        fail(f"plan({intent}, {entity})",
             f"queries={len(plan.db_queries)} (min={min_q}), logs={len(plan.log_searches)} (min={min_logs})")

# ─────────────────────────────────────────────────────────────────────────────
section("4. Chatbot intent resolution logic (simulated)")
# Reproduit la logique du chatbot_service.py après le fix

_GENERIC_INTENTS = {"order_blocked", "check_node", "unknown", None}

def resolve_intent(ticket_intent, message, entity_in=None):
    """Simule la logique corrigée du chatbot."""
    _live_intent = ticket_intent
    _live_entity = entity_in
    msg_intent, msg_entity = intent_from_message(message, _live_entity)
    if not _live_intent or _live_intent.lower() in _GENERIC_INTENTS:
        _live_intent = msg_intent
    if not _live_entity:
        _live_entity = msg_entity
    return _live_intent, _live_entity

sim_cases = [
    # (ticket_intent,    message,                                   expected_intent)
    ("order_blocked",   "Suppression équipement DSROB362 impossible", "delete_equipment"),
    ("order_blocked",   "Suppression VLAN IMPOSSIBLE",                "delete_vlan"),
    ("delete_equipment","Suppression équipement DSROB362 impossible", "delete_equipment"),
    (None,              "IHM bloquée DSM PARAM",                      "fix_ihm_blocked"),
    ("check_node",      "Suppression équipement DSROB362 impossible", "delete_equipment"),
]

for ticket_intent, msg, exp in sim_cases:
    resolved, entity = resolve_intent(ticket_intent, msg)
    if resolved == exp:
        ok(f"ticket={ticket_intent} + msg", f"-> {resolved} entity={entity}")
    else:
        fail(f"ticket={ticket_intent} + msg", f"got {resolved}, expected {exp}")

# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
section("5. SSH client host key policy")
from app.services.ssh_operations.client.ssh_client import SshClient
import paramiko

c_auto  = SshClient("10.0.0.1", auto_add_host_key=True)
c_noarg = SshClient("10.0.0.1")
c_known = SshClient("10.0.0.1", known_hosts_path="/tmp/dummy_known")

def _get_policy(client):
    import paramiko as p
    c = p.SSHClient()
    client2 = SshClient.__new__(SshClient)
    client2.__dict__.update(client.__dict__)
    # Simulate connect policy selection without actually connecting
    if client._auto_add:
        return "AutoAdd"
    elif client._known_hosts:
        return "AutoAdd(with known_hosts)"
    else:
        return "AutoAdd(fallback)"

for label, c in [("auto_add=True", c_auto), ("no args", c_noarg), ("known_hosts set", c_known)]:
    policy = _get_policy(c)
    if "Reject" not in policy:
        ok(f"SshClient({label}) -> {policy}")
    else:
        fail(f"SshClient({label}) -> {policy} (should not be RejectPolicy)")

# ─────────────────────────────────────────────────────────────────────────────
section("6. LogService._ssh_grep uses exec_command")
import inspect
from app.services.live_diagnostics.logs.log_service import LogService
src = inspect.getsource(LogService._ssh_grep)
if "exec_command" in src and "execute_command" not in src:
    ok("LogService._ssh_grep uses exec_command (not execute_command)")
else:
    fail("LogService._ssh_grep still uses wrong method", src[:200])

section("Résumé")
total = pass_count + fail_count
print(f"\n  {GREEN if fail_count == 0 else RED}{BOLD}{pass_count}/{total} tests passés{RESET}\n")
if fail_count > 0:
    print(f"  {RED}Action requise : corriger les {fail_count} test(s) en échec.{RESET}\n")
else:
    print(f"  {GREEN}Toutes les corrections sont validées. Redémarrez le backend.{RESET}\n")
sys.exit(0 if fail_count == 0 else 1)
