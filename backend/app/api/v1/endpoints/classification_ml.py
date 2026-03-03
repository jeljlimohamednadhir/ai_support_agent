"""
Classification ML API Endpoints
"""
import os
import io
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import pandas as pd
import numpy as np

from app.models.classification_ml import (
    UploadResponse, TrainRequest, TrainResponse, PredictRequest, PredictResponse,
    PredictionResult, CorrectionRequest, CorrectionResponse, KeywordsConfig,
    ParetoResponse, ParetoItem, TimeseriesResponse, TimeseriesPoint,
    TopValuesResponse, TopValue, ExecSummary, PDFExportRequest, ModelInfo,
    DataPreparationRequest, DataPreparationResponse
)
from app.services.ml_classifier import MLClassifier
from app.services.data_processor import DataProcessor
from app.services.keywords_manager import KeywordsManager
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
        
        # Load and process
        df = _data_processor.load_csv_robust(str(temp_path))
        detected = _data_processor.detect_columns(df)
        
        # Store in memory with session ID
        _uploaded_data = df
        _uploaded_sessions[session_id] = df
        
        # Get preview
        preview = df.head(20).fillna("").to_dict("records")
        
        # Get stats
        stats = _data_processor.compute_stats(df)
        
        # Clean up
        temp_path.unlink()
        
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
    
    # Restore from session if provided
    if hasattr(request, 'session_id') and request.session_id:
        if request.session_id in _uploaded_sessions:
            _uploaded_data = _uploaded_sessions[request.session_id]
    
    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    
    try:
        df = _uploaded_data
        
        # Auto-select text column if not provided
        text_col = request.text_col
        if not text_col:
            if 'text_ml_postmortem' in df.columns:
                text_col = 'text_ml_postmortem'
            elif 'texte_complet' in df.columns:
                text_col = 'texte_complet'
            elif 'resume' in df.columns:
                text_col = 'resume'
            else:
                raise HTTPException(status_code=400, detail="Cannot auto-detect text column. Available columns: " + ", ".join(df.columns))
        
        # Prepare training data
        df_train = df.dropna(subset=[request.label_col]).copy()
        df_train = df_train[df_train[request.label_col].astype(str).str.strip() != ""]
        
        if len(df_train) < 10:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough labeled data: {len(df_train)} rows (minimum 10)"
            )
        
        # Prepare text column
        text_col = request.text_col
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
        logger.error(f"Training failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-info", response_model=ModelInfo)
async def get_model_info():
    """Get information about current ML model"""
    info = _ml_classifier.get_info()
    return ModelInfo(**info)


@router.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """
    Predict labels for tickets
    """
    global _uploaded_data
    
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
        
        stats = {
            "total": len(results),
            "accepted": accepted_count,
            "rejected": len(results) - accepted_count,
            "coverage": round(accepted_count / len(results), 3) if len(results) > 0 else 0
        }
        
        return PredictResponse(predictions=results, stats=stats)
    
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
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
    
    if column not in _uploaded_data.columns:
        raise HTTPException(status_code=400, detail=f"Column '{column}' not found")
    
    try:
        series = _uploaded_data[column].fillna("Non classé").replace("", "Non classé")
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
        
        return ParetoResponse(items=items, column=column)
    
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
async def get_exec_summary():
    """
    Get executive summary with KPIs and highlights
    """
    global _uploaded_data
    
    if _uploaded_data is None:
        raise HTTPException(status_code=400, detail="No data uploaded")
    
    try:
        df = _uploaded_data
        
        # Volume
        volume = len(df)
        
        # MTTR
        mttr_med = None
        if "mttr_days" in df.columns:
            try:
                mttr_med = float(pd.to_numeric(df["mttr_days"], errors="coerce").median())
            except:
                pass
        
        # Top causes
        top_causes = []
        if "cause_canonique" in df.columns:
            vc = df["cause_canonique"].value_counts().head(10)
            top_causes = [
                {"cause": str(k), "volume": int(v), "pct": round(v/volume*100, 1)}
                for k, v in vc.items()
            ]
        
        # Top categories
        top_categories = []
        if "categorie_intelligente" in df.columns:
            vc = df["categorie_intelligente"].value_counts().head(10)
            top_categories = [
                {"category": str(k), "volume": int(v), "pct": round(v/volume*100, 1)}
                for k, v in vc.items()
            ]
        
        # Top error codes
        top_codes = []
        if "codes_erreur" in df.columns:
            all_codes = []
            for lst in df["codes_erreur"]:
                if isinstance(lst, list):
                    all_codes.extend(lst)
            if all_codes:
                vc = pd.Series(all_codes).value_counts().head(10)
                top_codes = [{"code": str(k), "volume": int(v)} for k, v in vc.items()]
        
        # Highlights
        highlights = [
            f"Volume analysé: {volume} tickets" + (f"; MTTR médian: {mttr_med:.1f} jours" if mttr_med else "")
        ]
        
        if top_categories:
            top_cat = top_categories[0]
            highlights.append(
                f"Catégorie dominante: {top_cat['category']} (~{top_cat['pct']}% ; {top_cat['volume']} tickets)"
            )
        
        if top_codes:
            codes_str = ", ".join([c["code"] for c in top_codes[:3]])
            highlights.append(f"Codes d'erreur saillants: {codes_str}")
        
        # Recommendations
        recommendations = [
            "Gouvernance inter-SI hebdomadaire (SCA/SEBA/BRASIL/IPON/Artemis)",
            "Checklists prérequis OPERATION/TP + contrôles FARID/VLAN/CCL",
            "Scripts de rattrapage standardisés",
            "Campagne Habilitations/Procédures (100% pratique)",
            "Pilotage: volumétrie rejets, délais de purge"
        ]
        
        return ExecSummary(
            volume=volume,
            mttr_med=mttr_med,
            top_causes=top_causes,
            top_categories=top_categories,
            top_codes=top_codes,
            highlights=highlights,
            recommendations=recommendations
        )
    
    except Exception as e:
        logger.error(f"Exec summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-pdf")
async def export_pdf(request: PDFExportRequest):
    """
    Export PDF report
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2*cm, height - 2*cm, request.title)
        
        # Date
        c.setFont("Helvetica", 10)
        c.drawString(2*cm, height - 3*cm, f"Généré le: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
        
        # Content
        y = height - 4*cm
        c.setFont("Helvetica", 12)
        
        if request.rca_text:
            c.drawString(2*cm, y, "Analyse:")
            y -= 0.5*cm
            c.setFont("Helvetica", 10)
            for line in request.rca_text.split("\n")[:20]:
                c.drawString(2.5*cm, y, line[:80])
                y -= 0.4*cm
        
        c.save()
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={request.title}.pdf"}
        )
    
    except Exception as e:
        logger.error(f"PDF export failed: {e}")
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
        for col in ['resume', 'signalement', 'cause', 'solution', 'description']:
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
    """Tâche arrière-plan: indexer tickets dans Qdrant"""
    try:
        from qdrant_client.models import PointStruct
        import uuid as uuid_lib
        
        points = []
        for idx, row in df.iterrows():
            # Générer embedding
            text = row['text_for_rag']
            embedding = vector_service.embedding_model.encode(text).tolist()
            
            # Construire point Qdrant
            point = PointStruct(
                id=str(uuid_lib.uuid4()),
                vector=embedding,
                payload={
                    "ticket_id": row.get('ticket_id', f"ticket_{idx}"),
                    "text": text[:500],  # Limiter taille
                    "resume": str(row.get('resume', '')),
                    "cause": str(row.get('cause', '')),
                    "solution": str(row.get('solution', '')),
                    "application": str(row.get('application', '')),
                    "date": str(row.get('date_debut', '')),
                    "indexed_at": pd.Timestamp.now().isoformat()
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
        
        logger.info(f"[RAG] Indexation complete: {len(df)} tickets")
        
    except Exception as e:
        logger.error(f"[RAG] Indexation failed: {e}")
