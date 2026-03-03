#!/usr/bin/env python3
"""
Script pour synchroniser les tickets Jira dans la base de connaissances
"""
import asyncio
import sys
from datetime import datetime
from typing import List, Dict, Any

from app.services.collector.orchestrator import JiraCollector
from app.services.knowledge.vector_service import VectorService
from app.services.knowledge.graph_service import GraphService


async def sync_jira_tickets():
    """Synchroniser tous les tickets Jira dans Qdrant et Neo4j"""
    
    print("="*80)
    print("SYNCHRONISATION DES TICKETS JIRA")
    print("="*80)
    
    # 1. Initialiser les services
    print("\n📦 Initialisation des services...")
    jira_collector = JiraCollector()
    vector_service = VectorService()
    graph_service = GraphService()
    
    # 2. Récupérer les tickets Jira
    print("\n🎫 Récupération des tickets Jira...")
    try:
        tickets = await jira_collector.collect_issues(
            jql="ORDER BY created DESC",
            max_results=100  # Ajustez selon vos besoins
        )
        print(f"   ✅ {len(tickets)} tickets récupérés")
    except Exception as e:
        print(f"   ❌ Erreur lors de la récupération: {e}")
        return
    
    if not tickets:
        print("   ⚠️  Aucun ticket trouvé")
        return
    
    # 3. Indexer dans Qdrant
    print(f"\n📊 Indexation dans Qdrant...")
    success_qdrant = 0
    for i, ticket in enumerate(tickets, 1):
        try:
            # Préparer le contenu pour RAG
            ticket_data = jira_collector.format_issue_for_rag(ticket)
            
            # Créer le texte complet pour l'embedding
            full_text = f"""
Ticket: {ticket_data['key']}
Résumé: {ticket_data['summary']}
Description: {ticket_data['description']}
Statut: {ticket_data['status']}
Priorité: {ticket_data['priority']}
Créé le: {ticket_data['created']}
"""
            
            # Indexer dans Qdrant
            await vector_service.upsert_code(
                code_id=f"jira_{ticket_data['key']}",
                code_text=full_text,
                metadata={
                    'type': 'jira_ticket',
                    'key': ticket_data['key'],
                    'summary': ticket_data['summary'],
                    'status': ticket_data['status'],
                    'priority': ticket_data['priority'],
                    'created': ticket_data['created'],
                    'updated': ticket_data['updated'],
                    'reporter': ticket_data['reporter'],
                    'assignee': ticket_data['assignee'],
                    'source': 'jira'
                },
                file_path=f"jira/tickets/{ticket_data['key']}"
            )
            success_qdrant += 1
            
            if i % 10 == 0:
                print(f"   📝 {i}/{len(tickets)} tickets indexés...")
                
        except Exception as e:
            print(f"   ⚠️  Erreur ticket {ticket.get('key', 'unknown')}: {e}")
    
    print(f"   ✅ {success_qdrant}/{len(tickets)} tickets indexés dans Qdrant")
    
    # 4. Créer les nœuds dans Neo4j
    if graph_service.is_available():
        print(f"\n🕸️  Création des nœuds Neo4j...")
        success_neo4j = 0
        for ticket in tickets:
            try:
                ticket_data = jira_collector.format_issue_for_rag(ticket)
                
                # Créer le nœud dans Neo4j
                await graph_service.add_code_node(
                    node_id=f"jira_{ticket_data['key']}",
                    node_type="jira_ticket",
                    name=ticket_data['key'],
                    content=f"{ticket_data['summary']} - {ticket_data['description'][:200]}",
                    metadata={
                        'status': ticket_data['status'],
                        'priority': ticket_data['priority'],
                        'created': ticket_data['created'],
                        'reporter': ticket_data['reporter']
                    }
                )
                success_neo4j += 1
                
            except Exception as e:
                print(f"   ⚠️  Erreur Neo4j pour {ticket.get('key', 'unknown')}: {e}")
        
        print(f"   ✅ {success_neo4j}/{len(tickets)} nœuds créés dans Neo4j")
    else:
        print("   ⚠️  Neo4j non disponible - nœuds non créés")
    
    # 5. Résumé
    print("\n" + "="*80)
    print("✅ SYNCHRONISATION TERMINÉE")
    print("="*80)
    print(f"Total tickets: {len(tickets)}")
    print(f"Indexés dans Qdrant: {success_qdrant}")
    if graph_service.is_available():
        print(f"Nœuds Neo4j créés: {success_neo4j}")
    print("\n💡 Vous pouvez maintenant poser des questions sur les tickets Jira au chatbot!")


if __name__ == "__main__":
    asyncio.run(sync_jira_tickets())
