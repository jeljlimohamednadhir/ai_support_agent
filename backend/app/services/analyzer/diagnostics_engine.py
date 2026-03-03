"""
Diagnostics Engine
Analyse intelligente de problèmes avec IA
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json

from app.core.llm_client import LLMClient
from app.services.knowledge.graph_service import GraphService
from app.services.knowledge.vector_service import VectorService
from app.models.database import DiagnosticReport, SimilarIssue
from app.schemas.diagnostics import DiagnosticRequest
from sqlalchemy.orm import Session


class DiagnosticsEngine:
    """Moteur de diagnostic IA pour analyse de problèmes"""
    
    def __init__(self, db: Session):
        self.db = db
        self.llm_client = LLMClient()
        self.graph_service = GraphService()
        self.vector_service = VectorService()
    
    async def diagnose(self, request: DiagnosticRequest) -> Dict[str, Any]:
        """
        Diagnostic complet d'un problème
        
        Étapes:
        1. Analyser les symptômes
        2. Rechercher dans le knowledge graph
        3. Trouver issues similaires
        4. Identifier la cause racine
        5. Suggérer des solutions
        
        Args:
            request: Requête de diagnostic
        
        Returns:
            Rapport de diagnostic complet
        """
        diagnostic_id = str(uuid.uuid4())
        
        # 1. Recherche sémantique de contexte pertinent
        relevant_context = await self._search_relevant_context(
            request.issue_description,
            request.affected_component
        )
        
        # 2. Trouver issues similaires
        similar_issues = await self.find_similar_issues(request.issue_description)
        
        # 3. Analyser avec LLM
        analysis = await self._analyze_with_llm(
            request,
            relevant_context,
            similar_issues
        )
        
        # 4. Générer suggestions de solutions
        suggested_fixes = await self._generate_fix_suggestions(analysis, relevant_context)
        
        # 5. Sauvegarder le rapport
        report = DiagnosticReport(
            id=diagnostic_id,
            issue_description=request.issue_description,
            affected_component=request.affected_component,
            severity=analysis.get("severity", "medium"),
            status="open",
            root_cause=analysis.get("root_cause"),
            analysis=analysis,
            confidence=analysis.get("confidence", 0.7),
            error_logs=request.error_logs,
            related_code=relevant_context.get("code_sections", []),
            context=request.context,
            suggested_fixes=suggested_fixes,
            requester_id=request.context.get("requester_id") if request.context else None
        )
        
        self.db.add(report)
        
        # Sauvegarder les issues similaires
        for similar in similar_issues[:5]:  # Top 5
            similar_issue = SimilarIssue(
                diagnostic_id=diagnostic_id,
                reference_issue_id=similar.get("id"),
                similarity_score=similar.get("score"),
                description=similar.get("description"),
                resolution=similar.get("resolution")
            )
            self.db.add(similar_issue)
        
        self.db.commit()
        
        return {
            "diagnostic_id": diagnostic_id,
            "root_cause": analysis.get("root_cause"),
            "severity": analysis.get("severity"),
            "confidence": analysis.get("confidence"),
            "related_code": relevant_context.get("code_sections", []),
            "related_logs": relevant_context.get("log_entries", []),
            "suggested_fixes": suggested_fixes,
            "similar_issues": similar_issues[:3],
            "analysis_details": analysis
        }
    
    async def find_similar_issues(self, issue_description: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Trouve des issues similaires dans l'historique
        
        Utilise:
        - Recherche vectorielle (Qdrant)
        - Historique des diagnostics (PostgreSQL)
        - Tickets Jira (Neo4j)
        
        Args:
            issue_description: Description du problème
            limit: Nombre max de résultats
        
        Returns:
            Liste d'issues similaires avec scores
        """
        similar_issues = []
        
        # 1. Recherche vectorielle dans Qdrant
        vector_results = await self.vector_service.search_similar(
            issue_description,
            collection_name="diagnostics",
            limit=limit
        )
        
        for result in vector_results:
            similar_issues.append({
                "id": result.get("id"),
                "description": result.get("payload", {}).get("description"),
                "resolution": result.get("payload", {}).get("resolution"),
                "score": result.get("score"),
                "source": "history"
            })
        
        # 2. Recherche dans les diagnostics précédents
        previous_diagnostics = self.db.query(DiagnosticReport).filter(
            DiagnosticReport.status == "resolved"
        ).order_by(DiagnosticReport.resolved_at.desc()).limit(limit).all()
        
        for diag in previous_diagnostics:
            # Calculer similarité (simplifié)
            similarity = self._calculate_text_similarity(
                issue_description,
                diag.issue_description
            )
            
            if similarity > 0.6:  # Seuil de similarité
                similar_issues.append({
                    "id": diag.id,
                    "description": diag.issue_description,
                    "root_cause": diag.root_cause,
                    "resolution": diag.resolution_notes,
                    "score": similarity,
                    "source": "diagnostics"
                })
        
        # 3. Recherche dans Neo4j (tickets Jira similaires)
        jira_issues = await self._search_jira_issues(issue_description)
        similar_issues.extend(jira_issues)
        
        # Trier par score de similarité
        similar_issues.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return similar_issues[:limit]
    
    async def suggest_fixes(self, diagnostic_id: str) -> List[Dict[str, Any]]:
        """
        Génère des suggestions de solutions pour un diagnostic
        
        Args:
            diagnostic_id: ID du diagnostic
        
        Returns:
            Liste de solutions suggérées
        """
        report = self.db.query(DiagnosticReport).filter(
            DiagnosticReport.id == diagnostic_id
        ).first()
        
        if not report:
            raise ValueError(f"Diagnostic {diagnostic_id} not found")
        
        # Si déjà des suggestions, les retourner
        if report.suggested_fixes:
            return report.suggested_fixes
        
        # Sinon, générer nouvelles suggestions
        context = {
            "issue": report.issue_description,
            "root_cause": report.root_cause,
            "component": report.affected_component,
            "error_logs": report.error_logs
        }
        
        fixes = await self._generate_fix_suggestions(report.analysis, context)
        
        # Mettre à jour le rapport
        report.suggested_fixes = fixes
        self.db.commit()
        
        return fixes
    
    async def get_diagnostic_patterns(self) -> Dict[str, Any]:
        """
        Analyse les patterns d'erreurs récurrents
        
        Returns:
            Statistiques des patterns de problèmes
        """
        from sqlalchemy import func
        
        # Top composants affectés
        top_components = self.db.query(
            DiagnosticReport.affected_component,
            func.count(DiagnosticReport.id).label("count")
        ).group_by(
            DiagnosticReport.affected_component
        ).order_by(
            func.count(DiagnosticReport.id).desc()
        ).limit(10).all()
        
        # Distribution par sévérité
        severity_dist = self.db.query(
            DiagnosticReport.severity,
            func.count(DiagnosticReport.id).label("count")
        ).group_by(
            DiagnosticReport.severity
        ).all()
        
        # Taux de résolution
        total = self.db.query(func.count(DiagnosticReport.id)).scalar()
        resolved = self.db.query(func.count(DiagnosticReport.id)).filter(
            DiagnosticReport.status == "resolved"
        ).scalar()
        
        resolution_rate = (resolved / total * 100) if total > 0 else 0
        
        # Temps moyen de résolution
        avg_resolution_time = await self._calculate_avg_resolution_time()
        
        return {
            "total_diagnostics": total,
            "resolved": resolved,
            "resolution_rate": round(resolution_rate, 2),
            "avg_resolution_time_hours": avg_resolution_time,
            "top_affected_components": [
                {"component": comp, "count": count}
                for comp, count in top_components
            ],
            "severity_distribution": {
                sev: count for sev, count in severity_dist
            }
        }
    
    # Méthodes privées
    
    async def _search_relevant_context(
        self,
        issue_description: str,
        affected_component: Optional[str]
    ) -> Dict[str, Any]:
        """Recherche contexte pertinent (code, logs, docs)"""
        context = {
            "code_sections": [],
            "log_entries": [],
            "documentation": []
        }
        
        # Recherche dans le code via Qdrant
        code_results = await self.vector_service.search_similar(
            issue_description,
            collection_name="code",
            limit=5
        )
        
        context["code_sections"] = [
            {
                "file": r.get("payload", {}).get("file_path"),
                "content": r.get("payload", {}).get("content"),
                "score": r.get("score")
            }
            for r in code_results
        ]
        
        # Recherche dans les logs
        if affected_component:
            log_results = await self.vector_service.search_similar(
                f"{affected_component} {issue_description}",
                collection_name="logs",
                limit=5
            )
            
            context["log_entries"] = [
                {
                    "message": r.get("payload", {}).get("message"),
                    "timestamp": r.get("payload", {}).get("timestamp"),
                    "level": r.get("payload", {}).get("level")
                }
                for r in log_results
            ]
        
        # Recherche dans la documentation
        doc_results = await self.vector_service.search_similar(
            issue_description,
            collection_name="documentation",
            limit=3
        )
        
        context["documentation"] = [
            {
                "title": r.get("payload", {}).get("title"),
                "content": r.get("payload", {}).get("content"),
                "score": r.get("score")
            }
            for r in doc_results
        ]
        
        return context
    
    async def _analyze_with_llm(
        self,
        request: DiagnosticRequest,
        context: Dict[str, Any],
        similar_issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyse le problème avec le LLM"""
        prompt = f"""Tu es un expert en diagnostic de problèmes techniques.

**Problème signalé:**
{request.issue_description}

**Composant affecté:** {request.affected_component or 'Non spécifié'}

**Logs d'erreur:**
{json.dumps(request.error_logs, indent=2) if request.error_logs else 'Aucun'}

**Contexte du code:**
{json.dumps(context.get('code_sections', [])[:2], indent=2)}

**Issues similaires résolues:**
{json.dumps(similar_issues[:3], indent=2)}

**Analyse demandée:**
1. Identifie la cause racine probable
2. Évalue la sévérité (low, medium, high, critical)
3. Estime ta confiance (0.0 - 1.0)
4. Fournis une explication technique

Réponds en JSON avec: {{"root_cause": "...", "severity": "...", "confidence": 0.X, "explanation": "...", "technical_details": "..."}}
"""
        
        try:
            response = await self.llm_client.chat(prompt)
            analysis = json.loads(response)
        except:
            # Fallback si parsing JSON échoue
            analysis = {
                "root_cause": "Analyse en cours - nécessite investigation approfondie",
                "severity": "medium",
                "confidence": 0.5,
                "explanation": response if 'response' in locals() else "Erreur d'analyse"
            }
        
        return analysis
    
    async def _generate_fix_suggestions(
        self,
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Génère des suggestions de solutions"""
        prompt = f"""Basé sur cette analyse de problème, suggère 3-5 solutions concrètes.

**Cause racine:** {analysis.get('root_cause')}
**Sévérité:** {analysis.get('severity')}
**Contexte:** {json.dumps(context, indent=2)}

Fournis des solutions dans cet ordre:
1. Quick fix (solution rapide)
2. Proper fix (solution robuste)
3. Preventive measures (prévention)

Format JSON: [{{"type": "quick_fix", "description": "...", "steps": ["...", "..."], "estimated_time": "..."}}]
"""
        
        try:
            response = await self.llm_client.chat(prompt)
            suggestions = json.loads(response)
        except:
            # Suggestions par défaut
            suggestions = [
                {
                    "type": "investigation",
                    "description": "Analyser les logs détaillés du composant affecté",
                    "steps": [
                        "Consulter les logs",
                        "Identifier le moment exact de l'erreur",
                        "Vérifier l'état des dépendances"
                    ],
                    "estimated_time": "30 minutes"
                }
            ]
        
        return suggestions
    
    async def _search_jira_issues(self, issue_description: str) -> List[Dict[str, Any]]:
        """Recherche tickets Jira similaires dans Neo4j"""
        try:
            query = """
            MATCH (j:JiraTicket)
            WHERE j.summary CONTAINS $keyword OR j.description CONTAINS $keyword
            RETURN j.key as id, j.summary as description, j.resolution as resolution
            LIMIT 5
            """
            
            # Extraire mots-clés principaux (simplifié)
            keywords = issue_description.split()[:3]
            
            results = []
            for keyword in keywords:
                result = await self.graph_service.execute_query(query, {"keyword": keyword})
                results.extend(result)
            
            return [
                {
                    "id": r.get("id"),
                    "description": r.get("description"),
                    "resolution": r.get("resolution"),
                    "score": 0.7,  # Score fixe pour Jira
                    "source": "jira"
                }
                for r in results[:5]
            ]
        except:
            return []
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calcule similarité textuelle simple (Jaccard)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    async def _calculate_avg_resolution_time(self) -> float:
        """Calcule temps moyen de résolution en heures"""
        from sqlalchemy import func
        
        resolved_reports = self.db.query(DiagnosticReport).filter(
            DiagnosticReport.status == "resolved",
            DiagnosticReport.resolved_at.isnot(None)
        ).all()
        
        if not resolved_reports:
            return 0.0
        
        total_hours = sum(
            (report.resolved_at - report.created_at).total_seconds() / 3600
            for report in resolved_reports
        )
        
        return round(total_hours / len(resolved_reports), 2)
