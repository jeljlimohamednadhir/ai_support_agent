"""
Hierarchical ML Endpoints
Provides 2-level taxonomy classification (L1 KNN + L2 LR + Groq fallback).
"""
from __future__ import annotations

import io
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
import pandas as pd

from app.services.hierarchical_classifier import HierarchicalClassifier
from app.services.data_processor import DataProcessor
from app.core.logging import get_logger

# Re-use the shared session state from classification_ml
from app.api.v1.endpoints import classification_ml as _cml

logger = get_logger(__name__)

router = APIRouter()

# ─────────────────────────────────────────────────────────────────────────────
# Singleton service (shared across requests)
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

_hclassifier = HierarchicalClassifier(data_dir=str(DATA_DIR))
_hclassifier.load()  # attempt to restore persisted model on startup
_data_processor = DataProcessor()

# ─────────────────────────────────────────────────────────────────────────────
# Text column candidates (BRASIL schema)
# ─────────────────────────────────────────────────────────────────────────────
_TEXT_CANDIDATES = [
    "text_ml_postmortem", "texte_complet",
    "inc_resume",         "resume",
    "inc_cause",          "cause",
    "inc_commentaire",    "commentaire",
    "inc_solution",       "solution",
    "description",        "text",
]

_LABEL_CANDIDATES = [
    "qualification",     "inc_qualification",
    "label",             "categorie",
    "category",          "classe",
    "class",             "target",
    "inc_categorie",
]

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────────────────

class HierarchicalTrainRequest(BaseModel):
    session_id:   Optional[str]  = None
    text_col:     Optional[str]  = None
    label_col:    Optional[str]  = None
    # If True, the CSV already has 'level_1' and 'level_2' columns
    is_pre_mapped: bool = False
    l1_col:       Optional[str]  = None
    l2_col:       Optional[str]  = None


class HierarchicalTrainResponse(BaseModel):
    status:           str
    n_samples:        int
    l1_categories:    List[str]
    l1_distribution:  Dict[str, int]
    l2_stats:         Dict[str, Any]
    trained_at:       str
    message:          str


class PredictSingleRequest(BaseModel):
    text:       str
    use_llm:    bool = True


class PredictBatchRequest(BaseModel):
    texts:      List[str]
    use_llm:    bool = False  # disabled by default for batch (latency)


class PredictionResult(BaseModel):
    level_1:            str
    level_2:            str
    level_1_confidence: float
    level_2_confidence: float
    confidence_tier:    str     # HIGH / MEDIUM / LOW
    l2_source:          str
    llm_used:           bool
    llm_rationale:      Optional[str] = None
    nearest_neighbors:  List[Dict[str, Any]]
    needs_review:       bool


class PredictBatchResponse(BaseModel):
    predictions:        List[PredictionResult]
    n_high:             int
    n_medium:           int
    n_low:              int
    n_llm_fallback:     int


class LabelMappingResponse(BaseModel):
    mapping:    Dict[str, Dict[str, str]]
    count:      int


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_groq_client():
    """Return the Groq LLM client if available."""
    try:
        from app.services.ml_ai_analyst import ml_ai_analyst
        return ml_ai_analyst.llm_client
    except Exception:
        return None


def _resolve_text_col(df: pd.DataFrame, hint: Optional[str]) -> str:
    if hint and hint in df.columns:
        return hint
    for c in _TEXT_CANDIDATES:
        if c in df.columns:
            return c
    raise HTTPException(
        status_code=400,
        detail=f"Cannot auto-detect text column. Available columns: {', '.join(df.columns)}. "
               f"Set 'text_col' in your request."
    )


def _resolve_label_col(df: pd.DataFrame, hint: Optional[str]) -> str:
    if hint and hint in df.columns:
        return hint
    for c in _LABEL_CANDIDATES:
        if c in df.columns:
            return c
    raise HTTPException(
        status_code=400,
        detail=f"Cannot auto-detect label column. Available columns: {', '.join(df.columns)}. "
               f"Set 'label_col' in your request."
    )


def _build_combined_text(row: pd.Series) -> str:
    """Combine inc_resume + inc_cause + inc_solution into one string."""
    parts = []
    for col in ["inc_resume", "resume", "inc_cause", "cause", "inc_solution", "solution",
                "inc_commentaire", "description", "text_ml_postmortem", "texte_complet"]:
        val = row.get(col, None)
        if val and str(val).strip() not in ("", "nan", "None"):
            parts.append(str(val).strip())
    return " | ".join(parts) if parts else ""


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload a CSV file for hierarchical training.
    Delegates to the shared classification_ml upload logic so the session
    can be reused across both modules.
    """
    return await _cml.upload_csv(file)


@router.post("/train", response_model=HierarchicalTrainResponse)
async def train_hierarchical(request: HierarchicalTrainRequest):
    """
    Train the 2-level hierarchical classifier.
    Uses the uploaded CSV (shared session or latest upload).
    """
    global _hclassifier

    # ── Resolve dataframe from session ────────────────────────────────────────
    df: Optional[pd.DataFrame] = None
    if request.session_id and request.session_id in _cml._uploaded_sessions:
        df = _cml._uploaded_sessions[request.session_id]
    elif _cml._uploaded_data is not None:
        df = _cml._uploaded_data
    else:
        raise HTTPException(
            status_code=400,
            detail="No uploaded data found. Please call /hierarchical-ml/upload first."
        )

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded dataframe is empty.")

    # ── Build combined texts ───────────────────────────────────────────────────
    # If a single text_col is specified → use it directly
    # Otherwise → combine BRASIL text fields
    if request.text_col and request.text_col in df.columns:
        texts = df[request.text_col].fillna("").astype(str).tolist()
    else:
        # Try auto-detect first; if ambiguous, build combined text
        try:
            text_col = _resolve_text_col(df, request.text_col)
            texts = df[text_col].fillna("").astype(str).tolist()
        except HTTPException:
            logger.info("[HierarchicalML] Building combined text from BRASIL columns")
            texts = df.apply(_build_combined_text, axis=1).tolist()
            # Fallback: filter out empties
            if all(t == "" for t in texts):
                raise HTTPException(
                    status_code=400,
                    detail="Could not find any text content. "
                           f"Available columns: {', '.join(df.columns)}"
                )

    # ── Resolve label(s) ──────────────────────────────────────────────────────
    if request.is_pre_mapped and request.l1_col and request.l2_col:
        l1_col = request.l1_col
        l2_col = request.l2_col
        if l1_col not in df.columns or l2_col not in df.columns:
            raise HTTPException(
                status_code=400,
                detail=f"Pre-mapped columns not found. "
                       f"l1_col='{l1_col}', l2_col='{l2_col}' — "
                       f"available: {', '.join(df.columns)}"
            )
        labels_l1 = df[l1_col].fillna("CAUSE_INDETERMINEE").astype(str).tolist()
        labels_l2 = df[l2_col].fillna("CAUSE_INDETERMINEE").astype(str).tolist()
        labels_original = [""] * len(texts)
    else:
        label_col = _resolve_label_col(df, request.label_col)
        labels_original = df[label_col].fillna("CAUSE INDETERMINEE").astype(str).tolist()
        labels_l1 = None
        labels_l2 = None

    # Filter out rows with empty texts
    valid_idx = [i for i, t in enumerate(texts) if t.strip()]
    if len(valid_idx) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Too few valid text rows ({len(valid_idx)}). Need at least 5."
        )
    texts          = [texts[i] for i in valid_idx]
    labels_original = [labels_original[i] for i in valid_idx] if labels_original else labels_original
    if labels_l1:
        labels_l1 = [labels_l1[i] for i in valid_idx]
        labels_l2 = [labels_l2[i] for i in valid_idx]

    try:
        result = _hclassifier.train(
            texts=texts,
            labels_original=labels_original,
            label_col_is_hierarchical=request.is_pre_mapped,
            l1_col=labels_l1,
            l2_col=labels_l2,
        )
    except Exception as e:
        logger.error(f"[HierarchicalML] Training failed: {e}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

    return HierarchicalTrainResponse(
        status=result["status"],
        n_samples=result["n_samples"],
        l1_categories=result["l1_categories"],
        l1_distribution={k: int(v) for k, v in result["l1_distribution"].items()},
        l2_stats=result["l2_stats"],
        trained_at=result["trained_at"],
        message=(
            f"Hierarchical model trained on {result['n_samples']} tickets. "
            f"{len(result['l1_categories'])} L1 categories, "
            f"{sum(1 for v in result['l2_stats'].values() if v.get('model') == 'LogisticRegression')} L2 models."
        )
    )


@router.get("/taxonomy")
async def get_taxonomy():
    """Return the full 2-level taxonomy (categories + descriptions + label mapping)."""
    taxonomy = _hclassifier.get_taxonomy()
    return {
        "level_1_categories": taxonomy.get("level_1_categories", []),
        "level_2_descriptions": taxonomy.get("level_2_descriptions", {}),
        "label_mapping_count": len(taxonomy.get("label_mapping", {})),
    }


@router.get("/label-mapping", response_model=LabelMappingResponse)
async def get_label_mapping():
    """Return the complete old-label → new hierarchy mapping."""
    taxonomy = _hclassifier.get_taxonomy()
    mapping  = taxonomy.get("label_mapping", {})
    return LabelMappingResponse(mapping=mapping, count=len(mapping))


@router.post("/predict-single", response_model=PredictionResult)
async def predict_single(request: PredictSingleRequest):
    """
    Predict L1 + L2 category for a single ticket text.
    """
    if not _hclassifier.is_trained:
        # Try to load from disk
        loaded = _hclassifier.load()
        if not loaded:
            raise HTTPException(
                status_code=400,
                detail="Model not trained. Call POST /hierarchical-ml/train first."
            )

    groq_client = _get_groq_client() if request.use_llm else None

    try:
        result = _hclassifier.predict_single(text=request.text, groq_client=groq_client)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[HierarchicalML] predict_single failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return PredictionResult(**result)


@router.post("/predict", response_model=PredictBatchResponse)
async def predict_batch(request: PredictBatchRequest):
    """
    Predict L1 + L2 categories for a list of ticket texts.
    """
    if not _hclassifier.is_trained:
        loaded = _hclassifier.load()
        if not loaded:
            raise HTTPException(
                status_code=400,
                detail="Model not trained. Call POST /hierarchical-ml/train first."
            )

    if not request.texts:
        raise HTTPException(status_code=400, detail="'texts' list is empty.")

    groq_client = _get_groq_client() if request.use_llm else None

    try:
        raw_results = _hclassifier.predict_batch(
            texts=request.texts, groq_client=groq_client
        )
    except Exception as e:
        logger.error(f"[HierarchicalML] predict_batch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    predictions = [PredictionResult(**r) for r in raw_results]
    return PredictBatchResponse(
        predictions=predictions,
        n_high=sum(1 for p in predictions if p.confidence_tier == "HIGH"),
        n_medium=sum(1 for p in predictions if p.confidence_tier == "MEDIUM"),
        n_low=sum(1 for p in predictions if p.confidence_tier == "LOW"),
        n_llm_fallback=sum(1 for p in predictions if p.llm_used),
    )


@router.get("/model-info")
async def get_model_info():
    """Return model card metadata (training stats, thresholds, distribution)."""
    info = _hclassifier.get_info()
    if not info.get("exists"):
        return {
            "exists": False,
            "message": "No model trained yet. Call POST /hierarchical-ml/train."
        }
    return info


@router.post("/predict-csv")
async def predict_csv(
    file: UploadFile = File(...),
    text_col: Optional[str] = None,
    use_llm: bool = False,
):
    """
    Upload a CSV and return predictions for every row.
    Returns a JSON array with original columns + level_1, level_2, confidence_tier.
    """
    if not _hclassifier.is_trained:
        loaded = _hclassifier.load()
        if not loaded:
            raise HTTPException(
                status_code=400,
                detail="Model not trained. Call POST /hierarchical-ml/train first."
            )

    try:
        import io as _io
        content = await file.read()
        df = pd.read_csv(_io.BytesIO(content), sep=None, engine="python", encoding_errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {e}")

    # Resolve text column
    if text_col and text_col in df.columns:
        texts = df[text_col].fillna("").astype(str).tolist()
    else:
        try:
            col = _resolve_text_col(df, text_col)
            texts = df[col].fillna("").astype(str).tolist()
        except HTTPException:
            texts = df.apply(_build_combined_text, axis=1).tolist()

    groq_client = _get_groq_client() if use_llm else None

    try:
        results = _hclassifier.predict_batch(texts=texts, groq_client=groq_client)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Merge back
    out = df.copy()
    out["level_1"]            = [r["level_1"] for r in results]
    out["level_2"]            = [r["level_2"] for r in results]
    out["confidence_tier"]    = [r["confidence_tier"] for r in results]
    out["level_1_confidence"] = [r["level_1_confidence"] for r in results]
    out["level_2_confidence"] = [r["level_2_confidence"] for r in results]
    out["needs_review"]       = [r["needs_review"] for r in results]
    out["llm_used"]           = [r["llm_used"] for r in results]

    output_csv = io.StringIO()
    out.to_csv(output_csv, index=False, encoding="utf-8-sig")
    output_csv.seek(0)

    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([output_csv.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hierarchical_predictions.csv"},
    )
