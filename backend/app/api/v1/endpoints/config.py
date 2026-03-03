"""
Configuration Endpoints
Manage system configuration settings
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.schemas.config import (
    ConfigItem,
    ConfigUpdate,
    SystemConfiguration,
    ConfigResponse,
    LLMConfig,
    DatabaseConfig,
    UIPreferences
)
from app.models.database import SystemConfig
from app.db.session import get_db
from app.core.security import encrypt_value, decrypt_value
import json

router = APIRouter()


@router.get("/", response_model=SystemConfiguration)
async def get_all_config(db: Session = Depends(get_db)):
    """Get all configuration settings grouped by category"""
    try:
        configs = db.query(SystemConfig).all()
        
        # Group by category
        config_dict = {
            "llm": {},
            "database": {},
            "ui_preferences": {}
        }
        
        for config in configs:
            value = config.value
            if config.is_sensitive and value:
                # Decrypt sensitive values
                try:
                    value = decrypt_value(value)
                except:
                    value = None  # Don't expose if decryption fails
            
            category_key = config.category
            if category_key in config_dict:
                # Remove category prefix from key
                key_parts = config.key.split(".", 1)
                key_name = key_parts[1] if len(key_parts) > 1 else config.key
                config_dict[category_key][key_name] = value
        
        return SystemConfiguration(
            llm=LLMConfig(**config_dict.get("llm", {})),
            database=DatabaseConfig(**config_dict.get("database", {})),
            ui_preferences=UIPreferences(**config_dict.get("ui_preferences", {}))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching config: {str(e)}")


@router.get("/category/{category}", response_model=List[ConfigItem])
async def get_config_by_category(category: str, db: Session = Depends(get_db)):
    """Get configuration by category"""
    try:
        configs = db.query(SystemConfig).filter(SystemConfig.category == category).all()
        
        result = []
        for config in configs:
            value = config.value
            if config.is_sensitive:
                value = "***HIDDEN***"  # Don't expose sensitive values in list
            
            result.append(ConfigItem(
                key=config.key,
                value=value,
                category=config.category,
                is_sensitive=config.is_sensitive,
                description=config.description
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{key}", response_model=ConfigItem)
async def get_config_item(key: str, db: Session = Depends(get_db)):
    """Get a specific configuration item"""
    try:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        
        if not config:
            raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
        
        value = config.value
        if config.is_sensitive and value:
            try:
                value = decrypt_value(value)
            except:
                value = None
        
        return ConfigItem(
            key=config.key,
            value=value,
            category=config.category,
            is_sensitive=config.is_sensitive,
            description=config.description
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{key}", response_model=ConfigResponse)
async def update_config_item(key: str, update: ConfigUpdate, db: Session = Depends(get_db)):
    """Update a configuration item"""
    try:
        config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        
        if not config:
            raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
        
        value = update.value
        
        # Encrypt if sensitive
        if config.is_sensitive and value:
            value = encrypt_value(str(value))
        
        config.value = value
        db.commit()
        db.refresh(config)
        
        return ConfigResponse(
            status="success",
            message=f"Configuration '{key}' updated successfully",
            config={key: update.value}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")


@router.post("/bulk", response_model=ConfigResponse)
async def update_bulk_config(config_data: SystemConfiguration, db: Session = Depends(get_db)):
    """Update multiple configuration items at once"""
    try:
        updated_keys = []
        
        # Update LLM config
        for key, value in config_data.llm.dict().items():
            if value is not None:
                full_key = f"llm.{key}"
                config = db.query(SystemConfig).filter(SystemConfig.key == full_key).first()
                
                if config:
                    # Encrypt API keys
                    if "key" in key.lower() or "password" in key.lower():
                        value = encrypt_value(str(value))
                    
                    config.value = value
                    updated_keys.append(full_key)
                else:
                    # Create new config entry
                    new_config = SystemConfig(
                        key=full_key,
                        value=encrypt_value(str(value)) if "key" in key.lower() else value,
                        category="llm",
                        is_sensitive="key" in key.lower() or "password" in key.lower()
                    )
                    db.add(new_config)
                    updated_keys.append(full_key)
        
        # Update Database config
        for key, value in config_data.database.dict().items():
            if value is not None:
                full_key = f"database.{key}"
                config = db.query(SystemConfig).filter(SystemConfig.key == full_key).first()
                
                if config:
                    if "password" in key.lower() or "uri" in key.lower():
                        value = encrypt_value(str(value))
                    
                    config.value = value
                    updated_keys.append(full_key)
                else:
                    new_config = SystemConfig(
                        key=full_key,
                        value=encrypt_value(str(value)) if "password" in key.lower() else value,
                        category="database",
                        is_sensitive="password" in key.lower()
                    )
                    db.add(new_config)
                    updated_keys.append(full_key)
        
        # Update UI preferences
        for key, value in config_data.ui_preferences.dict().items():
            if value is not None:
                full_key = f"ui_preferences.{key}"
                config = db.query(SystemConfig).filter(SystemConfig.key == full_key).first()
                
                if config:
                    config.value = value
                    updated_keys.append(full_key)
                else:
                    new_config = SystemConfig(
                        key=full_key,
                        value=value,
                        category="ui_preferences",
                        is_sensitive=False
                    )
                    db.add(new_config)
                    updated_keys.append(full_key)
        
        db.commit()
        
        return ConfigResponse(
            status="success",
            message=f"Updated {len(updated_keys)} configuration items",
            config={"updated_keys": updated_keys}
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating bulk config: {str(e)}")


@router.post("/reset", response_model=ConfigResponse)
async def reset_config(db: Session = Depends(get_db)):
    """Reset configuration to defaults"""
    try:
        # Delete all config
        db.query(SystemConfig).delete()
        
        # Create default config
        default_configs = [
            SystemConfig(key="llm.provider", value="groq", category="llm", is_sensitive=False),
            SystemConfig(key="llm.model", value="llama-3.3-70b-versatile", category="llm", is_sensitive=False),
            SystemConfig(key="llm.temperature", value=0.7, category="llm", is_sensitive=False),
            SystemConfig(key="llm.max_tokens", value=2000, category="llm", is_sensitive=False),
            SystemConfig(key="database.neo4j_uri", value="bolt://localhost:7687", category="database", is_sensitive=False),
            SystemConfig(key="database.neo4j_user", value="neo4j", category="database", is_sensitive=False),
            SystemConfig(key="database.qdrant_host", value="localhost", category="database", is_sensitive=False),
            SystemConfig(key="database.qdrant_port", value=6333, category="database", is_sensitive=False),
            SystemConfig(key="ui_preferences.theme", value="light", category="ui_preferences", is_sensitive=False),
            SystemConfig(key="ui_preferences.language", value="fr", category="ui_preferences", is_sensitive=False),
            SystemConfig(key="ui_preferences.items_per_page", value=20, category="ui_preferences", is_sensitive=False),
            SystemConfig(key="ui_preferences.enable_notifications", value=True, category="ui_preferences", is_sensitive=False),
        ]
        
        db.add_all(default_configs)
        db.commit()
        
        return ConfigResponse(
            status="success",
            message="Configuration reset to defaults",
            config=None
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error resetting config: {str(e)}")
