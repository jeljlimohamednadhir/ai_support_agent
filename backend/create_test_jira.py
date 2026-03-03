#!/usr/bin/env python3
"""Créer des tickets Jira de test dans Qdrant pour tester le chatbot"""
import asyncio
from datetime import datetime, timedelta
from app.services.knowledge.vector_service import VectorService

async def create_test_jira_tickets():
    """Créer 10 tickets Jira de test"""
    
    print("="*80)
    print("CRÉATION DE TICKETS JIRA DE TEST")
    print("="*80)
    
    vector_service = VectorService()
    
    # Tickets de test
    test_tickets = [
        {
            'key': 'BRASIL-101',
            'summary': 'Erreur lors de l\'affectation sur CCL VC déjà occupé',
            'description': 'Lors de l\'affectation d\'un service, le système retourne une erreur car le CCL VC est déjà occupé. Il faut libérer le port.',
            'status': 'Résolu',
            'priority': 'Haute',
            'created': (datetime.now() - timedelta(days=2)).isoformat(),
            'reporter': 'tech.brasil@orange.com',
            'assignee': 'admin.brasil@orange.com'
        },
        {
            'key': 'BRASIL-102',
            'summary': 'Incohérence BRASIL terrain - carte manquante',
            'description': 'Des différences ont été détectées entre BRASIL et le terrain concernant des cartes manquantes sur certains DSLAM.',
            'status': 'En cours',
            'priority': 'Moyenne',
            'created': (datetime.now() - timedelta(days=5)).isoformat(),
            'reporter': 'supervision@orange.com',
            'assignee': 'tech.brasil@orange.com'
        },
        {
            'key': 'BRASIL-103',
            'summary': 'Problème sur compteurs de ressources logiques VP VLAN',
            'description': 'Les compteurs de ressources logiques VP VLAN sont incorrects, causant des échecs d\'affectation.',
            'status': 'Nouveau',
            'priority': 'Haute',
            'created': (datetime.now() - timedelta(days=1)).isoformat(),
            'reporter': 'noc@orange.com',
            'assignee': None
        },
        {
            'key': 'BRASIL-104',
            'summary': 'Suppression DSLAM impossible',
            'description': 'Impossible de supprimer un DSLAM car il est encore référencé dans des services actifs.',
            'status': 'Résolu',
            'priority': 'Basse',
            'created': (datetime.now() - timedelta(days=10)).isoformat(),
            'reporter': 'tech.brasil@orange.com',
            'assignee': 'dev.brasil@orange.com'
        },
        {
            'key': 'BRASIL-105',
            'summary': 'Erreur B4002 interne BRASIL lors de la réception de demande',
            'description': 'Erreur interne B4002 lors de la mise en service d\'un ND via Seba. Nécessite une analyse des logs.',
            'status': 'En cours',
            'priority': 'Critique',
            'created': datetime.now().isoformat(),
            'reporter': 'exploitation@orange.com',
            'assignee': 'dev.brasil@orange.com'
        },
        {
            'key': 'BRASIL-106',
            'summary': 'Port réseau sans service ni extrémité',
            'description': 'Certains ports réseau n\'ont ni service ni extrémité configurés, causant des incohérences.',
            'status': 'Nouveau',
            'priority': 'Moyenne',
            'created': (datetime.now() - timedelta(hours=12)).isoformat(),
            'reporter': 'audit@orange.com',
            'assignee': None
        },
        {
            'key': 'BRASIL-107',
            'summary': 'Caractères erronés dans t_ports.t_remarks',
            'description': 'Des caractères spéciaux incorrects sont présents dans le champ remarks de la table t_ports.',
            'status': 'Résolu',
            'priority': 'Basse',
            'created': (datetime.now() - timedelta(days=15)).isoformat(),
            'reporter': 'dba@orange.com',
            'assignee': 'dba@orange.com'
        },
        {
            'key': 'BRASIL-108',
            'summary': 'Mutation de liens impossible',
            'description': 'La mutation de liens entre deux DSLAM échoue avec un timeout.',
            'status': 'En cours',
            'priority': 'Haute',
            'created': (datetime.now() - timedelta(days=3)).isoformat(),
            'reporter': 'tech.brasil@orange.com',
            'assignee': 'tech.senior@orange.com'
        },
        {
            'key': 'BRASIL-109',
            'summary': 'Demandes ARTEMIS bloquées en attente réponse',
            'description': 'Plusieurs demandes ARTEMIS pour l\'affectation THD sont bloquées en attente de réponse.',
            'status': 'Nouveau',
            'priority': 'Critique',
            'created': (datetime.now() - timedelta(hours=6)).isoformat(),
            'reporter': 'artemis@orange.com',
            'assignee': None
        },
        {
            'key': 'BRASIL-110',
            'summary': 'Modification état TP impossible',
            'description': 'Impossible de modifier l\'état d\'un point de terminaison depuis l\'IHM BRASIL.',
            'status': 'En cours',
            'priority': 'Moyenne',
            'created': (datetime.now() - timedelta(days=7)).isoformat(),
            'reporter': 'tech.brasil@orange.com',
            'assignee': 'dev.brasil@orange.com'
        }
    ]
    
    print(f"\n📝 Création de {len(test_tickets)} tickets de test...\n")
    
    for ticket in test_tickets:
        # Créer le texte complet
        full_text = f"""
Ticket Jira: {ticket['key']}
Résumé: {ticket['summary']}
Description: {ticket['description']}
Statut: {ticket['status']}
Priorité: {ticket['priority']}
Créé le: {ticket['created']}
Rapporté par: {ticket['reporter']}
Assigné à: {ticket.get('assignee', 'Non assigné')}
"""
        
        # Indexer dans Qdrant
        await vector_service.add_code_snippet(
            code=full_text,
            snippet_id=f"jira_{ticket['key']}",
            metadata={
                'type': 'jira_ticket',
                'key': ticket['key'],
                'summary': ticket['summary'],
                'status': ticket['status'],
                'priority': ticket['priority'],
                'created': ticket['created'],
                'updated': ticket['created'],
                'reporter': ticket['reporter'],
                'assignee': ticket.get('assignee', ''),
                'source': 'jira',
                'file_path': f"jira/tickets/{ticket['key']}",
                'language': 'jira_ticket'
            }
        )
        
        print(f"✅ {ticket['key']}: {ticket['summary'][:60]}...")
    
    print(f"\n{'='*80}")
    print("✅ TICKETS CRÉÉS AVEC SUCCÈS")
    print("="*80)
    print("\n💡 Vous pouvez maintenant tester avec: 'cite-moi les 5 derniers jira'")

if __name__ == "__main__":
    asyncio.run(create_test_jira_tickets())
