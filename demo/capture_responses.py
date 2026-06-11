"""Capture full responses for all 20 GOLD scenarios."""
import json, requests, uuid
from pathlib import Path

scenarios = json.loads(Path('demo/scenarios.json').read_text(encoding='utf-8'))
base = 'http://localhost:8000'
chat_path = '/api/v1/chatbot/chat'
results = []

for sc in scenarios:
    print(f"Running {sc['id']}...")
    payload = {
        'content': sc['question'],
        'conversation_id': str(uuid.uuid4()),
        'context': {}
    }
    try:
        r = requests.post(f'{base}{chat_path}', json=payload, timeout=600)
        r.raise_for_status()
        data = r.json()
        results.append({
            'id': sc['id'],
            'question': sc['question'],
            'category': sc['category'],
            'full_response': data.get('message', ''),
            'trust_score': data.get('trust_score'),
            'sources': data.get('sources', []),
            'suggestions': data.get('suggestions', []),
        })
    except Exception as e:
        results.append({
            'id': sc['id'],
            'question': sc['question'],
            'category': sc['category'],
            'full_response': f'ERROR: {e}',
            'trust_score': None,
            'sources': [],
            'suggestions': [],
        })

out = Path('demo/full_responses.json')
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\nDone - {len(results)} responses saved to {out}')
