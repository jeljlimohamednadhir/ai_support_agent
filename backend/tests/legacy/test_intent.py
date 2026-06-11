import ast
with open('app/services/chatbot/chatbot_service.py', encoding='utf-8-sig') as f:
    src = f.read()
ast.parse(src)
print('Chatbot syntax OK')

from app.services.live_diagnostics.planners.diagnostic_planner import intent_from_message
tests = [
    ('Suppression equipement DSROB362 impossible', 'delete_equipment', 'DSROB362'),
    ('IHM bloquee DSM PARAM script bloque', 'fix_ihm_blocked', None),
    ('Erreur 1300 dans les logs', 'error_1300', None),
    ('TP bloque sur DSLA445', 'fix_blocked_tp', 'DSLA445'),
]
for msg, exp_intent, exp_entity in tests:
    intent, entity = intent_from_message(msg)
    ok = intent == exp_intent
    print(f'  [{"OK" if ok else "FAIL"}] "{msg[:45]}" -> {intent} / {entity}')
