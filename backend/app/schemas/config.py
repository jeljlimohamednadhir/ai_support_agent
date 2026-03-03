"""
Configuration Schemas
Pydantic models for system configuration
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime


class ConfigItem(BaseModel):
    """Configuration item schema"""
    key: str
    value: Any
    category: str
    is_sensitive: bool = False
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class ConfigUpdate(BaseModel):
    """Schema for updating configuration"""
    value: Any
    
    
class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: str = Field(default="groq", description="LLM provider (openai, anthropic, groq)")
    model: str = Field(default="llama-3.3-70b-versatile", description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key (if required)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=100, le=32000)
    
    
class DatabaseConfig(BaseModel):
    """Database configuration"""
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: Optional[str] = None
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    postgres_uri: Optional[str] = Field(default=None)


class UIPreferences(BaseModel):
    """UI preferences"""
    theme: str = Field(default="light", description="light or dark")
    language: str = Field(default="fr", description="UI language")
    items_per_page: int = Field(default=20, ge=5, le=100)
    enable_notifications: bool = Field(default=True)


class SystemConfiguration(BaseModel):
    """Complete system configuration"""
    llm: LLMConfig
    database: DatabaseConfig
    ui_preferences: UIPreferences
    
    class Config:
        from_attributes = True


class ConfigResponse(BaseModel):
    """Response for configuration operations"""
    status: str
    message: str
    config: Optional[Dict[str, Any]] = None
