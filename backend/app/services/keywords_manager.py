"""
Keywords Configuration Manager
Handles keyword-based categorization configuration
"""
import json
from pathlib import Path
from typing import Dict, List
from app.core.logging import get_logger

logger = get_logger(__name__)


class KeywordsManager:
    """Manage keywords configuration for categorization"""
    
    DEFAULT_CONFIG = {
        "Intégration / Interfaces SI": [
            "flux", "integration", "synchro", "api", "webservice",
            "umi", "epc", "gpc", "pidi",
        ],
        "Blocage commande": [
            "avp", "1200", "1201", "1202", "1203", "1211", "1218", "5038", "9903",
            "commande bloquee", "affectation thd", "mise en service",
            "jalon", "rdv", "ot", "artemis", "cde", "bloque", "bloquee"
        ],
        "Erreurs techniques / Réseau": [
            "1002", "1101", "1102", "1109", "1300", "b4002",
            "http 404", "http 500", "http 503", "timeout", "119",
            "erreur technique", "server", "socket", "ssl", "tls"
        ],
        "Qualité des données / Référentiels": [
            "donnee fantome", "doublon", "double affectation",
            "incoherence", "farid", "inexistant", "null", "vide",
            "mapping", "referentiel", "nd inconnu"
        ],
        "Paramétrage / Equipement": [
            "vlan", "ccl", "olt", "dslam", "ports ouverts", "release",
            "xgspon", "gpon", "opfa", "opge", "oxeg", "oghk"
        ],
        "Opérations / TP": [
            "orrah", "orrahd", "operation seba", "tp xgspon",
            "j-2", "j+1", "en cours", "suspendue", "rattrapage"
        ],
        "Changements / MEP / Reprises": [
            "mep", "mise en production", "retour arriere",
            "rattrapage", "patch", "upgrade"
        ],
        "Habilitations / Procédures": [
            "100% pratique", "habilitation", "droits", "profil",
            "permission", "acces refuse", "forbidden", "401", "403"
        ],
        "Demandes / Evolution": [
            "evolution", "amelioration", "nouvelle fonctionnalite", "cr"
        ],
        "Performance": [
            "lent", "lenteur", "performance", "timeout", "ralenti", "slow"
        ]
    }
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.config_path = self.data_dir / "keywords_config.json"
        self._config = None
    
    def load(self) -> Dict[str, List[str]]:
        """Load keywords configuration"""
        if self._config is not None:
            return self._config
        
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                logger.info("Keywords config loaded")
                return self._config
        except Exception as e:
            logger.error(f"Failed to load keywords config: {e}")
        
        self._config = self.DEFAULT_CONFIG.copy()
        return self._config
    
    def save(self, config: Dict[str, List[str]]) -> bool:
        """Save keywords configuration"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self._config = config
            logger.info("Keywords config saved")
            return True
        except Exception as e:
            logger.error(f"Failed to save keywords config: {e}")
            return False
    
    def get(self) -> Dict[str, List[str]]:
        """Get current configuration"""
        return self.load()
    
    def update(self, category: str, keywords: List[str]) -> bool:
        """Update a single category"""
        config = self.load()
        config[category] = keywords
        return self.save(config)
    
    def delete_category(self, category: str) -> bool:
        """Delete a category"""
        config = self.load()
        if category in config:
            del config[category]
            return self.save(config)
        return False
    
    def reset_to_default(self) -> bool:
        """Reset to default configuration"""
        return self.save(self.DEFAULT_CONFIG.copy())
