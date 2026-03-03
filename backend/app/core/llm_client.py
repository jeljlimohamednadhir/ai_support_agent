"""
LLM Client - Groq Integration
Gère les appels au LLM (Groq avec Llama 3.3)
"""
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
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> str:
        """
        Génère une réponse du LLM
        
        Args:
            prompt: Le prompt utilisateur
            system_prompt: Instructions système (optionnel)
            temperature: Contrôle la créativité (0-1)
            max_tokens: Nombre max de tokens
            stream: Streaming de la réponse
        
        Returns:
            La réponse générée
        """
        try:
            messages = []
            
            # Prompt système par défaut en français
            if system_prompt is None:
                system_prompt = self._get_default_system_prompt()
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
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
                    return response.choices[0].message.content
            
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
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"❌ Erreur generate_with_context: {e}")
            raise
    
    def _get_default_system_prompt(self) -> str:
        """Prompt système par défaut"""
        return """Tu es un assistant IA expert en analyse de systèmes informatiques.
        
Tu aides les développeurs et les équipes support à:
- Comprendre le fonctionnement de leurs applications
- Diagnostiquer des problèmes techniques
- Analyser des logs et des erreurs
- Proposer des solutions

Réponds toujours en français de manière claire, concise et professionnelle.
Si tu ne sais pas quelque chose, dis-le honnêtement."""
    
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
