"""
Classification ML API Endpoints
"""
import os
import io
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import pandas as pd
import numpy as np

from app.models.classification_ml import (
    UploadResponse, TrainRequest, TrainResponse, PredictRequest, PredictResponse,
    PredictionResult, CorrectionRequest, CorrectionResponse, KeywordsConfig,
    ParetoResponse, ParetoItem, TimeseriesResponse, TimeseriesPoint,
    TopValuesResponse, TopValue, ExecSummary, CriticalityScore, TemporalAnomaly,
    PDFExportRequest, ModelInfo,
    DataPreparationRequest, DataPreparationResponse
)
from app.services.ml_classifier import MLClassifier
from app.services.data_processor import DataProcessor
from app.services.keywords_manager import KeywordsManager
from app.services.ml_ai_analyst import ml_ai_analyst
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Global state (in production, use Redis or database)
_uploaded_data: Optional[pd.DataFrame] = None
_uploaded_sessions: Dict[str, pd.DataFrame] = {}  # session_id -> dataframe
_ml_classifier = MLClassifier()
_data_processor = DataProcessor()
_keywords_manager = KeywordsManager()

import uuid

# Data directory
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
CORRECTIONS_LOG = DATA_DIR / "ml_corrections.jsonl"

# Persistent uploads directory
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


def _reload_session_from_disk(session_id: str) -> Optional[pd.DataFrame]:
    """Try to reload a session dataframe from persisted parquet (after server restart)."""
    parquet_path = UPLOADS_DIR / f"{session_id}.parquet"
    if parquet_path.exists():
        try:
            df = pd.read_parquet(parquet_path, dtype_backend="numpy_nullable")
            # Convert to plain numpy dtypes to avoid PyArrow-backed columns
            # that break sklearn's train_test_split (_safe_indexing / ChunkedArray)
            df = df.astype({col: "object" for col in df.select_dtypes("string").columns})
            _uploaded_sessions[session_id] = df
            logger.info(f"Reloaded session {session_id} from disk ({len(df)} rows)")
            return df
        except Exception as e:
            logger.error(f"Failed to reload session {session_id}: {e}")
    return None


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload and analyze CSV file with session persistence
    """
    global _uploaded_data, _uploaded_sessions
    
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Save temporarily
        temp_path = DATA_DIR / f"temp_{session_id}_{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            # Load and process
            df = _data_processor.load_csv_robust(str(temp_path))
        finally:
            # Always clean up temp file, even on error
            if temp_path.exists():
                temp_path.unlink()
        
        # Auto-drop unwanted column
        if "user_nom_complet" in df.columns:
            df = df.drop(columns=["user_nom_complet"])
            logger.info("Auto-dropped column: user_nom_complet")
        
        detected = _data_processor.detect_columns(df)
        
        # Store in memory with session ID
        _uploaded_data = df
        _uploaded_sessions[session_id] = df
        
        # Persist to disk (parquet + metadata JSON)
        parquet_path = UPLOADS_DIR / f"{session_id}.parquet"
        df.to_parquet(parquet_path, index=False)
        meta = {
            "session_id": session_id,
            "filename": file.filename,
            "n_rows": len(df),
            "columns": list(df.columns),
            "uploaded_at": pd.Timestamp.now().isoformat()
        }
        (UPLOADS_DIR / f"{session_id}.json").write_text(json.dumps(meta, ensure_ascii=False))
        logger.info(f"Persisted upload to disk: {parquet_path}")
        
        # Get preview
        preview = df.head(20).fillna("").to_dict("records")
        
        # Get stats
        stats = _data_processor.compute_stats(df)
        
        return UploadResponse(
            columns=list(df.columns),
            preview=preview,
            stats=stats,
            n_rows=len(df),
            detected_columns=detected,
            session_id=session_id  # Retourner session_id au frontend
        )
    
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/prepare", response_model=DataPreparationResponse)
async def prepare_data(request: DataPreparationRequest):
    """
    Prepare uploaded data (compute features, causes, categories)
    """
    global _uploaded_data

    # Reload from disk if session_id provided and memory is empty (server restart)
    if _uploaded_data is None and hasattr(request, 'session_id') and request.session_id:
        df_reload = _reload_session_from_disk(request.session_id)
        if df_reload is not None:
            _uploaded_data = df_reload

    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    
    try:
        import time
        start = time.time()
        
        columns_before = set(_uploaded_data.columns)
        
        _uploaded_data = _data_processor.prepare_dataframe(
            _uploaded_data,
            compute_causes=request.compute_causes,
            compute_categories=request.compute_categories
        )
        
        columns_after = set(_uploaded_data.columns)
        columns_added = list(columns_after - columns_before)
        
        processing_time = time.time() - start
        
        return DataPreparationResponse(
            n_rows=len(_uploaded_data),
            columns_added=columns_added,
            processing_time=round(processing_time, 2),
            warnings=[]
        )
    
    except Exception as e:
        logger.error(f"Data preparation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keywords-config", response_model=KeywordsConfig)
async def get_keywords_config():
    """Get keywords configuration"""
    config = _keywords_manager.get()
    return KeywordsConfig(categories=config)


@router.put("/keywords-config", response_model=KeywordsConfig)
async def update_keywords_config(config: KeywordsConfig):
    """Update keywords configuration"""
    success = _keywords_manager.save(config.categories)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save configuration")
    return config


@router.post("/keywords-config/reset")
async def reset_keywords_config():
    """Reset keywords configuration to defaults"""
    success = _keywords_manager.reset_to_default()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to reset configuration")
    return {"message": "Configuration reset to defaults"}


@router.post("/train", response_model=TrainResponse)
async def train_model(request: TrainRequest):
    """
    Train ML classification model with auto text column selection
    """
    global _uploaded_data, _uploaded_sessions
    
    # Restore from session — check memory first, then disk (handles server restart)
    if hasattr(request, 'session_id') and request.session_id:
        sid = request.session_id
        if sid in _uploaded_sessions:
            _uploaded_data = _uploaded_sessions[sid]
        else:
            df_reload = _reload_session_from_disk(sid)
            if df_reload is not None:
                _uploaded_data = df_reload

    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded — please re-upload your CSV")
    
    try:
        df = _uploaded_data
        
        # Auto-select text column if not provided
        text_col = request.text_col
        if not text_col:
            _TEXT_CANDIDATES = [
                "text_ml_postmortem", "texte_complet",
                # colonnes BRASIL standard
                "inc_resume", "resume",
                "inc_cause", "cause",
                "inc_commentaire", "commentaire",
                "inc_solution", "solution",
                "description", "text",
            ]
            for _candidate in _TEXT_CANDIDATES:
                if _candidate in df.columns:
                    text_col = _candidate
                    break
            if not text_col:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot auto-detect text column. Available columns: " + ", ".join(df.columns)
                )
        
        # Prepare training data
        df_train = df.dropna(subset=[request.label_col]).copy()
        df_train = df_train[df_train[request.label_col].astype(str).str.strip() != ""]
        
        if len(df_train) < 10:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough labeled data: {len(df_train)} rows (minimum 10)"
            )
        
        # Validate class count — sklearn needs at least 2 distinct classes
        n_classes = df_train[request.label_col].nunique()
        if n_classes < 2:
            unique_val = df_train[request.label_col].dropna().unique().tolist()
            # Suggest columns with 2-50 unique values (good ML candidates)
            alt_cols = [
                c for c in df.columns
                if c != request.label_col
                and 2 <= int(df[c].nunique()) <= 50
                and df[c].dtype == object
            ][:8]
            raise HTTPException(
                status_code=400,
                detail={
                    "error": (
                        f"La colonne '{request.label_col}' ne contient qu'une seule valeur "
                        f"('{unique_val[0] if unique_val else '?'}') — "
                        f"impossible d'entraîner un classificateur sans au moins 2 classes."
                    ),
                    "suggestion": "Choisissez une colonne avec au moins 2 classes différentes, par exemple 'categorie_intelligente'.",
                    "colonnes_candidates": alt_cols,
                }
            )

        if request.use_cause_hint and request.label_col == "categorie_intelligente":
            df_train["text_for_ml"] = (
                df_train[text_col].fillna("") + 
                " [CAUSE_HINT] " + 
                df_train.get("cause_canonique", pd.Series([""] * len(df_train))).fillna("")
            )
            text_col = "text_for_ml"
        
        # Train
        result = _ml_classifier.train(
            df=df_train,
            text_col=text_col,
            label_col=request.label_col,
            max_features=request.max_features,
            test_size=request.test_size
        )
        
        return TrainResponse(
            metrics={
                "classification_report": result["classification_report"],
                "macro_f1": result.get("macro_f1"),
                "confusion_matrix": result.get("confusion_matrix", [])
            },
            recommended_threshold=result["recommended_threshold"],
            classes=result["classes"],
            training_count=result["training_count"],
            trained_at=pd.Timestamp.now().isoformat(),
            weak_points=[]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Training failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-info", response_model=ModelInfo)
async def get_model_info():
    """Get information about current ML model"""
    info = _ml_classifier.get_info()
    return ModelInfo(**info)


@router.post("/predict-session", response_model=PredictResponse)
async def predict_session(request: PredictRequest):
    """
    Predict ALL tickets from the stored session df (no need to send ticket list).
    Uses session_id to reload data from memory or disk, then returns all predictions
    plus updated_preview of the full dataframe with categorie_intelligente column.
    """
    global _uploaded_data, _uploaded_sessions

    # Load model
    if _ml_classifier.model is None:
        loaded = _ml_classifier.load()
        if not loaded:
            raise HTTPException(status_code=400, detail="No trained model available")

    # Resolve the dataframe
    session_id = getattr(request, 'session_id', None)
    target_df = None
    if session_id:
        if session_id in _uploaded_sessions:
            target_df = _uploaded_sessions[session_id]
        else:
            target_df = _reload_session_from_disk(session_id)
    if target_df is None:
        target_df = _uploaded_data
    if target_df is None:
        raise HTTPException(status_code=400, detail="No data uploaded — please upload a CSV first")

    try:
        # Find text column
        text_cols = ["text_ml_postmortem", "texte_complet", "resume", "description"]
        text_col = next((c for c in text_cols if c in target_df.columns), None)
        if text_col is None:
            # fallback to first string column
            text_col = next((c for c in target_df.columns if target_df[c].dtype == object), None)
        if text_col is None:
            raise HTTPException(status_code=400, detail="No text column found in data")

        texts = pd.Series(target_df[text_col].fillna("").astype(str).tolist())

        # Predict all rows
        preds, confidences, all_probs = _ml_classifier.predict(texts, request.threshold)

        results = []
        accepted_count = 0
        classes = _ml_classifier.model.classes_ if _ml_classifier.model else []

        for i, (pred, conf) in enumerate(zip(preds, confidences)):
            accepted = conf >= request.threshold
            if accepted:
                accepted_count += 1
            prob_dict = None
            if all_probs is not None:
                prob_dict = {str(c): float(p) for c, p in zip(classes, all_probs[i])}
            results.append(PredictionResult(
                ticket_id=str(i),
                predicted_label=str(pred),
                confidence=float(conf),
                all_probabilities=prob_dict,
                accepted=accepted
            ))

        # Write categorie_intelligente back to df
        target_df = target_df.copy()
        target_df["categorie_intelligente"] = [str(p) for p in preds]

        if session_id:
            _uploaded_sessions[session_id] = target_df
        _uploaded_data = target_df

        # Persist to parquet + update metadata
        if session_id:
            parquet_path = UPLOADS_DIR / f"{session_id}.parquet"
            target_df.to_parquet(parquet_path, index=False)
            meta_path = UPLOADS_DIR / f"{session_id}.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                meta["columns"] = list(target_df.columns)
                meta_path.write_text(json.dumps(meta, ensure_ascii=False))

        stats = {
            "total": len(results),
            "accepted": accepted_count,
            "rejected": len(results) - accepted_count,
            "coverage": round(accepted_count / len(results), 3) if results else 0
        }

        # Return full dataframe preview (all rows, not just head 20)
        updated_preview = target_df.fillna("").to_dict("records")
        response = PredictResponse(predictions=results, stats=stats)
        response.updated_preview = updated_preview
        return response

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"predict-session failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Predict labels for tickets and write categorie_intelligente back to stored df
    """
    global _uploaded_data, _uploaded_sessions
    
    # Load model if not loaded
    if _ml_classifier.model is None:
        loaded = _ml_classifier.load()
        if not loaded:
            raise HTTPException(status_code=400, detail="No trained model available")
    
    try:
        # Extract texts
        texts = pd.Series([t.get("text", "") for t in request.tickets])
        ticket_ids = [t.get("ticket_id", f"ticket_{i}") for i, t in enumerate(request.tickets)]
        
        # Predict
        preds, confidences, all_probs = _ml_classifier.predict(texts, request.threshold)
        
        # Build results
        results = []
        accepted_count = 0
        
        for i, (pred, conf) in enumerate(zip(preds, confidences)):
            accepted = conf >= request.threshold
            if accepted:
                accepted_count += 1
            
            prob_dict = None
            if all_probs is not None:
                classes = _ml_classifier.model.classes_
                prob_dict = {str(c): float(p) for c, p in zip(classes, all_probs[i])}
            
            results.append(PredictionResult(
                ticket_id=ticket_ids[i],
                predicted_label=str(pred),
                confidence=float(conf),
                all_probabilities=prob_dict,
                accepted=accepted
            ))
        
        # Write categorie_intelligente back to stored df
        session_id = getattr(request, 'session_id', None)
        pred_map = {ticket_ids[i]: str(preds[i]) for i in range(len(preds))}

        # Update in-memory session df — reload from disk if needed
        target_df = None
        if session_id:
            if session_id in _uploaded_sessions:
                target_df = _uploaded_sessions[session_id]
            else:
                target_df = _reload_session_from_disk(session_id)
        if target_df is None and _uploaded_data is not None:
            target_df = _uploaded_data
        
        updated_preview = None
        if target_df is not None:
            target_df = target_df.copy()
            # Map predictions back using index-based ticket_ids
            categorie_col = []
            for idx in range(len(target_df)):
                tid = ticket_ids[idx] if idx < len(ticket_ids) else f"ticket_{idx}"
                categorie_col.append(pred_map.get(tid, ""))
            target_df["categorie_intelligente"] = categorie_col
            
            # Update memory
            if session_id and session_id in _uploaded_sessions:
                _uploaded_sessions[session_id] = target_df
            _uploaded_data = target_df
            
            # Persist updated parquet to disk
            if session_id:
                parquet_path = UPLOADS_DIR / f"{session_id}.parquet"
                if parquet_path.exists():
                    target_df.to_parquet(parquet_path, index=False)
                    # Update metadata to reflect new column
                    meta_path = UPLOADS_DIR / f"{session_id}.json"
                    if meta_path.exists():
                        meta = json.loads(meta_path.read_text())
                        meta["columns"] = list(target_df.columns)
                        meta_path.write_text(json.dumps(meta, ensure_ascii=False))
            
            updated_preview = target_df.head(20).fillna("").to_dict("records")
        
        stats = {
            "total": len(results),
            "accepted": accepted_count,
            "rejected": len(results) - accepted_count,
            "coverage": round(accepted_count / len(results), 3) if len(results) > 0 else 0
        }
        
        response = PredictResponse(predictions=results, stats=stats)
        if updated_preview is not None:
            response.updated_preview = updated_preview
        return response
    
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def list_uploaded_files():
    """
    List all persistently saved CSV uploads with metadata
    """
    files = []
    try:
        for json_path in sorted(UPLOADS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                meta = json.loads(json_path.read_text(encoding="utf-8"))
                files.append(meta)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Failed to list uploaded files: {e}")
    return files


@router.post("/files/{session_id}/load", response_model=UploadResponse)
async def load_saved_file(session_id: str):
    """
    Reload a previously saved file from disk into the active session
    """
    global _uploaded_data, _uploaded_sessions
    
    parquet_path = UPLOADS_DIR / f"{session_id}.parquet"
    meta_path = UPLOADS_DIR / f"{session_id}.json"
    
    if not parquet_path.exists():
        raise HTTPException(status_code=404, detail="Saved file not found")
    
    try:
        df = pd.read_parquet(parquet_path, dtype_backend="numpy_nullable")
        # Convert to plain numpy dtypes to avoid PyArrow-backed columns
        df = df.astype({col: "object" for col in df.select_dtypes("string").columns})
        _uploaded_sessions[session_id] = df
        _uploaded_data = df
        
        preview = df.head(20).fillna("").to_dict("records")
        stats = _data_processor.compute_stats(df)
        detected = _data_processor.detect_columns(df)
        
        return UploadResponse(
            columns=list(df.columns),
            preview=preview,
            stats=stats,
            n_rows=len(df),
            detected_columns=detected,
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"Failed to load saved file {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/corrections", response_model=CorrectionResponse)
async def save_correction(request: CorrectionRequest):
    """
    Save a manual correction to log
    """
    try:
        record = {
            "timestamp": pd.Timestamp.now().isoformat(),
            "ticket_id": request.ticket_id,
            "original_label": request.original_label,
            "corrected_label": request.corrected_label,
            "text": request.text,
            "reason": request.reason
        }
        
        with open(CORRECTIONS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        # Count corrections
        corrections_count = 0
        if CORRECTIONS_LOG.exists():
            with open(CORRECTIONS_LOG, "r", encoding="utf-8") as f:
                corrections_count = sum(1 for _ in f)
        
        return CorrectionResponse(
            success=True,
            corrections_count=corrections_count,
            message="Correction saved successfully"
        )
    
    except Exception as e:
        logger.error(f"Failed to save correction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/corrections/stats")
async def get_corrections_stats():
    """Get statistics about corrections"""
    if not CORRECTIONS_LOG.exists():
        return {"total": 0, "by_label": {}}
    
    try:
        corrections = []
        with open(CORRECTIONS_LOG, "r", encoding="utf-8") as f:
            for line in f:
                corrections.append(json.loads(line))
        
        by_label = {}
        for c in corrections:
            label = c.get("corrected_label", "Unknown")
            by_label[label] = by_label.get(label, 0) + 1
        
        return {
            "total": len(corrections),
            "by_label": by_label,
            "recent": corrections[-10:] if len(corrections) > 10 else corrections
        }
    except Exception as e:
        logger.error(f"Failed to get corrections stats: {e}")
        return {"total": 0, "by_label": {}, "error": str(e)}


@router.get("/pareto", response_model=ParetoResponse)
async def get_pareto(column: str):
    """
    Get Pareto analysis for a column
    """
    global _uploaded_data
    
    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    
    # Fallback automatique si la colonne demandée n'existe pas dans les données
    CANDIDATE_COLS = [
        column,  # demandée en premier
        "cause_canonique", "categorie_intelligente", "predicted_label",
        "label", "categorie", "category", "inc_cause", "groupe", "application",
    ]
    resolved_col = next((c for c in CANDIDATE_COLS if c in _uploaded_data.columns), None)

    # Dernier recours : prendre la première colonne de type object (texte/catégorie)
    if resolved_col is None:
        text_cols = [c for c in _uploaded_data.columns if _uploaded_data[c].dtype == object]
        if text_cols:
            resolved_col = text_cols[0]
            logger.info(f"[Pareto] Colonne '{column}' introuvable, fallback sur '{resolved_col}'")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Aucune colonne catégorielle disponible. Colonnes : {list(_uploaded_data.columns)[:10]}"
            )
    
    try:
        series = _uploaded_data[resolved_col].fillna("Non classé").replace("", "Non classé")
        vc = series.value_counts()
        
        total = vc.sum()
        items = []
        cumulative = 0.0
        
        for label, count in vc.items():
            pct = (count / total * 100) if total > 0 else 0
            cumulative += pct
            items.append(ParetoItem(
                label=str(label),
                volume=int(count),
                percentage=round(pct, 2),
                cumulative=round(cumulative, 2)
            ))
        
        return ParetoResponse(items=items, column=resolved_col)
    
    except Exception as e:
        logger.error(f"Pareto analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeseries", response_model=TimeseriesResponse)
async def get_timeseries(date_col: str = "date", group_by: Optional[str] = None):
    """
    Get timeseries data
    """
    global _uploaded_data
    
    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    
    if date_col not in _uploaded_data.columns:
        raise HTTPException(status_code=400, detail=f"Column '{date_col}' not found")
    
    try:
        df = _uploaded_data.copy()
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col])
        
        if df.empty:
            return TimeseriesResponse(data=[], date_col=date_col)
        
        if group_by and group_by in df.columns:
            agg = df.groupby([date_col, group_by]).size().reset_index(name="volume")
            data = [
                TimeseriesPoint(
                    date=row[date_col].strftime("%Y-%m-%d"),
                    volume=int(row["volume"]),
                    label=str(row[group_by])
                )
                for _, row in agg.iterrows()
            ]
        else:
            agg = df.groupby(date_col).size().reset_index(name="volume")
            data = [
                TimeseriesPoint(
                    date=row[date_col].strftime("%Y-%m-%d"),
                    volume=int(row["volume"])
                )
                for _, row in agg.iterrows()
            ]
        
        return TimeseriesResponse(data=data, date_col=date_col)
    
    except Exception as e:
        logger.error(f"Timeseries failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-values", response_model=TopValuesResponse)
async def get_top_values(column: str, topn: int = 10):
    """
    Get top N values for a column
    """
    global _uploaded_data
    
    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    
    if column not in _uploaded_data.columns:
        raise HTTPException(status_code=400, detail=f"Column '{column}' not found")
    
    try:
        vc = _uploaded_data[column].replace("", pd.NA).dropna().value_counts().head(topn)
        items = [TopValue(name=str(k), volume=int(v)) for k, v in vc.items()]
        
        return TopValuesResponse(
            items=items,
            column=column,
            total=len(_uploaded_data)
        )
    
    except Exception as e:
        logger.error(f"Top values failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exec-summary", response_model=ExecSummary)
async def get_exec_summary(ai: bool = Query(default=True, description="Enable AI-generated insights")):
    """
    Executive summary with KPIs + IA narrative + recommandations contextualisées
    + scores de criticité + anomalies temporelles.
    """
    global _uploaded_data

    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")

    try:
        df = _uploaded_data

        # ── KPIs de base ──────────────────────────────────────────────────
        volume = len(df)

        mttr_med = None
        if "mttr_days" in df.columns:
            try:
                mttr_med = float(pd.to_numeric(df["mttr_days"], errors="coerce").median())
                if pd.isna(mttr_med):
                    mttr_med = None
            except Exception:
                pass

        # Date range
        date_range = None
        for dc in ["datetime_debut", "date"]:
            if dc in df.columns:
                try:
                    s = pd.to_datetime(df[dc], errors="coerce").dropna()
                    if not s.empty:
                        date_range = {
                            "start": str(s.min().date()),
                            "end": str(s.max().date()),
                        }
                    break
                except Exception:
                    pass

        # Top causes
        top_causes = []
        if "cause_canonique" in df.columns:
            vc = df["cause_canonique"].replace("", pd.NA).dropna().value_counts().head(10)
            top_causes = [
                {"cause": str(k), "volume": int(v), "pct": round(v / volume * 100, 1)}
                for k, v in vc.items()
            ]

        # Top categories
        top_categories = []
        if "categorie_intelligente" in df.columns:
            vc = df["categorie_intelligente"].replace("", pd.NA).dropna().value_counts().head(10)
            top_categories = [
                {"category": str(k), "volume": int(v), "pct": round(v / volume * 100, 1)}
                for k, v in vc.items()
            ]

        # Top error codes
        top_codes = []
        if "codes_erreur" in df.columns:
            all_codes: list = []
            for lst in df["codes_erreur"]:
                if isinstance(lst, list):
                    all_codes.extend(lst)
            if all_codes:
                vc = pd.Series(all_codes).value_counts().head(10)
                top_codes = [{"code": str(k), "volume": int(v)} for k, v in vc.items()]

        # Highlights basiques
        highlights: List[str] = [
            f"Volume analysé : {volume} tickets"
            + (f" — MTTR médian : {mttr_med:.1f} jours" if mttr_med else "")
        ]
        if top_categories:
            top_cat = top_categories[0]
            highlights.append(
                f"Catégorie dominante : {top_cat['category']} (~{top_cat['pct']}% — {top_cat['volume']} tickets)"
            )
        if top_codes:
            codes_str = ", ".join(c["code"] for c in top_codes[:3])
            highlights.append(f"Codes d'erreur saillants : {codes_str}")
        if date_range:
            highlights.append(f"Période couverte : {date_range['start']} → {date_range['end']}")

        # ── IA insights (idées 1 + 2 + 3) ────────────────────────────────
        ai_narrative: Optional[str] = None
        ai_recommendations: Optional[List[AIRecommendation]] = None
        criticality_scores_out: Optional[List[CriticalityScore]] = None
        temporal_anomalies_out: Optional[List[TemporalAnomaly]] = None
        ai_generated = False

        if ai and (top_causes or top_categories):
            try:
                insights = await ml_ai_analyst.generate_executive_insights(
                    volume=volume,
                    mttr_med=mttr_med,
                    top_causes=top_causes,
                    top_categories=top_categories,
                    top_codes=top_codes,
                    date_range=date_range,
                )

                ai_narrative = insights.get("narrative")

                raw_recs = insights.get("recommendations", [])
                ai_recommendations = [
                    AIRecommendation(
                        priority=r.get("priority", i + 1),
                        action=r.get("action", ""),
                        impact=r.get("impact", "medium").lower(),
                        category=r.get("category", ""),
                    )
                    for i, r in enumerate(raw_recs)
                    if r.get("action")
                ]

                raw_cs = insights.get("criticality_scores", [])
                criticality_scores_out = []
                for cs in raw_cs:
                    cat_name = cs.get("category", "?")
                    vol_for_cat = next(
                        (c["volume"] for c in top_categories if c["category"] == cat_name), 0
                    )
                    mttr_for_cat = mttr_med
                    score_val = float(cs.get("score", 50))
                    badge = "high" if score_val >= 70 else ("medium" if score_val >= 40 else "low")
                    criticality_scores_out.append(CriticalityScore(
                        category=cat_name,
                        score=score_val,
                        volume=vol_for_cat,
                        mttr=mttr_for_cat,
                        badge=badge,
                        rationale=cs.get("rationale", ""),
                    ))

                # Idée 4 : anomalies temporelles
                timeseries_data = _build_timeseries_for_anomaly(df)
                if timeseries_data:
                    raw_anomalies = await ml_ai_analyst.detect_temporal_anomalies(timeseries_data)
                    temporal_anomalies_out = [
                        TemporalAnomaly(
                            period=a["period"],
                            volume=a["volume"],
                            delta_pct=a["delta_pct"],
                            direction=a["direction"],
                            hypothesis=a.get("hypothesis", ""),
                        )
                        for a in raw_anomalies
                    ]

                ai_generated = True

            except Exception as e:
                logger.warning(f"[exec-summary] AI insights failed (non-blocking): {e}")

        # Recommandations legacy (toujours présentes comme fallback)
        legacy_recommendations = [
            "Gouvernance inter-SI hebdomadaire (SCA/SEBA/BRASIL/IPON/Artemis)",
            "Checklists prérequis OPERATION/TP + contrôles FARID/VLAN/CCL",
            "Scripts de rattrapage standardisés",
            "Campagne Habilitations/Procédures (100% pratique)",
            "Pilotage : volumétrie rejets, délais de purge",
        ]

        return ExecSummary(
            volume=volume,
            mttr_med=mttr_med,
            top_causes=top_causes,
            top_categories=top_categories,
            top_codes=top_codes,
            highlights=highlights,
            recommendations=legacy_recommendations,
            ai_narrative=ai_narrative,
            ai_recommendations=ai_recommendations,
            criticality_scores=criticality_scores_out,
            temporal_anomalies=temporal_anomalies_out,
            date_range=date_range,
            ai_generated=ai_generated,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exec summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _build_timeseries_for_anomaly(df: pd.DataFrame) -> List[Dict]:
    """Helper : construit une timeseries agrégée par semaine pour la détection d'anomalies."""
    for dc in ["datetime_debut", "date"]:
        if dc in df.columns:
            try:
                tmp = df.copy()
                tmp["_date"] = pd.to_datetime(tmp[dc], errors="coerce")
                tmp = tmp.dropna(subset=["_date"])
                if tmp.empty:
                    continue
                tmp["_week"] = tmp["_date"].dt.to_period("W").dt.start_time
                agg = tmp.groupby("_week").size().reset_index(name="volume")
                return [
                    {"date": str(row["_week"].date()), "volume": int(row["volume"])}
                    for _, row in agg.iterrows()
                ]
            except Exception:
                continue
    return []


@router.post("/export-pdf")
async def export_pdf(request: PDFExportRequest):
    """
    Export PDF enrichi : page de garde, narratif IA, Pareto causes,
    scores criticité, anomalies temporelles, recommandations IA priorisées.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, PageBreak,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()

        # Styles custom
        title_style   = ParagraphStyle("Title",   parent=styles["Title"],   fontSize=20, spaceAfter=6, alignment=TA_CENTER)
        h1_style      = ParagraphStyle("H1",       parent=styles["Heading1"], fontSize=14, spaceBefore=14, spaceAfter=4, textColor=colors.HexColor("#1d4ed8"))
        h2_style      = ParagraphStyle("H2",       parent=styles["Heading2"], fontSize=11, spaceBefore=8, spaceAfter=3, textColor=colors.HexColor("#374151"))
        body_style    = ParagraphStyle("Body",     parent=styles["Normal"],  fontSize=9,  leading=13, spaceAfter=4, alignment=TA_JUSTIFY)
        meta_style    = ParagraphStyle("Meta",     parent=styles["Normal"],  fontSize=8,  textColor=colors.grey, alignment=TA_CENTER)
        badge_high    = ParagraphStyle("BadgeH",   parent=styles["Normal"],  fontSize=9,  textColor=colors.HexColor("#991b1b"))
        badge_med     = ParagraphStyle("BadgeM",   parent=styles["Normal"],  fontSize=9,  textColor=colors.HexColor("#92400e"))
        badge_low     = ParagraphStyle("BadgeL",   parent=styles["Normal"],  fontSize=9,  textColor=colors.HexColor("#065f46"))

        story = []

        # ── Page de garde ─────────────────────────────────────────────────
        story.append(Spacer(1, 2*cm))
        story.append(Paragraph(request.title, title_style))
        story.append(Spacer(1, 0.3*cm))
        generated_at = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
        story.append(Paragraph(f"Généré le {generated_at}", meta_style))
        if request.volume:
            story.append(Paragraph(f"Volume analysé : {request.volume:,} tickets", meta_style))
        if request.mttr_med:
            story.append(Paragraph(f"MTTR médian : {request.mttr_med:.1f} jours", meta_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1d4ed8"), spaceAfter=12))

        # ── Narratif IA ───────────────────────────────────────────────────
        if request.ai_narrative:
            story.append(Paragraph("Synthèse Managériale", h1_style))
            story.append(Paragraph(request.ai_narrative.replace("\n", "<br/>"), body_style))
            story.append(Spacer(1, 0.3*cm))

        # ── Recommandations IA ────────────────────────────────────────────
        recs = request.ai_recommendations or request.recommendations
        if recs:
            story.append(Paragraph("Recommandations Prioritaires", h1_style))
            for rec in recs:
                color = colors.HexColor("#991b1b") if "HIGH" in rec.upper() else (
                    colors.HexColor("#92400e") if "MEDIUM" in rec.upper() else colors.HexColor("#065f46")
                )
                story.append(Paragraph(f"• {rec}", ParagraphStyle(
                    "RecStyle", parent=body_style, textColor=color, spaceAfter=3
                )))
            story.append(Spacer(1, 0.3*cm))

        # ── Scores de criticité ───────────────────────────────────────────
        if request.criticality_scores:
            story.append(Paragraph("Criticité par Catégorie", h1_style))
            cs_data = [["Catégorie", "Score /100", "Volume", "Niveau", "Justification"]]
            for cs in sorted(request.criticality_scores, key=lambda x: -x.get("score", 0)):
                badge = cs.get("badge", "medium").upper()
                cs_data.append([
                    cs.get("category", "?"),
                    str(int(cs.get("score", 0))),
                    str(cs.get("volume", 0)),
                    badge,
                    cs.get("rationale", "")[:60],
                ])
            cs_table = Table(cs_data, colWidths=[4.5*cm, 2*cm, 2*cm, 2.5*cm, 6*cm])
            cs_table.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("FONTSIZE",      (0, 0), (-1, 0), 9),
                ("FONTSIZE",      (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
                ("GRID",          (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("ALIGN",         (1, 1), (2, -1), "CENTER"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(cs_table)
            story.append(Spacer(1, 0.4*cm))

        # ── Top causes ────────────────────────────────────────────────────
        if request.top_causes:
            story.append(Paragraph("Top Causes", h1_style))
            tc_data = [["Cause", "Volume", "% du total"]]
            for c in request.top_causes[:10]:
                tc_data.append([c.get("cause", "?"), str(c.get("volume", 0)), f"{c.get('pct', 0):.1f}%"])
            tc_table = Table(tc_data, colWidths=[10*cm, 3*cm, 4*cm])
            tc_table.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#374151")),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("FONTSIZE",      (0, 0), (-1, 0), 9),
                ("FONTSIZE",      (0, 1), (-1, -1), 8),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("GRID",          (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("ALIGN",         (1, 1), (-1, -1), "CENTER"),
                ("TOPPADDING",    (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(tc_table)
            story.append(Spacer(1, 0.4*cm))

        # ── Anomalies temporelles ─────────────────────────────────────────
        if request.temporal_anomalies:
            story.append(Paragraph("Anomalies Temporelles Détectées", h1_style))
            for a in request.temporal_anomalies[:6]:
                icon = "📈" if a.get("direction") == "spike" else "📉"
                delta = a.get("delta_pct", 0)
                story.append(Paragraph(
                    f"{icon} <b>{a.get('period', '?')}</b> — {a.get('volume', '?')} tickets "
                    f"({'+' if delta > 0 else ''}{delta:.1f}% vs moyenne) — {a.get('hypothesis', '')}",
                    body_style
                ))

        doc.build(story)
        buffer.seek(0)

        filename = request.title.replace(" ", "_").replace("/", "-")
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
        )

    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed — pip install reportlab")
    except Exception as e:
        logger.error(f"PDF export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/inject-insights")
async def inject_ml_insights_to_qdrant(background_tasks: BackgroundTasks):
    """
    Idée 5 : injecte le résumé exécutif ML (narratif + stats + recommandations)
    dans Qdrant (collection code_knowledge, type=ml_insight) pour que le chatbot
    puisse répondre sur les tendances de tickets.
    """
    global _uploaded_data

    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")

    try:
        # Appel exec-summary pour construire le payload
        summary = await get_exec_summary(ai=True)
        recs_raw   = [r.dict() for r in (summary.ai_recommendations or [])]
        cs_raw     = [cs.dict() for cs in (summary.criticality_scores or [])]
        anom_raw   = [a.dict() for a in (summary.temporal_anomalies or [])]

        text_payload = ml_ai_analyst.build_qdrant_payload(
            summary={
                "volume": summary.volume,
                "mttr_med": summary.mttr_med,
                "top_causes": summary.top_causes,
                "top_categories": summary.top_categories,
            },
            narrative=summary.ai_narrative,
            recommendations=recs_raw,
            criticality_scores=cs_raw,
            temporal_anomalies=anom_raw,
            date_range=summary.date_range,
        )

        background_tasks.add_task(
            _inject_insights_background, text_payload, summary.dict()
        )

        return {"message": "Injection ML insights en cours", "text_length": len(text_payload)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"inject-insights failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _inject_insights_background(text_payload: str, summary_dict: dict):
    """Tâche arrière-plan : injecte le snapshot ML dans Qdrant."""
    try:
        import uuid as uuid_lib
        from app.services.knowledge.vector_service import VectorService
        from qdrant_client.models import PointStruct

        vs = VectorService()
        if not vs.is_available():
            logger.warning("[ML-Inject] VectorService non disponible")
            return

        embedding = vs.embedding_model.encode(text_payload).tolist()
        point = PointStruct(
            id=str(uuid_lib.uuid4()),
            vector=embedding,
            payload={
                "code": text_payload,
                "snippet_id": f"ml-insight-{pd.Timestamp.now().strftime('%Y%m%d-%H%M')}",
                "name": "Analyse ML Tickets BRASIL",
                "type": "ml_insight",
                "language": "text",
                "file_path": "ml/exec_summary",
                "volume": summary_dict.get("volume", 0),
                "mttr_med": summary_dict.get("mttr_med"),
                "date_range": summary_dict.get("date_range", {}),
                "ai_generated": summary_dict.get("ai_generated", False),
                "indexed_at": pd.Timestamp.now().isoformat(),
            }
        )
        vs.client.upsert(collection_name="code_knowledge", points=[point])
        logger.info("[ML-Inject] Snapshot ML injecté dans code_knowledge")

    except Exception as e:
        logger.error(f"[ML-Inject] Erreur background: {e}")


@router.post("/retrain-with-corrections")
async def retrain_with_corrections():
    """
    Idée 6 : Relit le fichier ml_corrections.jsonl et réentraîne le modèle
    en fusionnant les corrections validées avec le dataset courant.
    """
    global _uploaded_data

    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")

    if not CORRECTIONS_LOG.exists():
        raise HTTPException(status_code=400, detail="No corrections found — correct predictions first")

    try:
        # Lire les corrections
        corrections = []
        with open(CORRECTIONS_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    corrections.append(json.loads(line))
                except Exception:
                    pass

        if not corrections:
            raise HTTPException(status_code=400, detail="Corrections file is empty")

        # Construire un mini-dataframe de corrections
        corr_df = pd.DataFrame(corrections)
        corr_df = corr_df[corr_df["corrected_label"].notna() & (corr_df["corrected_label"] != "")]

        # Chercher le label_col utilisé lors du dernier entraînement
        label_col = "cause_canonique"
        if _ml_classifier.model_card and _ml_classifier.model_card.get("label_col"):
            label_col = _ml_classifier.model_card["label_col"]

        # Sélectionner colonne texte disponible
        text_col = None
        for col in ["text_ml_postmortem", "texte_complet",
                    "inc_resume", "resume",
                    "inc_cause", "cause",
                    "inc_commentaire", "commentaire",
                    "inc_solution", "solution",
                    "description", "text"]:
            if col in _uploaded_data.columns:
                text_col = col
                break
        if not text_col and "text" in corr_df.columns:
            text_col = "text"

        if not text_col:
            raise HTTPException(status_code=400, detail="Cannot find text column in current dataset")

        # Fusionner dataset courant + corrections (les corrections écrasent le label)
        df_base = _uploaded_data[[text_col, label_col]].dropna(subset=[label_col]).copy()
        df_base = df_base.rename(columns={text_col: "__text__", label_col: "__label__"})

        if "corrected_label" in corr_df.columns and "text" in corr_df.columns:
            corr_subset = corr_df[["text", "corrected_label"]].rename(
                columns={"text": "__text__", "corrected_label": "__label__"}
            ).dropna()
            df_merged = pd.concat([df_base, corr_subset], ignore_index=True)
        else:
            df_merged = df_base

        df_merged = df_merged.rename(columns={"__text__": text_col, "__label__": label_col})

        result = _ml_classifier.train(
            df=df_merged,
            text_col=text_col,
            label_col=label_col,
            max_features=5000,
        )

        logger.info(f"[Retrain] Model retrained with {len(corr_df)} corrections merged")

        # Idea G: check if we should trigger auto-retrain next time
        total_corrections = 0
        if CORRECTIONS_LOG.exists():
            try:
                with open(CORRECTIONS_LOG, "r", encoding="utf-8") as _f:
                    total_corrections = sum(1 for _l in _f if _l.strip())
            except Exception:
                pass
        logger.info(f"[Retrain] Total corrections on file: {total_corrections}")

        return {
            "message": f"Modèle réentraîné avec {len(corr_df)} corrections fusionnées",
            "corrections_merged": len(corr_df),
            "total_samples": len(df_merged),
            "macro_f1": result.get("macro_f1"),
            "recommended_threshold": result.get("recommended_threshold"),
            "auto_retrain_threshold": AUTO_RETRAIN_THRESHOLD,
            "total_corrections_on_file": total_corrections,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Retrain with corrections failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index-tickets")
async def index_tickets_for_rag(background_tasks: BackgroundTasks):
    """
    Indexer les tickets uploadés dans Qdrant pour RAG chatbot
    """
    global _uploaded_data
    
    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    
    try:
        from app.services.knowledge.vector_service import VectorService
        from qdrant_client.models import Distance, VectorParams, PointStruct
        
        vector_service = VectorService()
        
        if not vector_service.is_available():
            raise HTTPException(status_code=503, detail="Vector service unavailable")
        
        # Créer collection tickets si n'existe pas
        try:
            vector_service.client.get_collection("tickets_rag")
        except:
            vector_service.client.create_collection(
                collection_name="tickets_rag",
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            logger.info("[RAG] Collection 'tickets_rag' créée")
        
        # Préparer textes tickets
        df = _uploaded_data.copy()
        
        # Détecter colonnes texte
        text_cols = []
        for col in ['inc_resume', 'resume', 'inc_cause', 'cause',
                    'inc_solution', 'solution', 'inc_commentaire', 'commentaire',
                    'signalement', 'description', 'text']:
            if col in df.columns:
                text_cols.append(col)
        
        if not text_cols:
            raise HTTPException(status_code=400, detail="No text columns found in data")
        
        # Créer texte complet pour chaque ticket
        df['text_for_rag'] = df[text_cols].fillna('').agg(' | '.join, axis=1)
        
        # Indexer en arrière-plan
        background_tasks.add_task(_index_tickets_background, df, vector_service)
        
        return {
            "message": f"Indexing {len(df)} tickets in background",
            "ticket_count": len(df),
            "text_columns": text_cols
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Index tickets failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _index_tickets_background(df: pd.DataFrame, vector_service):
    """Tâche arrière-plan: indexer tickets dans Qdrant avec labels ML enrichis"""
    try:
        from qdrant_client.models import PointStruct
        import uuid as uuid_lib

        # ── Pré-classification ML pour enrichir le payload ───────────────────
        ml_labels: dict = {}
        ml_confidences: dict = {}
        if _ml_classifier.model is not None:
            try:
                text_col = None
                for col in ["text_ml_postmortem", "texte_complet",
                            "inc_resume", "resume",
                            "inc_cause", "cause",
                            "inc_commentaire", "commentaire",
                            "inc_solution", "solution",
                            "description", "text", "text_for_rag"]:
                    if col in df.columns:
                        text_col = col
                        break
                if text_col:
                    preds, confs, _ = _ml_classifier.predict(
                        df[text_col].fillna("").astype(str),
                        threshold=0.0  # all tickets regardless of confidence
                    )
                    for idx_pos, idx_label in enumerate(df.index):
                        ml_labels[idx_label] = str(preds[idx_pos])
                        ml_confidences[idx_label] = float(confs[idx_pos])
            except Exception as ml_err:
                logger.warning(f"[RAG] ML pre-labeling failed: {ml_err}")

        points = []
        for idx, row in df.iterrows():
            # Générer embedding
            text = row['text_for_rag']
            embedding = vector_service.embedding_model.encode(text).tolist()

            # Extraire mois depuis date_debut si disponible
            date_str = str(row.get('date_debut', ''))
            mois = date_str[:7] if len(date_str) >= 7 else ""

            # Construire point Qdrant avec payload enrichi ML
            point = PointStruct(
                id=str(uuid_lib.uuid4()),
                vector=embedding,
                payload={
                    "ticket_id":       row.get('ticket_id', f"ticket_{idx}"),
                    "text":            text[:500],
                    "resume":          str(row.get('resume', '')),
                    "cause":           str(row.get('cause', '')),
                    "solution":        str(row.get('solution', '')),
                    "application":     str(row.get('application', '')),
                    "date":            date_str,
                    "mois":            mois,
                    "groupe":          str(row.get('groupe', '')),
                    # ML enrichment fields
                    "predicted_label": ml_labels.get(idx, ""),
                    "confidence":      round(ml_confidences.get(idx, 0.0), 3),
                    "mttr":            float(row.get('mttr', 0)) if pd.notna(row.get('mttr', None)) else None,
                    "indexed_at":      pd.Timestamp.now().isoformat(),
                }
            )
            points.append(point)

            # Batch upsert every 100 tickets
            if len(points) >= 100:
                vector_service.client.upsert(
                    collection_name="tickets_rag",
                    points=points
                )
                logger.info(f"[RAG] Indexed {len(points)} tickets batch")
                points = []

        # Upsert remaining
        if points:
            vector_service.client.upsert(
                collection_name="tickets_rag",
                points=points
            )

        logger.info(f"[RAG] Indexation complete: {len(df)} tickets (ML labels: {len(ml_labels)})")

    except Exception as e:
        logger.error(f"[RAG] Indexation failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Idea B — Solution Index by Cause
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/build-solution-index")
async def build_solution_index(background_tasks: BackgroundTasks):
    """
    Idée B : construit un index de solutions groupées par cause dans Qdrant.
    Pour chaque cause (top 20), agrège les solutions des tickets correspondants
    et injecte un document de type solution_pattern dans code_knowledge.
    """
    global _uploaded_data

    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    if _ml_classifier.model is None:
        raise HTTPException(status_code=400, detail="Model not trained yet")

    # Detect columns
    label_col = _ml_classifier.model_card.get("label_col", "") if _ml_classifier.model_card else ""
    solution_col = None
    for col in ["solution", "inc_solution", "resolution", "résolution"]:
        if col in _uploaded_data.columns:
            solution_col = col
            break

    if not label_col or label_col not in _uploaded_data.columns:
        raise HTTPException(status_code=400, detail="Label column not found in data")
    if not solution_col:
        raise HTTPException(status_code=400, detail="No solution column found (solution, inc_solution, resolution)")

    background_tasks.add_task(
        _build_solution_index_background,
        _uploaded_data.copy(),
        label_col,
        solution_col,
    )
    return {"message": "Construction de l'index de solutions en cours (arrière-plan)"}


def _build_solution_index_background(df: pd.DataFrame, label_col: str, solution_col: str):
    """Tâche arrière-plan : construire et injecter les patterns de solutions par cause."""
    try:
        from app.services.knowledge.vector_service import VectorService
        from qdrant_client.models import PointStruct
        import uuid as uuid_lib

        vs = VectorService()
        if not vs.is_available():
            logger.warning("[SolutionIndex] VectorService non disponible")
            return

        # Group solutions by label (top 20 by frequency)
        df_valid = df[[label_col, solution_col]].dropna(subset=[label_col])
        df_valid = df_valid[df_valid[solution_col].fillna("").str.len() > 10]
        top_labels = df_valid[label_col].value_counts().head(20).index.tolist()

        injected = 0
        for label in top_labels:
            group = df_valid[df_valid[label_col] == label]
            # Aggregate unique solutions (max 10 per label)
            solutions = (
                group[solution_col]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )[:10]

            if not solutions:
                continue

            solution_text = (
                f"Solutions connues pour la cause « {label} » ({len(group)} tickets) :\n\n"
                + "\n---\n".join(f"• {s[:500]}" for s in solutions)
            )

            embedding = vs.embedding_model.encode(solution_text).tolist()
            point = PointStruct(
                id=str(uuid_lib.uuid4()),
                vector=embedding,
                payload={
                    "code":       solution_text[:800],
                    "snippet_id": f"sol-pattern-{label[:40].replace(' ', '-')}",
                    "name":       f"Solutions — {label}",
                    "type":       "solution_pattern",
                    "cause":      label,
                    "ticket_count": len(group),
                    "indexed_at": pd.Timestamp.now().isoformat(),
                }
            )
            vs.client.upsert(collection_name="code_knowledge", points=[point])
            injected += 1

        logger.info(f"[SolutionIndex] {injected} solution patterns injected into code_knowledge")

    except Exception as e:
        logger.error(f"[SolutionIndex] Failed: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Idea A — Groq Auto-Labeling on Low Confidence
# ─────────────────────────────────────────────────────────────────────────────

class AutoLabelRequest(BaseModel):
    threshold: float = 0.5
    max_tickets: int = 50


class AutoLabelResult(BaseModel):
    ticket_id: str
    text: str
    current_label: Optional[str]
    current_confidence: float
    groq_suggested_label: str
    groq_rationale: str


class AutoLabelResponse(BaseModel):
    auto_labeled: int
    results: List[AutoLabelResult]


@router.post("/auto-label-low-confidence", response_model=AutoLabelResponse)
async def auto_label_low_confidence(request: "AutoLabelRequest"):
    """
    Idée A : pour les tickets dont la confiance < threshold, appelle Groq
    avec la liste des classes comme few-shot pour proposer un label alternatif.
    """
    global _uploaded_data

    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    if _ml_classifier.model is None:
        raise HTTPException(status_code=400, detail="Model not trained yet")

    # Detect text column
    text_col = None
    for col in ["text_ml_postmortem", "texte_complet",
                "inc_resume", "resume",
                "inc_cause", "cause",
                "inc_commentaire", "commentaire",
                "inc_solution", "solution",
                "description", "text"]:
        if col in _uploaded_data.columns:
            text_col = col
            break
    if not text_col:
        raise HTTPException(status_code=400, detail="No text column found")

    label_col = _ml_classifier.model_card.get("label_col", "") if _ml_classifier.model_card else ""
    classes = _ml_classifier.model_card.get("classes", []) if _ml_classifier.model_card else []
    if not classes:
        raise HTTPException(status_code=400, detail="No classes in model card")

    # Predict all and filter low confidence
    try:
        preds, confs, _ = _ml_classifier.predict(
            _uploaded_data[text_col].fillna("").astype(str),
            threshold=0.0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    df_w = _uploaded_data.copy()
    df_w["__pred__"] = preds
    df_w["__conf__"] = confs
    low_conf = df_w[df_w["__conf__"] < request.threshold].head(request.max_tickets)

    if low_conf.empty:
        return AutoLabelResponse(auto_labeled=0, results=[])

    classes_str = ", ".join(f"« {c} »" for c in classes)
    results = []

    for idx, row in low_conf.iterrows():
        ticket_text = str(row[text_col])[:600]
        current_label = str(row.get(label_col, "")) if label_col and label_col in row else ""
        current_conf = float(row["__conf__"])

        groq_prompt = (
            f"Tu es un expert en classification de tickets d'incident BRASIL (opérateur télécom).\n"
            f"Classes disponibles : {classes_str}\n\n"
            f"Ticket à classifier :\n\"\"\"\n{ticket_text}\n\"\"\"\n\n"
            f"Réponds en JSON strict : {{\"label\": \"<label>\", \"rationale\": \"<explication courte>\"}}"
        )

        try:
            raw = await ml_ai_analyst.llm_client.generate(
                prompt=groq_prompt,
                system_prompt="Tu es un classificateur de tickets télécom. Réponds uniquement en JSON.",
                max_tokens=150,
            )
            parsed = ml_ai_analyst._parse_json_response(raw)
            groq_label = parsed.get("label", current_label or "Autre")
            groq_rationale = parsed.get("rationale", "")
        except Exception as groq_err:
            groq_label = current_label or "Autre"
            groq_rationale = f"Groq indisponible: {groq_err}"

        results.append(AutoLabelResult(
            ticket_id=str(row.get("ticket_id", f"row_{idx}")),
            text=ticket_text[:200],
            current_label=current_label,
            current_confidence=round(current_conf, 3),
            groq_suggested_label=groq_label,
            groq_rationale=groq_rationale,
        ))

    return AutoLabelResponse(auto_labeled=len(results), results=results)


# ─────────────────────────────────────────────────────────────────────────────
# Idea G — Auto-retrain threshold (enhancement to retrain-with-corrections)
# ─────────────────────────────────────────────────────────────────────────────

# Track last auto-retrain metadata
_auto_retrain_status: Dict = {"last_trigger": None, "corrections_at_trigger": 0, "status": "idle"}
AUTO_RETRAIN_THRESHOLD = 20  # trigger auto-retrain when corrections >= this


@router.get("/corrections-status")
async def get_corrections_status():
    """Statut des corrections en attente et de l'auto-réentraînement."""
    n_corrections = 0
    if CORRECTIONS_LOG.exists():
        try:
            with open(CORRECTIONS_LOG, "r", encoding="utf-8") as f:
                n_corrections = sum(1 for line in f if line.strip())
        except Exception:
            pass

    return {
        "corrections_pending": n_corrections,
        "auto_retrain_threshold": AUTO_RETRAIN_THRESHOLD,
        "auto_retrain_eligible": n_corrections >= AUTO_RETRAIN_THRESHOLD,
        "last_auto_retrain": _auto_retrain_status.get("last_trigger"),
        "auto_retrain_status": _auto_retrain_status.get("status", "idle"),
    }


def _maybe_auto_retrain(n_corrections: int, background_tasks: Optional[BackgroundTasks] = None):
    """
    Idea G: Si n_corrections >= seuil ET modèle dispo → déclencher auto-réentraînement
    + inject-insights en arrière-plan.
    """
    global _auto_retrain_status

    if n_corrections < AUTO_RETRAIN_THRESHOLD:
        return
    if _ml_classifier.model is None or _uploaded_data is None:
        return
    if _auto_retrain_status.get("status") == "running":
        return

    _auto_retrain_status["status"] = "running"
    _auto_retrain_status["last_trigger"] = pd.Timestamp.now().isoformat()
    _auto_retrain_status["corrections_at_trigger"] = n_corrections
    logger.info(f"[AutoRetrain] Triggered: {n_corrections} corrections >= {AUTO_RETRAIN_THRESHOLD}")

    if background_tasks:
        background_tasks.add_task(_auto_retrain_background)
    else:
        import threading
        threading.Thread(target=_auto_retrain_background_sync, daemon=True).start()


def _auto_retrain_background_sync():
    """Wrapper sync pour threading (sans background_tasks)."""
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_auto_retrain_background())
    except Exception as e:
        logger.error(f"[AutoRetrain] Sync wrapper error: {e}")
    finally:
        _auto_retrain_status["status"] = "idle"


async def _auto_retrain_background():
    """Auto-retrain + inject-insights en arrière-plan."""
    global _auto_retrain_status
    try:
        # Read corrections
        if not CORRECTIONS_LOG.exists():
            return
        corrections = []
        with open(CORRECTIONS_LOG, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    corrections.append(json.loads(line.strip()))
                except Exception:
                    pass

        if not corrections or _uploaded_data is None:
            return

        label_col = _ml_classifier.model_card.get("label_col", "cause") if _ml_classifier.model_card else "cause"
        text_col = None
        for col in ["text_ml_postmortem", "texte_complet",
                    "inc_resume", "resume",
                    "inc_cause", "cause",
                    "inc_commentaire", "commentaire",
                    "inc_solution", "solution",
                    "description", "text"]:
            if col in _uploaded_data.columns:
                text_col = col
                break
        if not text_col:
            return

        corr_df = pd.DataFrame(corrections)
        df_base = _uploaded_data[[text_col, label_col]].dropna(subset=[label_col]).copy()
        df_base = df_base.rename(columns={text_col: "__text__", label_col: "__label__"})

        if "corrected_label" in corr_df.columns and "text" in corr_df.columns:
            corr_subset = corr_df[["text", "corrected_label"]].rename(
                columns={"text": "__text__", "corrected_label": "__label__"}
            ).dropna()
            df_merged = pd.concat([df_base, corr_subset], ignore_index=True)
        else:
            df_merged = df_base

        df_merged = df_merged.rename(columns={"__text__": text_col, "__label__": label_col})
        _ml_classifier.train(df=df_merged, text_col=text_col, label_col=label_col, max_features=5000)
        logger.info(f"[AutoRetrain] Model retrained with {len(corrections)} corrections")

        # Inject insights to Qdrant
        try:
            summary = await get_exec_summary(ai=True)
            recs_raw = [r.dict() for r in (summary.ai_recommendations or [])]
            cs_raw = [cs.dict() for cs in (summary.criticality_scores or [])]
            anom_raw = [a.dict() for a in (summary.temporal_anomalies or [])]
            text_payload = ml_ai_analyst.build_qdrant_payload(
                summary={"volume": summary.volume, "mttr_med": summary.mttr_med,
                         "top_causes": summary.top_causes, "top_categories": summary.top_categories},
                narrative=summary.ai_narrative,
                recommendations=recs_raw,
                criticality_scores=cs_raw,
                temporal_anomalies=anom_raw,
                date_range=summary.date_range,
            )
            _inject_insights_background(text_payload, summary.dict())
            logger.info("[AutoRetrain] Insights injected post-retrain")
        except Exception as inj_err:
            logger.warning(f"[AutoRetrain] Post-retrain inject-insights failed: {inj_err}")

        _auto_retrain_status["status"] = "idle"

    except Exception as e:
        logger.error(f"[AutoRetrain] Failed: {e}")
        _auto_retrain_status["status"] = "error"


# ─────────────────────────────────────────────────────────────────────────────
# Idea C — Distribution Drift Detection
# ─────────────────────────────────────────────────────────────────────────────

def _compute_kl_divergence(p: Dict[str, float], q: Dict[str, float]) -> float:
    """KL divergence D(P||Q) between two label distributions (as dicts)."""
    all_labels = set(p) | set(q)
    kl = 0.0
    for label in all_labels:
        pi = p.get(label, 1e-10)
        qi = q.get(label, 1e-10)
        if pi > 0:
            kl += pi * np.log(pi / qi)
    return float(kl)


@router.get("/drift-detection")
async def detect_distribution_drift():
    """
    Idée C : compare la distribution actuelle des labels avec la distribution
    enregistrée au moment de l'entraînement (model_card.json) via la divergence KL.
    Retourne une alerte si drift significatif (KL > 0.15).
    """
    global _uploaded_data

    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    if _ml_classifier.model is None or _ml_classifier.model_card is None:
        raise HTTPException(status_code=400, detail="Model not trained yet")

    label_col = _ml_classifier.model_card.get("label_col", "")
    if not label_col or label_col not in _uploaded_data.columns:
        raise HTTPException(status_code=400, detail=f"Label column '{label_col}' not found in data")

    # Current distribution
    current_counts = _uploaded_data[label_col].value_counts(normalize=True)
    current_dist: Dict[str, float] = current_counts.to_dict()

    # Training distribution from model_card
    training_classes = _ml_classifier.model_card.get("classes", [])
    n_samples = _ml_classifier.model_card.get("n_samples", 1)

    # Try to reconstruct training dist from a saved distribution snapshot
    training_dist_saved = _ml_classifier.model_card.get("label_distribution", {})
    if training_dist_saved:
        training_dist = {k: v / sum(training_dist_saved.values()) for k, v in training_dist_saved.items()}
    else:
        # Assume uniform if no snapshot
        training_dist = {c: 1.0 / len(training_classes) for c in training_classes} if training_classes else {}

    if not training_dist:
        raise HTTPException(status_code=400, detail="No training distribution available in model card")

    # KL divergence
    kl_score = _compute_kl_divergence(current_dist, training_dist)
    drift_detected = kl_score > 0.15

    # Identify shifted labels
    drifted_labels = []
    for label in set(current_dist) | set(training_dist):
        curr = current_dist.get(label, 0.0)
        train = training_dist.get(label, 0.0)
        delta = curr - train
        if abs(delta) > 0.05:  # >5% shift
            drifted_labels.append({
                "label": label,
                "current_pct": round(curr * 100, 1),
                "training_pct": round(train * 100, 1),
                "delta_pct": round(delta * 100, 1),
                "direction": "increase" if delta > 0 else "decrease",
            })
    drifted_labels.sort(key=lambda x: abs(x["delta_pct"]), reverse=True)

    alert_level = (
        "critical" if kl_score > 0.40
        else "warning" if kl_score > 0.15
        else "ok"
    )

    return {
        "kl_divergence": round(kl_score, 4),
        "drift_detected": drift_detected,
        "alert_level": alert_level,
        "alert_message": (
            f"⚠️ Dérive significative détectée (KL={kl_score:.3f}). "
            "Réentraîner le modèle avec les nouvelles données est recommandé."
            if drift_detected else
            f"✅ Distribution stable (KL={kl_score:.3f})"
        ),
        "drifted_labels": drifted_labels[:10],
        "current_distribution": {k: round(v * 100, 1) for k, v in list(current_dist.items())[:15]},
        "training_distribution": {k: round(v * 100, 1) for k, v in list(training_dist.items())[:15]},
        "training_date": _ml_classifier.model_card.get("trained_at"),
        "recommendation": (
            "Réentraîner le modèle avec les données actuelles via /retrain-with-corrections"
            if alert_level == "critical"
            else "Surveiller l'évolution de la distribution"
            if alert_level == "warning"
            else "Aucune action requise"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# /health — Statut global du module ML
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/health")
async def ml_health():
    """Santé globale du module ML : modèle, données, corrections, preprocessing."""
    model_info = _ml_classifier.get_info()
    n_corrections = 0
    if CORRECTIONS_LOG.exists():
        try:
            with open(CORRECTIONS_LOG, "r", encoding="utf-8") as f:
                n_corrections = sum(1 for line in f if line.strip())
        except Exception:
            pass

    data_loaded = _uploaded_data is not None or bool(_uploaded_sessions)

    try:
        from app.services.ml_preprocessing import telecom_preprocessor
        preprocessing_ok = True
        preprocessing_test = telecom_preprocessor.preprocess("DSLAM OP49MAB11 bloqué erreur 1300")
    except Exception:
        preprocessing_ok = False
        preprocessing_test = None

    status = "healthy"
    issues = []
    if not model_info.get("exists"):
        status = "degraded"
        issues.append("Aucun modèle entraîné — veuillez uploader un CSV et entraîner le modèle")
    if not data_loaded:
        issues.append("Aucune donnée en mémoire — veuillez uploader un CSV")
    if n_corrections >= AUTO_RETRAIN_THRESHOLD:
        issues.append(f"{n_corrections} corrections en attente (seuil: {AUTO_RETRAIN_THRESHOLD})")

    return {
        "status": status,
        "issues": issues,
        "model": {
            "exists": model_info.get("exists", False),
            "trained_at": model_info.get("trained_at"),
            "macro_f1": model_info.get("macro_f1"),
            "training_count": model_info.get("training_count", 0),
            "classes_count": len(model_info.get("classes", [])),
            "recommended_threshold": model_info.get("recommended_threshold", 0.7),
            "hybrid_embeddings": model_info.get("use_sentence_transformers", False),
        },
        "data": {
            "loaded": data_loaded,
            "sessions_count": len(_uploaded_sessions),
            "rows": len(_uploaded_data) if _uploaded_data is not None else 0,
        },
        "corrections": {
            "pending": n_corrections,
            "auto_retrain_threshold": AUTO_RETRAIN_THRESHOLD,
            "retrain_eligible": n_corrections >= AUTO_RETRAIN_THRESHOLD,
        },
        "preprocessing": {
            "available": preprocessing_ok,
            "sample_output": preprocessing_test,
        },
        "auto_retrain": _auto_retrain_status,
    }


# ─────────────────────────────────────────────────────────────────────────────
# /stats — Statistiques consolidées du module ML
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def ml_stats():
    """Statistiques consolidées : modèle + données + drift + corrections."""
    model_info = _ml_classifier.get_info()
    current_dist: dict = {}
    coverage = None

    if _uploaded_data is not None:
        label_col = model_info.get("label_col") or ""
        if label_col and label_col in _uploaded_data.columns:
            vc = _uploaded_data[label_col].value_counts(normalize=True)
            current_dist = {str(k): round(float(v) * 100, 1) for k, v in vc.items()}
        if "categorie_intelligente" in _uploaded_data.columns:
            total = len(_uploaded_data)
            predicted = _uploaded_data["categorie_intelligente"].replace("", pd.NA).dropna()
            coverage = round(len(predicted) / total * 100, 1) if total > 0 else None

    n_corrections = 0
    corrections_by_label: dict = {}
    if CORRECTIONS_LOG.exists():
        try:
            corrs = []
            with open(CORRECTIONS_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        corrs.append(json.loads(line))
                    except Exception:
                        pass
            n_corrections = len(corrs)
            for c in corrs:
                lbl = c.get("corrected_label", "?")
                corrections_by_label[lbl] = corrections_by_label.get(lbl, 0) + 1
        except Exception:
            pass

    return {
        "model": {
            "exists": model_info.get("exists", False),
            "macro_f1": model_info.get("macro_f1"),
            "training_count": model_info.get("training_count", 0),
            "n_samples": model_info.get("n_samples"),
            "classes": model_info.get("classes", []),
            "trained_at": model_info.get("trained_at"),
            "recommended_threshold": model_info.get("recommended_threshold", 0.7),
            "label_distribution_training": model_info.get("label_distribution", {}),
        },
        "predictions": {
            "coverage_pct": coverage,
            "current_distribution": current_dist,
        },
        "corrections": {
            "total": n_corrections,
            "by_label": corrections_by_label,
            "auto_retrain_threshold": AUTO_RETRAIN_THRESHOLD,
            "retrain_eligible": n_corrections >= AUTO_RETRAIN_THRESHOLD,
        },
        "auto_retrain": _auto_retrain_status,
    }


# ─────────────────────────────────────────────────────────────────────────────
# /model-versions — Historique et rollback
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/model-versions")
async def list_model_versions():
    """Liste des versions sauvegardées du modèle."""
    versions = _ml_classifier.list_versions()
    return {
        "versions": versions,
        "count": len(versions),
        "current": _ml_classifier.model_card.get("training_count") if _ml_classifier.model_card else None,
    }


@router.post("/model-versions/{version_dir}/rollback")
async def rollback_model(version_dir: str):
    """Recharge le modèle depuis une version précédente (rollback)."""
    success = _ml_classifier.rollback_to_version(version_dir)
    if not success:
        raise HTTPException(status_code=404, detail=f"Version '{version_dir}' introuvable ou rollback échoué")
    return {
        "message": f"Rollback vers '{version_dir}' effectué",
        "model_info": _ml_classifier.get_info(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# /export-csv — Export dataset avec prédictions
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/export-csv")
async def export_csv_endpoint(session_id: Optional[str] = Query(default=None)):
    """Export CSV du dataset courant (avec categorie_intelligente si disponible)."""
    global _uploaded_data, _uploaded_sessions
    target_df = None
    if session_id:
        if session_id in _uploaded_sessions:
            target_df = _uploaded_sessions[session_id]
        else:
            target_df = _reload_session_from_disk(session_id)
    if target_df is None:
        target_df = _uploaded_data
    if target_df is None:
        raise HTTPException(status_code=400, detail="No data loaded")
    try:
        buf = io.BytesIO()
        target_df.fillna("").to_csv(buf, index=False, encoding="utf-8-sig")
        buf.seek(0)
        filename = f"tickets_ml_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv"
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# /preprocessing/test — Débugger le preprocessor
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/preprocessing/test")
async def test_preprocessing(payload: dict):
    """Teste le TelecomPreprocessor sur un texte (pour debug et validation)."""
    text = payload.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Field 'text' is required")
    try:
        from app.services.ml_preprocessing import TelecomPreprocessor
        return TelecomPreprocessor().analyze(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVE LEARNING QUEUE  /active-learning/...
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/active-learning/queue")
async def get_active_learning_queue(
    status: str = Query("pending", description="pending | reviewed | corrected | dismissed | all"),
    max_items: int = Query(50, ge=1, le=200),
):
    """Retourne la file de review active learning (tickets à faible confiance)."""
    try:
        from app.services.ml_production import active_learning_queue
        items = active_learning_queue.get_queue(status=status, max_items=max_items)
        return {"items": items, "count": len(items), "status_filter": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/active-learning/{item_id}/review")
async def review_active_learning_item(item_id: str, payload: dict):
    """
    Soumet une correction depuis la file active learning.
    body: { corrected_label: str, status: "corrected" | "dismissed", reviewer?: str }
    """
    try:
        from app.services.ml_production import active_learning_queue
        status         = payload.get("status", "corrected")
        corrected_label = payload.get("corrected_label")
        reviewer       = payload.get("reviewer")
        if status not in ("corrected", "dismissed", "reviewed"):
            raise HTTPException(status_code=400, detail="status doit être corrected | dismissed | reviewed")
        updated = active_learning_queue.update_item(
            item_id=item_id,
            status=status,
            corrected_label=corrected_label,
            reviewer=reviewer,
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Item '{item_id}' introuvable dans la file")
        # Si correction validée, l'ajouter aux corrections ML
        if status == "corrected" and corrected_label:
            classifier.save_correction(
                text=payload.get("text", ""),
                predicted_label=payload.get("predicted_label", ""),
                corrected_label=corrected_label,
            )
        return {"status": "ok", "item_id": item_id, "action": status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active-learning/stats")
async def get_active_learning_stats():
    """Statistiques de la file active learning."""
    try:
        from app.services.ml_production import active_learning_queue
        return active_learning_queue.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# STAGING RETRAINING  /staging/...
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/staging/train-candidate")
async def staging_train_candidate(payload: dict):
    """
    Entraîne un modèle candidat dans staging/ (sans toucher à la production).
    body: { session_id?: str, text_col?: str, label_col: str }
    """
    from app.services.ml_production import staging_retrainer

    session_id = payload.get("session_id")
    text_col   = payload.get("text_col", "text")
    label_col  = payload.get("label_col", "label")

    # Récupérer les données
    df = None
    if session_id and session_id in _uploaded_sessions:
        df = _uploaded_sessions[session_id]
    elif session_id:
        df = _reload_session_from_disk(session_id)
    if df is None:
        df = _uploaded_data
    if df is None:
        raise HTTPException(status_code=400, detail="Aucune donnée disponible — uploader un CSV d'abord")
    if label_col not in df.columns:
        raise HTTPException(status_code=400, detail=f"Colonne '{label_col}' introuvable dans le dataset")

    try:
        # Corrections disponibles
        corrections_log = Path("data/corrections_log.jsonl")
        result = staging_retrainer.train_candidate(
            df=df, text_col=text_col, label_col=label_col,
            corrections_log=corrections_log if corrections_log.exists() else None,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staging/compare")
async def staging_compare():
    """Compare le modèle candidat staging vs production et retourne la décision de promotion."""
    try:
        from app.services.ml_production import staging_retrainer
        return staging_retrainer.compare()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/staging/promote")
async def staging_promote():
    """Promeut le candidat en production si les métriques le permettent."""
    try:
        from app.services.ml_production import staging_retrainer
        result = staging_retrainer.promote()
        if result.get("status") == "REJECTED":
            raise HTTPException(status_code=409, detail={
                "status": "REJECTED",
                "reasons": result.get("reasons", []),
            })
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staging/history")
async def staging_history(max_events: int = Query(20, ge=1, le=100)):
    """Historique des opérations staging (train / compare / promote)."""
    try:
        from app.services.ml_production import staging_retrainer
        return {"events": staging_retrainer.get_history(max_events=max_events)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# ERROR ANALYSIS  /error-analysis
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/error-analysis")
async def error_analysis(session_id: Optional[str] = Query(None)):
    """
    Analyse des erreurs de classification sur les données actuelles :
    top FP/FN par classe, confusion hotspots, classes critiques.
    Nécessite des colonnes 'predicted_label' et 'true_label' (ou équivalents) dans le session df.
    """
    from app.services.ml_production import error_analyzer

    # Récupérer le DataFrame
    df = None
    if session_id and session_id in _uploaded_sessions:
        df = _uploaded_sessions[session_id]
    elif session_id:
        df = _reload_session_from_disk(session_id)
    if df is None:
        df = _uploaded_data

    if df is None:
        raise HTTPException(status_code=400, detail="Aucune donnée chargée")

    # Détecter automatiquement les colonnes true vs pred
    TRUE_COLS = ["true_label", "label", "categorie", "category", "classe", "class"]
    PRED_COLS = ["predicted_label", "prediction", "pred_label", "label_pred"]

    true_col = next((c for c in TRUE_COLS if c in df.columns), None)
    pred_col = next((c for c in PRED_COLS if c in df.columns), None)
    text_col = next((c for c in ["text", "description", "resume", "summary"] if c in df.columns), None)
    conf_col = next((c for c in ["confidence", "score", "proba"] if c in df.columns), None)

    if true_col is None or pred_col is None:
        # Tenter de retourner une analyse depuis les corrections loguées
        corrections_file = Path("data/corrections_log.jsonl")
        if corrections_file.exists():
            rows = []
            with open(corrections_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
            if rows:
                cdf = pd.DataFrame(rows)
                cdf = cdf.dropna(subset=["predicted_label", "corrected_label"])
                if len(cdf) >= 5:
                    result = error_analyzer.analyze(
                        y_true=cdf["corrected_label"].astype(str).tolist(),
                        y_pred=cdf["predicted_label"].astype(str).tolist(),
                        texts=cdf["text"].fillna("").astype(str).tolist() if "text" in cdf.columns else None,
                    )
                    result["source"] = "corrections_log"
                    return result
        raise HTTPException(
            status_code=400,
            detail=f"Colonnes true/pred introuvables dans le dataset. "
                   f"Colonnes disponibles : {list(df.columns)[:10]}"
        )

    try:
        result = error_analyzer.analyze_from_session(
            df=df,
            true_col=true_col,
            pred_col=pred_col,
            text_col=text_col,
            conf_col=conf_col,
        )
        if result is None:
            raise HTTPException(status_code=400, detail="Données insuffisantes pour l'analyse (min 5 exemples labélisés)")
        result["source"] = f"session:{true_col}/{pred_col}"
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
