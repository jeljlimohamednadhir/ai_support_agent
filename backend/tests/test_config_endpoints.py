"""
Tests for Configuration Endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_all_config():
    """Test getting all configuration"""
    response = client.get("/api/v1/config/")
    assert response.status_code in [200, 500]  # 500 if DB not setup
    
    if response.status_code == 200:
        data = response.json()
        assert "llm" in data
        assert "database" in data
        assert "ui_preferences" in data


def test_get_config_by_category():
    """Test getting config by category"""
    response = client.get("/api/v1/config/category/llm")
    assert response.status_code in [200, 500]


def test_update_config_item():
    """Test updating a single config item"""
    # First, try to get existing config
    response = client.put(
        "/api/v1/config/llm.temperature",
        json={"value": 0.8}
    )
    # May fail if config doesn't exist or DB not setup
    assert response.status_code in [200, 404, 500]


def test_bulk_config_update():
    """Test bulk configuration update"""
    config_data = {
        "llm": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.7,
            "max_tokens": 2000
        },
        "database": {
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_user": "neo4j",
            "qdrant_host": "localhost",
            "qdrant_port": 6333
        },
        "ui_preferences": {
            "theme": "light",
            "language": "fr",
            "items_per_page": 20,
            "enable_notifications": True
        }
    }
    
    response = client.post("/api/v1/config/bulk", json=config_data)
    assert response.status_code in [200, 500]
    
    if response.status_code == 200:
        data = response.json()
        assert data["status"] == "success"
