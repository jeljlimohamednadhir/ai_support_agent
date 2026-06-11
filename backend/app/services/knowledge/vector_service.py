"""
Service de gestion du stockage vectoriel avec Qdrant
"""
import os
import ssl

# Forcer le mode offline AVANT tout import HuggingFace/transformers
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
import logging
from typing import List, Dict, Any, Optional
# NOTE: qdrant_client (~25s sur OneDrive) et SentenceTransformer sont importés LAZILY
# dans __init__ / embedding_model pour ne pas bloquer le démarrage.
import uuid

# Configuration SSL depuis variables d'environnement
DISABLE_SSL_VERIFY = os.getenv('DISABLE_SSL_VERIFY', 'true').lower() == 'true'
EMBEDDING_CACHE_DIR = os.getenv('EMBEDDING_CACHE_DIR', './data/models')

if DISABLE_SSL_VERIFY:
    # Désactiver la vérification SSL pour HuggingFace (problème de certificat corporate)
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    ssl._create_default_https_context = ssl._create_unverified_context
    logging.info("[SSL] Vérification SSL désactivée (DISABLE_SSL_VERIFY=true)")

logger = logging.getLogger(__name__)


class VectorService:
    """Service pour gérer les embeddings et la recherche vectorielle avec Qdrant (singleton)"""
    
    # Instances singleton au niveau de la classe
    _instance = None
    _client = None
    _embedding_model = None
    _initialized = False
    
    def __new__(cls, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        """Implémenter le singleton"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        """
        Initialiser le service vectoriel avec Qdrant
        
        Args:
            qdrant_host: Host de Qdrant
            qdrant_port: Port de Qdrant
        """
        # Éviter la réinitialisation si déjà fait
        if VectorService._initialized:
            return
        
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = "code_knowledge"  # Collection pour tout le contenu
        self._available = False
        
        # Initialiser Qdrant client (une seule fois) - avec gestion d'erreur
        if VectorService._client is None:
            try:
                # Import lazy de qdrant_client (~25s sur OneDrive si fait au niveau module)
                from qdrant_client import QdrantClient
                from qdrant_client.models import Distance, VectorParams

                logger.info(f"Initialisation Qdrant sur {qdrant_host}:{qdrant_port}...")
                VectorService._client = QdrantClient(host=qdrant_host, port=qdrant_port, timeout=2)
                
                # Créer la collection pour le code si elle n'existe pas
                try:
                    VectorService._client.get_collection("code_knowledge")
                except:
                    VectorService._client.create_collection(
                        collection_name="code_knowledge",
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                    )
                    logger.info("[OK] Collection 'code_knowledge' créée dans Qdrant")
                
                self._available = True
                logger.info(f"[OK] VectorService initialisé avec Qdrant ({qdrant_host}:{qdrant_port})")
            except Exception as e:
                logger.warning(f"[WARN] Qdrant non disponible ({qdrant_host}:{qdrant_port}): {e}")
                logger.warning("[WARN] VectorService fonctionnera en mode dégradé (sans recherche vectorielle)")
                self._available = False
        
        VectorService._initialized = True
    
    def is_available(self) -> bool:
        """Vérifier si le service Qdrant est disponible"""
        return getattr(self, '_available', False)
    
    @property
    def client(self):
        """Accès au client Qdrant"""
        return VectorService._client
    
    @property
    def embedding_model(self):
        """Chargement lazy du modèle d'embeddings avec fallback"""
        if VectorService._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Chargement du modèle d'embeddings (première utilisation)...")
                import glob as _glob, os.path as osp

                # Tentative 1: Chemin snapshot HuggingFace Hub (format actuel)
                try:
                    hf_hub_base = osp.expanduser(
                        '~/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2'
                    )
                    snapshots = _glob.glob(osp.join(hf_hub_base, 'snapshots', '*'))
                    if snapshots:
                        model_path = snapshots[0]
                        VectorService._embedding_model = SentenceTransformer(model_path, device='cpu')
                        logger.info(f"[OK] Modèle chargé depuis HuggingFace Hub snapshot: {model_path}")
                        return VectorService._embedding_model
                    else:
                        raise FileNotFoundError(f"Aucun snapshot trouvé dans {hf_hub_base}")
                except Exception as e:
                    logger.warning(f"[WARN] Snapshot HuggingFace Hub introuvable: {e}")

                # Tentative 2: Nom court avec offline forcé
                try:
                    os.environ['HF_HUB_OFFLINE'] = '1'
                    os.environ['TRANSFORMERS_OFFLINE'] = '1'
                    VectorService._embedding_model = SentenceTransformer(
                        'paraphrase-multilingual-MiniLM-L12-v2', device='cpu'
                    )
                    logger.info("[OK] Modèle chargé via SentenceTransformer offline")
                    return VectorService._embedding_model
                except Exception as e2:
                    logger.warning(f"[WARN] SentenceTransformer offline échoué: {e2}")

                # Tentative 3: Ancien format cache torch
                try:
                    model_path = osp.expanduser('~/.cache/torch/sentence_transformers/sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2')
                    if osp.exists(model_path):
                        VectorService._embedding_model = SentenceTransformer(model_path, device='cpu')
                        logger.info(f"[OK] Modèle chargé depuis cache torch: {model_path}")
                        return VectorService._embedding_model
                except Exception as e3:
                    logger.warning(f"[WARN] Fallback cache torch échoué: {e3}")

                    # Dernier recours: TF-IDF
                    logger.warning("[WARN] Mode dégradé: utilisation TF-IDF au lieu de embeddings neuronaux")
                    from sklearn.feature_extraction.text import TfidfVectorizer
                    
                    class TfidfEmbedder:
                        """Embedder TF-IDF simple pour fallback"""
                        def __init__(self):
                            self.vectorizer = TfidfVectorizer(max_features=384, ngram_range=(1,2))
                            self._fitted = False
                            
                        def encode(self, texts, convert_to_tensor=False):
                            """Encoder textes en vecteurs TF-IDF"""
                            if isinstance(texts, str):
                                texts = [texts]
                            if not self._fitted:
                                # Fit sur corpus minimal
                                corpus = texts + ["code python", "function definition", "class implementation"]
                                self.vectorizer.fit(corpus)
                                self._fitted = True
                            vectors = self.vectorizer.transform(texts).toarray()
                            return vectors[0] if len(texts) == 1 else vectors
                    
                    VectorService._embedding_model = TfidfEmbedder()
                    logger.warning("[WARN] Embeddings neuronaux indisponibles, TF-IDF activé (précision réduite)")
                    
            except Exception as e:
                logger.error(f"[ERREUR] Impossible de charger un modèle d'embeddings: {e}")
                logger.error("[ERREUR] VectorService ne pourra pas générer d'embeddings")
                raise RuntimeError("Aucun modèle d'embeddings disponible")
                
        return VectorService._embedding_model
    
    
    async def add_code_snippet(
        self,
        code: str,
        metadata: Dict[str, Any],
        snippet_id: str
    ) -> bool:
        """
        Ajouter un snippet de code avec ses embeddings
        
        Args:
            code: Code source à indexer
            metadata: Métadonnées (file_path, language, etc.)
            snippet_id: ID unique du snippet
            
        Returns:
            True si succès
        """
        try:
            # Générer l'embedding
            embedding = self.embedding_model.encode(code).tolist()
            
            # Import lazy
            from qdrant_client.models import PointStruct

            # Créer le point pour Qdrant
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "code": code,
                    "snippet_id": snippet_id,
                    **metadata
                }
            )
            
            # Ajouter à Qdrant
            self.client.upsert(
                collection_name="code_knowledge",
                points=[point]
            )
            
            logger.info(f"[OK] Snippet {snippet_id} ajouté à Qdrant ({metadata.get('language', 'unknown')})")
            return True
            
        except Exception as e:
            logger.error(f"[ERREUR] add_code_snippet: {e}")
            return False
    
    
    async def search_similar_code(
        self,
        query: str,
        top_k: int = 5,
        language_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Rechercher du code similaire par recherche vectorielle HYBRIDE
        Combine recherche sémantique + recherche exacte par nom de table
        
        Args:
            query: Question ou code à rechercher
            top_k: Nombre de résultats
            language_filter: Filtrer par langage (optionnel)
            
        Returns:
            Liste de résultats avec code, metadata et score
        """
        # Vérifier si Qdrant est disponible
        if not self.is_available():
            logger.debug("Qdrant non disponible - recherche vectorielle désactivée")
            return []
        
        try:
            # ÉTAPE 1: Recherche exacte par nom de table si la requête contient un mot comme "table"
            exact_matches = []
            query_lower = query.lower()
            
            # Extraire les noms de tables potentiels de la requête
            # Pattern: "table XXX" ou "XXX ?" ou juste un nom de table
            import re
            table_patterns = [
                r'table\s+(\w+)',  # "table qd_anomalie" ou "table t_ports"
                r'(\w+)\s*\?',      # "qd_anomalie?"
                r'\b((?:t|qd|rip|ora|aml|ano|ref|file|lv|i|d_|lst|encoding)_\w+)\b'  # Préfixes connus (t_ = BRASIL)
            ]

            # Mapping français → anglais pour les mots-clés courants BRASIL
            _FR_TO_EN_TABLE_KEYWORDS = {
                "equipement": "equipment",
                "equipements": "equipments",
                "équipement": "equipment",
                "équipements": "equipments",
                "port": "port",
                "ports": "ports",
                "carte": "card",
                "cartes": "cards",
                "slot": "slot",
                "slots": "slots",
                "noeud": "node",
                "noeuds": "nodes",
                "operateur": "operator",
                "opérateur": "operator",
                "operateurs": "operators",
                "opérateurs": "operators",
                "role": "role",
                "roles": "roles",
                "prestation": "prestation",
                "prestations": "prestations",
                "serveur": "server",
                "serveurs": "servers",
                "modele": "model",
                "modeles": "models",
                "modèle": "model",
                "modèles": "models",
                "logement": "shelf",
                "logements": "shelfs",
                "tiroir": "shelf",
                "profil": "profile",
                "profils": "profiles",
                "ressource": "resource",
                "ressources": "resources",
                "media": "media",
                "lien": "link",
                "liens": "links",
                "brassage": "stripe",
                "brassages": "stripes",
                "fabricant": "manufacturer",
                "fabricants": "manufacturers",
                "technologie": "technology",
                "technologies": "technology",
                "mutation": "mutation",
                "mutations": "mutations",
                "remplacement": "swap",
                "remplacements": "swaps",
                "distribution": "distributor",
                "distributeurs": "distributors",
                "dslam": "dslam",
                "vlan": "vlan",
                "acces": "access",
                "accès": "access",
            }
            
            potential_table_names = set()
            for pattern in table_patterns:
                matches = re.findall(pattern, query_lower)
                potential_table_names.update(matches)

            # Recherche fuzzy: extraire les mots-clés de la requête et chercher
            # les tables dont le nom contient ces mots-clés (FR→EN inclus)
            # Blocklist: mots trop génériques qui matchent n'importe quelle table
            _FUZZY_STOPWORDS = {
                "date", "dates", "type", "types", "code", "codes", "nom", "noms",
                "etat", "etats", "état", "états", "statut", "status", "label",
                "liste", "listes", "list", "data", "info", "infos", "ligne",
                "lignes", "valeur", "valeurs", "champ", "champs", "base",
                "table", "tables", "numero", "numéro", "numero", "version",
                "mode", "modes", "flag", "flags", "actif", "active",
                "heure", "heures", "time", "year", "month", "jira", "ticket",
                "carte", "message", "messages", "veux", "veut", "envoyé",
                # bare years
                *[str(y) for y in range(2000, 2035)],
            }
            _fuzzy_keywords = set()
            for word in re.findall(r'\b\w{4,}\b', query_lower):
                if word in _FUZZY_STOPWORDS:
                    continue
                _fuzzy_keywords.add(word)
                en_word = _FR_TO_EN_TABLE_KEYWORDS.get(word)
                if en_word and en_word not in _FUZZY_STOPWORDS:
                    _fuzzy_keywords.add(en_word)

            def _scroll_tables_by_keyword(keyword: str) -> list:
                """Scroll Qdrant pour trouver les tables dont le nom contient le keyword."""
                try:
                    all_pts, _next = self.client.scroll(
                        collection_name="code_knowledge",
                        scroll_filter=None,
                        limit=200,
                        with_payload=True,
                    )
                    return [
                        p for p in all_pts
                        if keyword in (p.payload.get('table_name') or '').lower()
                        and (p.payload.get('table_name') or '').lower()
                    ]
                except Exception:
                    return []

            # Rechercher chaque nom de table potentiel directement
            for table_name in potential_table_names:
                try:
                    results = self.client.scroll(
                        collection_name="code_knowledge",
                        scroll_filter={
                            'must': [
                                {
                                    'key': 'table_name',
                                    'match': {
                                        'value': table_name
                                    }
                                }
                            ]
                        },
                        limit=1
                    )
                    
                    if results[0]:
                        point = results[0][0]
                        exact_matches.append({
                            'id': point.payload.get('snippet_id', str(point.id)),
                            'code': point.payload.get('code', ''),
                            'metadata': {k: v for k, v in point.payload.items() if k not in ['code', 'snippet_id']},
                            'distance': 0.0,  # Distance 0 = correspondance exacte
                            'original_score': 1.0,
                            'boost_applied': 0.0,
                            'match_type': 'exact'
                        })
                        logger.info(f"[OK] Correspondance exacte trouvée: {table_name}")
                except Exception as e:
                    logger.debug(f"Pas de correspondance exacte pour {table_name}: {e}")

            # Recherche fuzzy si aucune correspondance exacte
            if not exact_matches:
                seen_ids = set()
                for kw in _fuzzy_keywords:
                    if len(exact_matches) >= top_k:
                        break
                    for point in _scroll_tables_by_keyword(kw):
                        pid = str(point.id)
                        if pid not in seen_ids:
                            seen_ids.add(pid)
                            exact_matches.append({
                                'id': point.payload.get('snippet_id', pid),
                                'code': point.payload.get('code', ''),
                                'metadata': {k: v for k, v in point.payload.items() if k not in ['code', 'snippet_id']},
                                'distance': 0.1,
                                'original_score': 0.9,
                                'boost_applied': 0.0,
                                'match_type': 'fuzzy_keyword'
                            })
                            logger.info(f"[OK] Correspondance fuzzy trouvée: {point.payload.get('table_name')} (kw={kw})")
            
            # ÉTAPE 2: Recherche vectorielle sémantique
            query_embedding = self.embedding_model.encode(query).tolist()
            formatted_results = []  # Initialiser la liste des résultats sémantiques
            
            # Filtrer par langage si spécifié
            query_filter = None
            if language_filter:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="language",
                            match=MatchValue(value=language_filter)
                        )
                    ]
                )
            
            # Recherche dans Qdrant (nouvelle API query_points)
            search_result = self.client.query_points(
                collection_name="code_knowledge",
                query=query_embedding,
                limit=top_k * 2,  # Chercher plus de résultats pour compenser les doublons
                query_filter=query_filter
            )
            
            # Formater les résultats vectoriels
            for hit in search_result.points:
                # Vérifier si ce résultat est déjà dans exact_matches (éviter doublons)
                hit_id = str(hit.id)
                if any(r['id'] == hit_id or r['id'] == hit.payload.get('snippet_id', '') for r in exact_matches):
                    continue
                
                formatted_results.append({
                    'id': hit.payload.get('snippet_id', str(hit.id)),
                    'code': hit.payload.get('code', ''),
                    'metadata': {k: v for k, v in hit.payload.items() if k not in ['code', 'snippet_id']},
                    'distance': 1 - hit.score,
                    'original_score': hit.score,
                    'boost_applied': 0.0,
                    'match_type': 'semantic'
                })
            
            # ÉTAPE 3: Combiner et trier (exact matches en premier, puis sémantique)
            all_results = exact_matches + formatted_results
            
            # Limiter au top_k demandé
            all_results = all_results[:top_k]
            
            logger.info(f"[OK] Trouvé {len(all_results)} résultats ({len(exact_matches)} exact, {len(formatted_results)} semantic)")
            return all_results
            
        except Exception as e:
            logger.error(f"[ERREUR] search_similar_code: {e}")
            return []
    
    
    async def add_documentation(
        self,
        content: str,
        metadata: Dict[str, Any],
        doc_id: str
    ) -> bool:
        """
        Ajouter de la documentation indexée
        
        Args:
            content: Contenu textuel de la documentation
            metadata: Métadonnées (type, source, etc.)
            doc_id: ID unique du document
            
        Returns:
            True si succès
        """
        try:
            from qdrant_client.models import Distance, VectorParams, PointStruct  # lazy
            # Créer collection documentation si elle n'existe pas
            try:
                self.client.get_collection("documentation")
            except Exception:
                self.client.create_collection(
                    collection_name="documentation",
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
            
            # Générer l'embedding
            embedding = self.embedding_model.encode(content).tolist()
            
            # Créer le point
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "content": content,
                    "doc_id": doc_id,
                    **metadata
                }
            )
            
            # Ajouter à Qdrant
            self.client.upsert(
                collection_name="documentation",
                points=[point]
            )
            
            logger.info(f"[OK] Documentation {doc_id} ajoutée à Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"[ERREUR] add_documentation: {e}")
            return False
    
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Obtenir les statistiques du store vectoriel
        
        Returns:
            Statistiques (nombre de documents, langages, etc.)
        """
        try:
            # Obtenir info de la collection
            collection_info = self.client.get_collection("code_knowledge")
            code_count = collection_info.points_count
            
            # Récupérer quelques points pour les statistiques
            # (Qdrant ne permet pas de récupérer tous les points facilement)
            scroll_result = self.client.scroll(
                collection_name="code_knowledge",
                limit=1000,
                with_payload=True
            )
            
            languages = {}
            for point in scroll_result[0]:
                lang = point.payload.get('language', 'unknown')
                languages[lang] = languages.get(lang, 0) + 1
            
            return {
                'total_code_snippets': code_count,
                'languages': languages,
                'qdrant_host': self.qdrant_host,
                'qdrant_port': self.qdrant_port
            }
            
        except Exception as e:
            logger.error(f"[ERREUR] get_statistics: {e}")
            return {}


# Instance globale du service vectoriel — lazy init pour ne pas bloquer le démarrage
_vector_service_instance: Optional["VectorService"] = None


def get_vector_service() -> "VectorService":
    """Retourne l'instance singleton VectorService (lazy, ne bloque pas le démarrage)."""
    global _vector_service_instance
    if _vector_service_instance is None:
        _vector_service_instance = VectorService()
    return _vector_service_instance


# Compatibilité descendante : accès via `vector_service.xxx` fonctionne toujours
# mais ne charge plus rien au démarrage du module.
class _LazyVectorServiceProxy:
    """Proxy transparent vers VectorService, instancié uniquement au premier accès."""
    def __getattr__(self, name):
        return getattr(get_vector_service(), name)

    def __bool__(self):
        return True


vector_service = _LazyVectorServiceProxy()
