"""
Pydantic models for Classification ML endpoints
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class UploadResponse(BaseModel):
    """Response after CSV upload and analysis"""
    columns: List[str] = Field(..., description="List of column names in CSV")
    preview: List[Dict[str, Any]] = Field(..., description="Preview of first rows")
    stats: Dict[str, Any] = Field(..., description="Dataset statistics")
    n_rows: int = Field(..., description="Total number of rows")
    detected_columns: Dict[str, Optional[str]] = Field(..., description="Auto-detected special columns")
    session_id: Optional[str] = Field(None, description="Session ID for upload persistence")


class TrainRequest(BaseModel):
    """Request to train ML model"""
    text_col: Optional[str] = Field(None, description="Column containing text for training (auto-detected if not provided)")
    label_col: str = Field(..., description="Column containing labels (target)")
    max_features: int = Field(default=5000, ge=1000, le=20000, description="TF-IDF max features")
    use_cause_hint: bool = Field(default=False, description="Include cause as hint for category prediction")
    test_size: float = Field(default=0.2, ge=0.1, le=0.5, description="Test set size ratio")
    session_id: Optional[str] = Field(None, description="Session ID to restore upload")


class TrainResponse(BaseModel):
    """Response after model training"""
    metrics: Dict[str, Any] = Field(..., description="Validation metrics")
    recommended_threshold: float = Field(..., description="Recommended confidence threshold")
    classes: List[str] = Field(..., description="List of target classes")
    training_count: int = Field(..., description="Number of times model has been trained")
    trained_at: str = Field(..., description="Training timestamp")
    weak_points: List[Dict[str, str]] = Field(default=[], description="Detected model weaknesses")


class PredictRequest(BaseModel):
    """Request for predictions"""
    tickets: List[Dict[str, str]] = Field(..., description="List of tickets to classify")
    threshold: float = Field(default=0.7, ge=0.5, le=0.95, description="Confidence threshold")


class PredictionResult(BaseModel):
    """Single prediction result"""
    ticket_id: str
    predicted_label: str
    confidence: float
    all_probabilities: Optional[Dict[str, float]] = None
    accepted: bool = Field(..., description="Whether prediction meets threshold")


class PredictResponse(BaseModel):
    """Response with predictions"""
    predictions: List[PredictionResult]
    stats: Dict[str, Any] = Field(..., description="Prediction statistics")


class CorrectionRequest(BaseModel):
    """Request to save a manual correction"""
    ticket_id: str
    corrected_label: str
    original_label: str
    text: Optional[str] = None
    reason: Optional[str] = None


class CorrectionResponse(BaseModel):
    """Response after saving correction"""
    success: bool
    corrections_count: int
    message: str


class KeywordsConfig(BaseModel):
    """Configuration for keyword-based categorization"""
    categories: Dict[str, List[str]] = Field(..., description="Category name -> list of keywords")


class ParetoItem(BaseModel):
    """Item in Pareto analysis"""
    label: str
    volume: int
    percentage: float
    cumulative: float


class ParetoResponse(BaseModel):
    """Response for Pareto analysis"""
    items: List[ParetoItem]
    column: str


class TimeseriesPoint(BaseModel):
    """Point in timeseries"""
    date: str
    volume: int
    label: Optional[str] = None


class TimeseriesResponse(BaseModel):
    """Response for timeseries data"""
    data: List[TimeseriesPoint]
    date_col: str


class TopValue(BaseModel):
    """Top value item"""
    name: str
    volume: int


class TopValuesResponse(BaseModel):
    """Response for top values"""
    items: List[TopValue]
    column: str
    total: int


class ExecHighlight(BaseModel):
    """Executive summary highlight"""
    text: str
    severity: Optional[str] = None


class ExecSummary(BaseModel):
    """Executive summary with KPIs"""
    volume: int
    mttr_med: Optional[float]
    top_causes: List[Dict[str, Any]]
    top_categories: List[Dict[str, Any]]
    top_codes: List[Dict[str, Any]]
    highlights: List[str]
    recommendations: List[str]
    date_range: Optional[Dict[str, str]] = None


class PDFExportRequest(BaseModel):
    """Request to export PDF report"""
    title: str = Field(default="Rapport Classification ML")
    rca_text: str = Field(default="")
    recommendations: List[str] = Field(default=[])
    synthesis: Dict[str, Any] = Field(default={})
    include_charts: bool = Field(default=False)


class ModelInfo(BaseModel):
    """Information about current ML model"""
    exists: bool
    trained_at: Optional[str] = None
    training_count: int = 0
    label_col: Optional[str] = None
    n_samples: Optional[int] = None
    classes: List[str] = []
    macro_f1: Optional[float] = None
    recommended_threshold: float = 0.7
    weak_points: List[Dict[str, str]] = []


class DataPreparationRequest(BaseModel):
    """Request for data preparation pipeline"""
    extended_semantic: bool = Field(default=True, description="Enable semantic clustering")
    compute_causes: bool = Field(default=True, description="Compute canonical causes")
    compute_categories: bool = Field(default=True, description="Compute intelligent categories")


class DataPreparationResponse(BaseModel):
    """Response after data preparation"""
    n_rows: int
    columns_added: List[str]
    processing_time: float
    warnings: List[str] = []
