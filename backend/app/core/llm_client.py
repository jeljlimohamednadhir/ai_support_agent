"""
LLM Client - Groq Integration
Gère les appels au LLM (Groq avec Llama 3.3)
"""
import re
from typing import Optional, List, Dict, Any
from groq import Groq
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Client unifié pour les appels LLM"""
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize le client selon le provider"""
        if self.provider == "groq":
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY non configurée dans .env")
            self.client = Groq(api_key=settings.GROQ_API_KEY)
            logger.info(f"[OK] Client Groq initialise avec modele: {settings.GROQ_MODEL}")
        else:
            raise ValueError(f"Provider {self.provider} non supporté")

    @staticmethod
    def _strip_thinking_tags(text: str) -> str:
        """Supprime les balises <think>...</think> des modèles reasoning (Qwen3, DeepSeek-R1...)."""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        text = re.sub(r"</?think>", "", text)
        return text.strip()

    @staticmethod
    def _extract_thinking(text: str) -> tuple[str, str]:
        """
        Sépare le contenu <think>...</think> de la réponse finale.
        Retourne (thinking_content, clean_response).
        """
        thinking_parts = re.findall(r"<think>(.*?)</think>", text, flags=re.DOTALL)
        thinking = "\n\n".join(t.strip() for t in thinking_parts) if thinking_parts else ""
        clean = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        clean = re.sub(r"</?think>", "", clean).strip()
        return thinking, clean

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        conversation_history: Optional[List[Dict]] = None,
        with_thinking: bool = False,
    ):
        """
        Génère une réponse du LLM.
        Si with_thinking=True, retourne (answer: str, thinking: str).
        Sinon retourne answer: str.
        """
        try:
            messages = []

            # Prompt système par défaut en français
            if system_prompt is None:
                system_prompt = self._get_default_system_prompt()

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Injecter l'historique (6 derniers échanges = 12 messages max)
            if conversation_history:
                messages.extend(conversation_history[-12:])

            messages.append({"role": "user", "content": prompt})
            
            # Paramètres
            temp = temperature if temperature is not None else settings.GROQ_TEMPERATURE
            max_tok = max_tokens if max_tokens is not None else settings.GROQ_MAX_TOKENS
            
            if self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tok,
                    stream=stream
                )
                
                if stream:
                    return response  # Retourne le stream
                else:
                    raw = response.choices[0].message.content or ""
                    # Groq SDK >= 0.9 exposes reasoning_content separately for reasoning models
                    # (Qwen3, DeepSeek-R1). Use it if available so the clean content is guaranteed.
                    msg_obj = response.choices[0].message
                    reasoning_content = getattr(msg_obj, "reasoning_content", None) or ""
                    if reasoning_content:
                        # Groq returned thinking separately — clean is already without <think>
                        thinking = reasoning_content.strip()
                        clean = self._strip_thinking_tags(raw)
                    else:
                        # Inline <think>...</think> — extract manually
                        thinking, clean = self._extract_thinking(raw)
                    if with_thinking:
                        return clean, thinking
                    return clean
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'appel LLM: {e}")
            raise
    
    async def generate_with_context(
        self,
        question: str,
        context: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Génère une réponse avec contexte RAG
        
        Args:
            question: Question de l'utilisateur
            context: Contexte récupéré (code, logs, docs)
            conversation_history: Historique de conversation
        
        Returns:
            Réponse générée avec le contexte
        """
        # Construire le prompt avec contexte
        system_prompt = self._build_rag_system_prompt()
        
        user_prompt = f"""Contexte pertinent récupéré de la base de connaissances:

```
{context}
```

Question de l'utilisateur:
{question}

Réponds à la question en te basant UNIQUEMENT sur le contexte fourni. Si le contexte ne contient pas l'information nécessaire, dis-le clairement."""
        
        # Ajouter l'historique si disponible
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if conversation_history:
            messages.extend(conversation_history[-5:])  # Garder les 5 derniers échanges
        
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            if self.provider == "groq":
                response = self.client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=messages,
                    temperature=settings.GROQ_TEMPERATURE,
                    max_tokens=settings.GROQ_MAX_TOKENS
                )
                raw = response.choices[0].message.content or ""
                _, clean = self._extract_thinking(raw)
                return clean
        except Exception as e:
            logger.error(f"❌ Erreur generate_with_context: {e}")
            raise
    
    def _get_default_system_prompt(self) -> str:
        """Prompt système N3 production — couvre les 4 familles d'intention."""
        return (
            "Tu es un assistant de support N3 expert pour les applications Orange Telecom (BRASIL).\n"
            "Tu travailles avec des ingénieurs support de niveau 2 et 3.\n"
            "\n"
            "## FAMILLES D'INTENTION ET COMPORTEMENT ATTENDU\n"
            "\n"
            "### 1. Diagnostic / Procédure FR (intent: investigate_*, check_status, get_procedure)\n"
            "- Cite UNIQUEMENT les procédures issues de la base de connaissances fournie.\n"
            "- Structure ta réponse : (1) Type d'incident détecté, (2) Systèmes impliqués,\n"
            "  (3) Étapes de diagnostic numérotées, (4) Recommandation d'escalade si nécessaire.\n"
            "- Ne fabrique JAMAIS de procédure absente du contexte.\n"
            "\n"
            "### 2. Analyse de patterns d'incidents (intent: analyze_behavior)\n"
            "- Appuie-toi sur les clusters et tickets similaires fournis.\n"
            "- Identifie les causes récurrentes et propose une piste de résolution.\n"
            "\n"
            "### 3. Logs / Debug / Infrastructure (intent: investigate_logs)\n"
            "- Indique les chemins de logs habituels pour l'application concernée.\n"
            "- Si des logs sont fournis dans le contexte, analyse-les immédiatement.\n"
            "- Précise quelles traces chercher en priorité selon le code d'erreur détecté.\n"
            "- Ne refuse pas cette question : c'est une demande opérationnelle légitime.\n"
            "\n"
            "### 4. Résumé / Message ticket (intent: summarize, write_ticket_message)\n"
            "- Utilise UNIQUEMENT l'historique de la conversation pour répondre.\n"
            "- Ne lance PAS de nouvelle recherche dans la base de connaissances.\n"
            "- Pour un résumé : (1) Problème signalé, (2) Diagnostic, (3) Actions recommandées.\n"
            "- Pour un message ticket : structure [Contexte] [Symptômes] [Diagnostic]\n"
            "  [Actions déjà effectuées] [Prochaines étapes]. Ton professionnel.\n"
            "\n"
            "## RÈGLES ANTI-HALLUCINATION (IMPÉRATIVES)\n"
            "- Ne cite JAMAIS une procédure, commande ou chemin de fichier que tu n'as pas reçu dans le contexte.\n"
            "- Ne mentionne JAMAIS un système informatique (ex: STARHUB, LIBRA, ORRAHD) si\n"
            "  ce système n'est pas explicitement cité dans le contexte fourni ou dans la conversation.\n"
            "- Ne génère JAMAIS d'identifiant de procédure (ex: BRASIL-PROC-XXXX, BRASIL-BATCH-XXXX)\n"
            "  qui n'existe pas dans la base de connaissances fournie.\n"
            "- Si la base de connaissances est vide ET que l'intention n'est pas contextuelle,\n"
            "  réponds : \"Je n'ai pas de procédure documentée pour ce cas. Je recommande l'escalade N3.\"\n"
            "- Indique toujours le niveau de confiance si la procédure est partielle.\n"
            "\n"
            "## FORMAT GÉNÉRAL\n"
            "- Réponds TOUJOURS en français.\n"
            "- Sois concis et factuel.\n"
            "- Utilise des listes numérotées pour les étapes.\n"
            "- Termine par une recommandation si l'incident n'est pas résolu.\n"
        )
    
    def _build_rag_system_prompt(self) -> str:
        """Prompt système pour RAG"""
        return """Tu es un assistant IA expert en analyse de code et de systèmes.

Tu as accès à une base de connaissances contenant:
- Le code source de l'application
- Les logs système
- La documentation
- Les schémas de base de données
- L'historique des incidents

INSTRUCTIONS IMPORTANTES:
1. Base tes réponses UNIQUEMENT sur le contexte fourni
2. Cite les sources (fichiers, fonctions, tables) dans tes réponses
3. Si le contexte est insuffisant, demande plus d'informations
4. Propose des actions concrètes et des commandes si pertinent
5. Utilise un langage technique mais accessible
6. Réponds toujours en français

Format de réponse recommandé:
- Réponse directe
- Explication technique
- Sources citées
- Actions suggérées (si applicable)"""


# Instance globale
llm_client = LLMClient()
