"""
Chatbot Service
Handles conversational AI logic — delègue l'intelligence à l'IntelligenceOrchestrator
"""
from typing import Optional, List, Dict
import uuid
from datetime import datetime
from app.schemas.chatbot import ChatMessage, ChatResponse
from app.core.llm_client import llm_client
from app.core.logging import get_logger
from app.services.orchestrator import intelligence_orchestrator

logger = get_logger(__name__)


class ChatbotService:
    """
    Service chatbot context-aware multi-tenant.
    Délègue la recherche de connaissance à l'IntelligenceOrchestrator
    qui route vers le bon pipeline selon le profil de l'application.
    """

    def __init__(self):
        self.llm = llm_client
        self.orchestrator = intelligence_orchestrator
        logger.info("[OK] ChatbotService initialisé avec IntelligenceOrchestrator")

    async def process_message(self, message: ChatMessage, db=None) -> ChatResponse:
        """
        Traite un message utilisateur via le pipeline adapté à l'application.

        Flux :
        1. Orchestrateur résout le profil app → pipeline adapté
        2. Pipeline recherche et score le contexte
        3. LLM génère la réponse avec le contexte structuré
        4. Réponse enrichie avec métadonnées trust
        """
        try:
            logger.info(f"[Chatbot] app={message.app_id}, message='{message.content[:60]}...'")

            conversation_id = message.conversation_id or str(uuid.uuid4())

            # 1. Déléguer à l'orchestrateur
            orch_result = await self.orchestrator.process(
                app_id=message.app_id,
                query=message.content,
                db=db,
                logs=message.logs,
                stack_trace=message.stack_trace,
                ticket_description=message.content,
                top_k=5,
            )

            # 2. Construire le contexte texte pour le LLM
            context_text = self.orchestrator.build_prompt_context(orch_result)

            # 3. Récupérer les garde-fous de réponse
            guard = self.orchestrator.get_response_guard(orch_result)
            llm_instructions = orch_result.get("llm_instructions", "")
            app_ctx = orch_result.get("app_context", {})

            # 4. Construire le prompt enrichi
            if context_text:
                system_prompt = (
                    f"Tu es un assistant expert de l'application {app_ctx.get('display_name', message.app_id)} "
                    f"(Orange). Tu aides les techniciens N3 à diagnostiquer et résoudre les incidents. "
                    f"Tu utilises exclusivement les informations de la base de connaissance fournie. "
                    f"Tu respectes scrupuleusement les niveaux de confiance indiqués."
                )
                full_prompt = f"""{context_text}

Question : {message.content}

{llm_instructions}"""
            else:
                # Aucun contexte disponible
                system_prompt = (
                    f"Tu es un assistant support pour l'application {app_ctx.get('display_name', message.app_id)}. "
                    f"Tu n'as pas de base de connaissance disponible pour cette requête."
                )
                full_prompt = (
                    f"{message.content}\n\n"
                    f"⚠️ Aucune connaissance structurée disponible. "
                    f"Réponds de façon générique en recommandant une investigation manuelle."
                )

            # 5. Appel LLM
            response_text = await self.llm.generate(
                prompt=full_prompt,
                system_prompt=system_prompt,
            )

            # 6. Extraire trust
            trust_score_obj = orch_result.get("trust_score")
            trust_score = trust_score_obj.score if trust_score_obj else 0
            trust_label = trust_score_obj.label.value if trust_score_obj else "insufficient"

            # 7. Construire les sources
            sources = orch_result.get("sources", [])

            # 8. Suggestions selon le mode
            suggestions = self._build_suggestions(orch_result.get("mode", ""), guard)

            logger.info(
                f"[Chatbot] Réponse générée — mode={orch_result.get('mode')}, "
                f"trust={trust_score}/100, sources={len(sources)}"
            )

            return ChatResponse(
                message=response_text,
                sources=sources,
                suggestions=suggestions,
                confidence=trust_score / 100,
                conversation_id=conversation_id,
                app_id=message.app_id,
                pipeline_mode=orch_result.get("mode"),
                trust_score=trust_score,
                trust_label=trust_label,
                diagnostic_available=guard.get("can_diagnose", False),
            )

        except Exception as e:
            logger.error(f"[Chatbot] Erreur dans process_message: {e}")
            raise

    def _build_suggestions(self, mode: str, guard: Dict) -> List[str]:
        """Suggestions contextuelles selon le mode et le trust"""
        if not guard.get("can_diagnose"):
            return [
                "Fournir les logs détaillés pour affiner l'analyse",
                "Préciser le code d'erreur exact",
                "Décrire les étapes qui ont précédé l'incident",
            ]
        if mode == "FR_RICH":
            return [
                "Afficher la procédure complète de résolution",
                "Quels sont les risques de cette intervention ?",
                "Existe-t-il des cas similaires résolus ?",
            ]
        if mode == "FR_WEAK":
            return [
                "Valider cette procédure avec l'équipe N3",
                "Consulter les tickets similaires",
                "Quelles vérifications préalables effectuer ?",
            ]
        # LOG_BASED
        return [
            "Analyser les logs détaillés",
            "Vérifier les dépendances du module",
            "Consulter l'historique des incidents similaires",
        ]

    async def get_conversation_history(self, conversation_id: str):
        """Retrieve conversation history"""
        # TODO: Implement avec DB
        pass

    async def save_feedback(self, conversation_id: str, message_id: str, feedback: dict):
        """Save user feedback for improvement"""
        # TODO: Implement — feedback alimente le TrustEngine
        passlogger = get_logger(__name__)


class ChatbotService:
    """AI Chatbot service with RAG capabilities"""
    
    def __init__(self):
        self.llm = llm_client
        # Connexion aux services de connaissances (singleton) - avec gestion du mode dégradé
        self.vector_service = get_vector_service()
        self.graph_service = get_graph_service()
        
        # Logger l'état des services
        rag_status = []
        if self.vector_service.is_available():
            rag_status.append("Qdrant")
        if self.graph_service.is_available():
            rag_status.append("Neo4j")
        
        if rag_status:
            logger.info(f"[OK] ChatbotService initialisé avec RAG ({', '.join(rag_status)})")
        else:
            logger.info("[OK] ChatbotService initialisé en mode basique (sans RAG)")
    
    async def _search_knowledge(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Rechercher dans le knowledge store (vecteurs + graphe)
        
        Args:
            query: Question de l'utilisateur
            top_k: Nombre de résultats à retourner
            
        Returns:
            Liste de contextes pertinents avec métadonnées enrichies
        """
        contexts = []
        
        try:
            # 1. Recherche vectorielle (similarité sémantique)
            vector_results = await self.vector_service.search_similar_code(
                query=query,
                top_k=top_k
            )
            
            # 2. Recherche dans le graphe Neo4j pour les corrélations
            graph_correlations = []
            if self.graph_service.is_available():
                try:
                    # Extraire entités de la requête (tables, tickets, etc.)
                    import re
                    entities = []
                    
                    # Extraire noms de tables
                    table_matches = re.findall(r'\b((?:qd|rip|ora|aml|ano|ref|file|lv|i)_\w+)\b', query.lower())
                    entities.extend([(name, 'table') for name in table_matches])
                    
                    # Extraire clés de tickets Jira  
                    ticket_matches = re.findall(r'\b(BRASIL-\d+)\b', query.upper())
                    entities.extend([(key, 'ticket') for key in ticket_matches])
                    
                    # Rechercher corrélations dans Neo4j
                    if entities:
                        for entity_name, entity_type in entities:
                            cypher_query = f"""
                            MATCH (n:CodeNode {{name: $entity_name}})
                            OPTIONAL MATCH (n)-[r]-(related:CodeNode)
                            RETURN n, r, related
                            LIMIT 10
                            """
                            
                            with self.graph_service.driver.session() as session:
                                result = session.run(cypher_query, entity_name=entity_name)
                                for record in result:
                                    if record["related"]:
                                        graph_correlations.append({
                                            'from_entity': entity_name,
                                            'from_type': entity_type,
                                            'to_entity': record["related"]["name"],
                                            'to_type': record["related"]["type"],
                                            'relationship': record["r"].type if record["r"] else "related"
                                        })
                
                    logger.info(f"[OK] Trouvé {len(graph_correlations)} corrélations dans Neo4j")
                except Exception as e:
                    logger.warning(f"Erreur recherche graphe: {e}")
            
            for result in vector_results:
                metadata = result.get('metadata', {})
                doc_type = metadata.get('type', 'code')
                
                # Construire le contexte selon le type de document
                if doc_type == 'database_table':
                    contexts.append({
                        'type': 'database',
                        'source': metadata.get('file_path', 'brasil_db.sql'),
                        'name': metadata.get('table_name', 'unknown'),
                        'language': 'sql',
                        'content': result.get('code', ''),
                        'relevance': 1.0 - (result.get('distance', 0) or 0),
                        'metadata': metadata
                    })
                elif doc_type == 'resolution_fiche':
                    contexts.append({
                        'type': 'fiche',
                        'source': metadata.get('filename', 'unknown.docx'),
                        'name': f"{metadata.get('fr_number', 'FR')} - {metadata.get('title', 'Sans titre')}",
                        'language': 'text',
                        'content': result.get('code', ''),
                        'relevance': 1.0 - (result.get('distance', 0) or 0),
                        'metadata': metadata
                    })
                elif doc_type == 'jira_ticket':
                    contexts.append({
                        'type': 'jira',
                        'source': 'Jira',
                        'name': f"{metadata.get('ticket_key', 'TICKET')} - {metadata.get('status', 'N/A')}",
                        'language': 'text',
                        'content': result.get('code', ''),
                        'relevance': 1.0 - (result.get('distance', 0) or 0),
                        'metadata': metadata
                    })
                else:
                    # Format ancien (code source)
                    contexts.append({
                        'type': 'code',
                        'source': metadata.get('file_path', 'unknown'),
                        'name': metadata.get('name', 'unknown'),
                        'language': metadata.get('language', 'unknown'),
                        'content': result.get('code', ''),
                        'relevance': 1.0 - (result.get('distance', 0) or 0),
                        'metadata': metadata
                    })
            
            # 3. Ajouter les corrélations du graphe aux contextes
            if graph_correlations:
                correlation_text = "\n🔗 CORRÉLATIONS IDENTIFIÉES:\n"
                for corr in graph_correlations:
                    correlation_text += f"- {corr['from_entity']} ({corr['from_type']}) → {corr['to_entity']} ({corr['to_type']}) via {corr['relationship']}\n"
                
                contexts.append({
                    'type': 'correlations',
                    'source': 'Neo4j Graph',
                    'name': 'Corrélations automatiques',
                    'language': 'text',
                    'content': correlation_text,
                    'relevance': 1.0,
                    'metadata': {'type': 'graph_correlations', 'correlations': graph_correlations}
                })
            
            # 2. TODO: Recherche dans le graphe de connaissances
            # graph_results = await self.graph_service.search_nodes(query)
            
            logger.info(f"[OK] {len(contexts)} contextes trouvés (tables: {sum(1 for c in contexts if c['type']=='database')}, fiches: {sum(1 for c in contexts if c['type']=='fiche')}, jira: {sum(1 for c in contexts if c['type']=='jira')}, corrélations: {sum(1 for c in contexts if c['type']=='correlations')})")
            
        except Exception as e:
            logger.warning(f"Erreur recherche knowledge: {e}")
        
        return contexts
    
    def _build_context_prompt(self, contexts: List[Dict]) -> str:
        """
        Construire le prompt de contexte à partir des résultats de recherche
        Sépare les tables de la base de données et les fiches de résolution
        """
        if not contexts:
            return ""
        
        # Séparer les contextes par type
        tables = []
        fiches = []
        jira_tickets = []
        correlations = []
        other = []
        
        for ctx in contexts:
            metadata = ctx.get('metadata', {})
            doc_type = metadata.get('type', 'code')
            
            if doc_type == 'database_table':
                tables.append(ctx)
            elif doc_type == 'resolution_fiche':
                fiches.append(ctx)
            elif doc_type == 'jira_ticket':
                jira_tickets.append(ctx)
            elif doc_type == 'graph_correlations':
                correlations.append(ctx)
            else:
                other.append(ctx)
        
        context_text = "\n\n=== CONTEXTE DE LA BASE DE CONNAISSANCES BRASIL ===\n"
        
        # 0. Corrélations automatiques (en premier pour guider l'analyse)
        if correlations:
            context_text += "\n🔗 CORRÉLATIONS AUTOMATIQUES DÉTECTÉES:\n"
            for i, ctx in enumerate(correlations, 1):
                context_text += f"{ctx['content']}\n"
        
        # 1. Tables de la base de données
        if tables:
            context_text += "\n📊 TABLES DE LA BASE DE DONNÉES:\n"
            for i, ctx in enumerate(tables, 1):
                metadata = ctx.get('metadata', {})
                table_name = metadata.get('table_name', 'unknown')
                column_count = metadata.get('column_count', 0)
                context_text += f"\n--- Table {i}: {table_name} ({column_count} colonnes) ---\n"
                context_text += f"{ctx['content'][:800]}\n"
        
        # 2. Fiches de résolution
        if fiches:
            context_text += "\n📋 FICHES DE RÉSOLUTION (PROCÉDURES):\n"
            for i, ctx in enumerate(fiches, 1):
                metadata = ctx.get('metadata', {})
                fr_number = metadata.get('fr_number', 'N/A')
                title = metadata.get('title', 'Sans titre')
                context_text += f"\n--- Fiche {i}: {fr_number} - {title} ---\n"
                context_text += f"{ctx['content'][:1500]}\n"
        
        # 3. Tickets Jira
        if jira_tickets:
            context_text += "\n🎫 TICKETS JIRA:\n"
            for i, ctx in enumerate(jira_tickets, 1):
                metadata = ctx.get('metadata', {})
                ticket_key = metadata.get('ticket_key', 'N/A')
                status = metadata.get('status', 'N/A')
                context_text += f"\n--- Ticket {i}: {ticket_key} ({status}) ---\n"
                context_text += f"{ctx['content'][:1200]}\n"
        
        # 4. Autres sources (ancien format)
        if other:
            context_text += "\n📁 AUTRES SOURCES:\n"
            for i, ctx in enumerate(other, 1):
                source = ctx.get('source', 'unknown')
                language = ctx.get('language', 'unknown')
                context_text += f"\n--- Fichier {i}: {source} ({language}) ---\n"
                context_text += f"```{language}\n{ctx['content']}\n```\n"
        
        context_text += "\n=== FIN DU CONTEXTE ===\n"
        return context_text
    
    async def _handle_list_query(self, query: str, limit: int = 5) -> str:
        """Gérer les questions de type liste (ex: "cite-moi les 5 derniers jira")"""
        
        # Détecter le type de liste demandée
        query_lower = query.lower()
        
        if 'jira' in query_lower or 'ticket' in query_lower:
            # Question sur les tickets Jira
            try:
                # Récupérer tous les tickets Jira de Qdrant
                from qdrant_client import models
                
                results = self.vector_service.client.scroll(
                    collection_name="code_knowledge",
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="type",  # Type directement dans payload
                                match=models.MatchValue(value="jira_ticket")
                            )
                        ]
                    ),
                    limit=100,
                    with_payload=True
                )
                
                tickets = []
                for point in results[0]:
                    payload = point.payload
                    tickets.append({
                        'key': payload.get('key', 'N/A'),
                        'summary': payload.get('summary', 'N/A'),
                        'status': payload.get('status', 'N/A'),
                        'priority': payload.get('priority', 'N/A'),
                        'created': payload.get('created', 'N/A'),
                        'updated': payload.get('updated', 'N/A')
                    })
                
                # Trier par date de création (plus récents en premier)
                tickets.sort(key=lambda x: x['created'], reverse=True)
                
                # Prendre les N premiers
                top_tickets = tickets[:limit]
                
                if not top_tickets:
                    return "❌ Aucun ticket Jira trouvé dans la base de connaissances. Utilisez l'endpoint `/api/v1/jira/sync` pour synchroniser les tickets."
                
                # Formater la réponse
                response = f"🎫 **Les {len(top_tickets)} derniers tickets Jira :**\n\n"
                for i, ticket in enumerate(top_tickets, 1):
                    response += f"**{i}. {ticket['key']}** - {ticket['summary']}\n"
                    response += f"   📅 Créé le: {ticket['created']}\n"
                    response += f"   📊 Statut: {ticket['status']}\n"
                    response += f"   🔥 Priorité: {ticket['priority']}\n\n"
                
                return response
                
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des tickets Jira: {e}")
                return f"❌ Erreur lors de la récupération des tickets Jira: {str(e)}"
        
        elif 'table' in query_lower or 'base' in query_lower:
            # Question sur les tables
            try:
                from qdrant_client import models
                
                results = self.vector_service.client.scroll(
                    collection_name="code_knowledge",
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="type",
                                match=models.MatchValue(value="database_table")
                            )
                        ]
                    ),
                    limit=limit,
                    with_payload=True
                )
                
                tables = []
                for point in results[0]:
                    metadata = point.payload.get('metadata', {})
                    tables.append({
                        'name': metadata.get('table_name', 'N/A'),
                        'description': metadata.get('description', 'N/A'),
                        'columns': metadata.get('column_count', 0)
                    })
                
                response = f"📊 **Les {len(tables)} tables de la base de données :**\n\n"
                for i, table in enumerate(tables, 1):
                    response += f"**{i}. {table['name']}**\n"
                    response += f"   📝 Description: {table['description']}\n"
                    response += f"   🔢 Nombre de colonnes: {table['columns']}\n\n"
                
                return response
                
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des tables: {e}")
                return f"❌ Erreur: {str(e)}"
        
        elif 'fiche' in query_lower or 'fr' in query_lower:
            # Question sur les fiches de résolution
            try:
                from qdrant_client import models
                
                results = self.vector_service.client.scroll(
                    collection_name="code_knowledge",
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="type",
                                match=models.MatchValue(value="resolution_fiche")
                            )
                        ]
                    ),
                    limit=100,
                    with_payload=True
                )
                
                fiches = []
                for point in results[0]:
                    payload = point.payload
                    fiches.append({
                        'number': payload.get('fr_number', 'N/A'),
                        'title': payload.get('title', 'N/A'),
                        'category': payload.get('category', 'N/A')
                    })
                
                response = f"📋 **Les {len(fiches)} fiches de résolution :**\n\n"
                for i, fiche in enumerate(fiches, 1):
                    response += f"**{i}. FR {fiche['number']}** - {fiche['title']}\n"
                    response += f"   📁 Catégorie: {fiche['category']}\n\n"
                
                return response
                
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des fiches: {e}")
                return f"❌ Erreur: {str(e)}"
        
        return None  # Pas une question de type liste

    async def process_message(self, message: ChatMessage) -> ChatResponse:
        """
        Process user message and generate response with RAG
        
        Steps:
        1. Understand user intent
        2. Search knowledge graph + vector store
        3. Retrieve relevant context
        4. Generate response with LLM + context
        5. Format response with sources
        """
        try:
            logger.info(f"Message recu: {message.content[:50]}...")
            
            # Générer conversation_id si nouveau
            conversation_id = message.conversation_id or str(uuid.uuid4())
            
            # Détecter si c'est une question de type "liste"
            query_lower = message.content.lower()
            list_patterns = [
                'cite', 'liste', 'derniers', 'dernières', 'récents', 'récentes',
                'tous les', 'toutes les', 'affiche', 'montre-moi'
            ]
            
            is_list_query = any(pattern in query_lower for pattern in list_patterns)
            
            if is_list_query:
                # Extraire le nombre demandé (par défaut 5)
                import re
                numbers = re.findall(r'\d+', message.content)
                limit = int(numbers[0]) if numbers else 5
                
                # Gérer la question de type liste
                list_response = await self._handle_list_query(message.content, limit)
                
                if list_response:
                    # Retourner directement la réponse formatée
                    return ChatResponse(
                        message=list_response,
                        sources=[],
                        suggestions=[],
                        confidence=1.0,
                        conversation_id=conversation_id
                    )
            
            # 1. Rechercher dans le knowledge store
            contexts = await self._search_knowledge(message.content, top_k=3)
            
            # 2. Construire le prompt enrichi
            context_prompt = self._build_context_prompt(contexts)
            
            # 3. Appel au LLM avec contexte
            if contexts:
                # Mode RAG: avec contexte
                enhanced_prompt = f"""Voici une question de l'utilisateur concernant l'application BRASIL.
            
{context_prompt}

Question: {message.content}

Instructions:
- Structure ta réponse en ÉTAPES NUMÉROTÉES si c'est une procédure de résolution
- Fais la CORRÉLATION SYSTÉMATIQUE entre les 3 sources :
  * 🎫 TICKETS JIRA : Incidents/problèmes rencontrés
  * 📋 FICHES DE RÉSOLUTION : Procédures documentées  
  * 📊 TABLES DB : Structure technique concernée
- ANALYSE LES LIENS :
  * Si un ticket Jira mentionne une table → explique le lien technique
  * Si une fiche fait référence à des tables → précise lesquelles et pourquoi
  * Si plusieurs tickets touchent la même table → identifie les patterns
- RECOMMANDATIONS PRÉVENTIVES basées sur l'historique Jira
- Cite systématiquement tes sources (numéros de FR, noms de tables, clés de tickets)
- Utilise des emojis pour clarifier: 📋 fiches, 📊 tables, 🎫 tickets, ⚠️ erreurs, 🔗 corrélations

Format de réponse :
1️⃣ **Analyse croisée** : Corrélations entre les 3 sources
2️⃣ **Contexte technique** : Tables/colonnes impliquées
3️⃣ **Historique incidents** : Tickets Jira similaires
4️⃣ **Procédure recommandée** : Étapes basées sur les fiches FR
5️⃣ **Prévention** : Comment éviter le problème (basé sur l'historique)
6️⃣ **Sources** : Références précises (🎫 tickets, 📋 FR, 📊 tables)

- Réponds en français de manière professionnelle et structurée"""
                
                response_text = await self.llm.generate(
                    prompt=enhanced_prompt,
                    system_prompt="Tu es un assistant expert de l'application BRASIL chez Orange. Tu aides les techniciens et développeurs à résoudre les problèmes en combinant la connaissance de la base de données PostgreSQL et les procédures documentées dans les fiches de résolution. Tu corrèles toujours les informations techniques (tables, colonnes) avec les étapes opérationnelles (fiches FR)."
                )
            else:
                # Mode standard: sans contexte
                response_text = await self.llm.generate(
                    prompt=message.content,
                    system_prompt=None
                )
            
            # 4. Extraire les sources (format dictionnaire pour le schema)
            sources = []
            for ctx in contexts:
                metadata = ctx.get('metadata', {})
                doc_type = metadata.get('type', 'code')
                
                if doc_type == 'database_table':
                    sources.append({
                        'file_path': metadata.get('file_path', 'brasil_db.sql'),
                        'name': f"📊 Table {metadata.get('table_name', 'unknown')}",
                        'type': 'database_table',
                        'relevance': ctx.get('relevance', 0.0)
                    })
                elif doc_type == 'resolution_fiche':
                    sources.append({
                        'file_path': metadata.get('file_path', 'FR/'),
                        'name': f"📋 {metadata.get('fr_number', 'FR')} - {metadata.get('title', 'Sans titre')[:50]}",
                        'type': 'resolution_fiche',
                        'relevance': ctx.get('relevance', 0.0)
                    })
                else:
                    sources.append({
                        'file_path': ctx.get('source', 'unknown'),
                        'name': ctx.get('name', 'unknown'),
                        'type': ctx.get('type', 'code'),
                        'relevance': ctx.get('relevance', 0.0)
                    })
            
            logger.info(f"Reponse generee pour conversation {conversation_id} (sources: {len(sources)})")
            
            return ChatResponse(
                message=response_text,
                sources=sources,
                suggestions=[
                    "Explique-moi cette fonction",
                    "Comment améliorer ce code ?",
                    "Quelles sont les dépendances ?"
                ],
                confidence=0.95 if contexts else 0.75,
                conversation_id=conversation_id
            )
            
        except Exception as e:
            logger.error(f"Erreur dans process_message: {e}")
            raise
    
    async def get_conversation_history(self, conversation_id: str):
        """Retrieve conversation history"""
        # TODO: Implement
        pass
    
    async def save_feedback(self, conversation_id: str, message_id: str, feedback: dict):
        """Save user feedback for improvement"""
        # TODO: Implement
        pass
