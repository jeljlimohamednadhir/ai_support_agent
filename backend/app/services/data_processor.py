"""
Data Processing Service for Classification ML
Handles CSV parsing, column detection, feature engineering
"""
import re
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from unidecode import unidecode

from app.core.logging import get_logger

logger = get_logger(__name__)


class DataProcessor:
    """Process and prepare ticket data for ML"""
    
    # French stopwords
    FRENCH_STOPWORDS = [
        "a", "à", "afin", "ai", "ainsi", "alors", "après", "au", "aucun", "aussi", "autre", "aux",
        "avec", "avoir", "bon", "car", "ce", "cela", "ces", "ceux", "comme", "comment", "dans",
        "de", "des", "du", "depuis", "donc", "dont", "elle", "en", "encore", "entre", "es", "est",
        "et", "être", "fait", "il", "ils", "je", "la", "le", "les", "leur", "lui", "mais", "me",
        "même", "mon", "ne", "ni", "non", "nos", "notre", "nous", "on", "ou", "où", "par", "pas",
        "pour", "qu", "que", "qui", "sa", "se", "si", "son", "sont", "sous", "sur", "ta", "te",
        "tes", "toi", "ton", "tous", "tout", "tu", "un", "une", "vos", "votre", "vous", "y"
    ]
    
    # Error code pattern
    ERROR_CODE_PATTERN = r"\b(?:B?4002|1002|1101|1102|1109|1200|1201|1202|1203|1211|1218|1300|9903|5038|ERR[-_]?\d{2,6}|ORA-\d{4,5}|SQLSTATE[:\- ]?\w{5}|HTTP[ _-]?(?:4\d{2}|5\d{2}))\b"
    
    def __init__(self):
        self.error_pattern = re.compile(self.ERROR_CODE_PATTERN, re.IGNORECASE)
    
    def load_csv_robust(self, file_path: str) -> pd.DataFrame:
        """Load CSV with automatic encoding and delimiter detection"""
        encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1"]
        df = None
        
        # Try with pandas auto-detection
        for enc in encodings:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=enc,
                    engine="python",
                    dtype=str,
                    na_values=["-", "Inconnu", "Inconnue", "Not Specified", "0", "", "NA", "null", "None"]
                )
                break
            except:
                continue
        
        # Try with explicit separators
        if df is None:
            for enc in encodings:
                for sep in [";", ",", "\t", "|"]:
                    try:
                        df = pd.read_csv(
                            file_path,
                            sep=sep,
                            encoding=enc,
                            engine="python",
                            dtype=str
                        )
                        break
                    except:
                        continue
                if df is not None:
                    break
        
        if df is None:
            raise ValueError("Unable to read CSV file")
        
        # Clean up
        df = df.dropna(axis=1, how="all")
        df.columns = [str(c).strip() for c in df.columns]
        
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = df[c].astype(str).str.strip()
        
        logger.info(f"CSV loaded: {len(df)} rows, {len(df.columns)} columns")
        return df
    
    def detect_columns(self, df: pd.DataFrame) -> Dict[str, Optional[str]]:
        """Auto-detect important columns"""
        def find_col(keywords: List[str]) -> Optional[str]:
            cols_lower = {c: str(c).lower() for c in df.columns}
            for kw in keywords:
                k = kw.lower()
                for c, cn in cols_lower.items():
                    if k in cn:
                        return c
            return None
        
        detected = {
            "resume": find_col(["inc_resume", "resume", "résumé", "summary", "description", "titre"]),
            "cause": find_col(["inc_cause", "cause", "motif", "reason", "root cause"]),
            "solution": find_col(["inc_solution", "solution", "resolution"]),
            "signalement": find_col(["inc_sig", "symptome", "signalement", "sig"]),
            "application": find_col(["application", "app", "systeme", "system"]),
            "ticket": find_col(["ticket", "incident", "id", "numero", "reference"]),
            "date_debut": find_col(["datetime_debut", "date", "date_debut", "ouverture", "created"]),
            "groupe": find_col(["groupe", "group", "assignment group", "support"]),
            "statut": find_col(["statut", "status", "state"])
        }
        
        logger.info(f"Detected columns: {sum(1 for v in detected.values() if v)} out of {len(detected)}")
        return detected
    
    def extract_error_codes(self, text: str) -> List[str]:
        """Extract error codes from text"""
        if not isinstance(text, str):
            return []
        codes = self.error_pattern.findall(text or "")
        return sorted(set(str(c).upper() for c in codes if c))
    
    def compute_durations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute duration columns from datetime fields"""
        for col in ["datetime_debut", "datetime_resolution", "datetime_cloture"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
        
        # MTTR
        if "datetime_resolution" in df.columns and "datetime_debut" in df.columns:
            try:
                calc = (df["datetime_resolution"] - df["datetime_debut"]).dt.total_seconds() / (3600 * 24)
                df["mttr_days"] = calc
            except:
                df["mttr_days"] = pd.NA
        
        # Date fields
        if "datetime_debut" in df.columns:
            try:
                df["date"] = df["datetime_debut"].dt.date
                df["mois"] = df["datetime_debut"].dt.to_period("M").astype(str)
                df["semaine"] = df["datetime_debut"].dt.to_period("W").astype(str)
            except:
                pass
        
        return df
    
    def prepare_dataframe(
        self,
        df: pd.DataFrame,
        compute_causes: bool = True,
        compute_categories: bool = True
    ) -> pd.DataFrame:
        """Main data preparation pipeline"""
        logger.info("Starting data preparation...")
        
        # Detect columns
        detected = self.detect_columns(df)
        
        # Normalize column names
        col_map = {}
        if detected["resume"]:
            col_map[detected["resume"]] = "inc_resume"
        if detected["cause"]:
            col_map[detected["cause"]] = "inc_cause"
        if detected["solution"]:
            col_map[detected["solution"]] = "inc_solution"
        if detected["signalement"]:
            col_map[detected["signalement"]] = "inc_sig"
        if detected["application"]:
            col_map[detected["application"]] = "application"
        if detected["ticket"]:
            col_map[detected["ticket"]] = "ticket"
        if detected["date_debut"]:
            col_map[detected["date_debut"]] = "datetime_debut"
        if detected["groupe"]:
            col_map[detected["groupe"]] = "groupe_nom"
        if detected["statut"]:
            col_map[detected["statut"]] = "inc_statut"
        
        df = df.rename(columns=col_map)
        
        # Compute durations
        df = self.compute_durations(df)
        
        # Extract error codes
        text_cols = ["inc_resume", "inc_cause", "inc_solution", "inc_sig"]
        df["codes_erreur"] = df.apply(
            lambda r: self.extract_error_codes(" ".join([
                str(r.get(c, "")) for c in text_cols
            ])),
            axis=1
        )
        
        # Create ticket_id
        if "ticket" in df.columns:
            df["ticket_id"] = df["ticket"].astype(str)
        else:
            df["ticket_id"] = df.index.astype(str)
        
        # Create combined text
        df["texte_complet"] = (
            df.get("inc_resume", pd.Series([""] * len(df))).fillna("") + " " +
            df.get("inc_sig", pd.Series([""] * len(df))).fillna("") + " " +
            df.get("inc_cause", pd.Series([""] * len(df))).fillna("") + " " +
            df.get("inc_solution", pd.Series([""] * len(df))).fillna("")
        )
        df["texte_complet"] = df["texte_complet"].apply(
            lambda s: (s[:2000] + "...") if isinstance(s, str) and len(s) > 2000 else s
        )
        
        # Text for ML (post-mortem: includes solution, excludes cause)
        df["text_ml_postmortem"] = (
            df.get("inc_resume", pd.Series([""] * len(df))).fillna("") + " " +
            df.get("inc_sig", pd.Series([""] * len(df))).fillna("") + " " +
            df.get("inc_solution", pd.Series([""] * len(df))).fillna("") + " " +
            df.get("application", pd.Series([""] * len(df))).fillna("")
        )
        
        # Compute causes (if requested)
        if compute_causes:
            df["cause_canonique"] = "Non déterminé"  # Placeholder
        
        # Compute categories (if requested)
        if compute_categories:
            df["categorie_intelligente"] = "Incident (à préciser)"  # Placeholder
        
        # Fill missing application
        if "application" in df.columns:
            df["application"] = df["application"].fillna("Inconnue")
        
        logger.info(f"Data preparation complete: {len(df)} rows")
        return df
    
    def compute_stats(self, df: pd.DataFrame) -> Dict:
        """Compute dataset statistics"""
        stats = {
            "volume": len(df),
            "columns": list(df.columns),
            "dtypes": {c: str(df[c].dtype) for c in df.columns}
        }
        
        # MTTR
        if "mttr_days" in df.columns:
            try:
                stats["mttr_median"] = float(pd.to_numeric(df["mttr_days"], errors="coerce").median())
            except:
                stats["mttr_median"] = None
        
        # Top values
        if "application" in df.columns:
            stats["top_applications"] = df["application"].value_counts().head(5).to_dict()
        
        if "cause_canonique" in df.columns:
            stats["top_causes"] = df["cause_canonique"].value_counts().head(5).to_dict()
        
        if "categorie_intelligente" in df.columns:
            stats["top_categories"] = df["categorie_intelligente"].value_counts().head(5).to_dict()
        
        return stats
