#!/usr/bin/env python3
"""Test de la détection des questions de type liste"""
import re

questions = [
    "cite-moi les 5 derniers jira",
    "liste les 10 derniers tickets",
    "affiche les tickets Jira récents",
    "Quels sont les problèmes sur t_ports?",
    "montre-moi toutes les fiches FR",
]

list_patterns = [
    'cite', 'liste', 'derniers', 'dernières', 'récents', 'récentes',
    'tous les', 'toutes les', 'affiche', 'montre-moi'
]

print("=== TEST DÉTECTION QUESTIONS DE TYPE LISTE ===\n")

for question in questions:
    query_lower = question.lower()
    is_list = any(pattern in query_lower for pattern in list_patterns)
    
    # Extraire le nombre
    numbers = re.findall(r'\d+', question)
    limit = int(numbers[0]) if numbers else 5
    
    print(f"Question: {question}")
    print(f"  → Type liste: {is_list}")
    print(f"  → Limite: {limit}")
    print()
