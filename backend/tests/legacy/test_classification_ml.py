"""
Quick Test Script for Classification ML API
Run this to test the endpoints without frontend
"""
import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1/classification-ml"

def test_model_info():
    """Test model info endpoint"""
    print("\n1. Testing GET /model-info...")
    response = requests.get(f"{BASE_URL}/model-info")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()

def test_keywords_config():
    """Test keywords config endpoint"""
    print("\n2. Testing GET /keywords-config...")
    response = requests.get(f"{BASE_URL}/keywords-config")
    print(f"Status: {response.status_code}")
    config = response.json()
    print(f"Categories: {len(config['categories'])}")
    for cat, keywords in list(config['categories'].items())[:3]:
        print(f"  - {cat}: {len(keywords)} keywords")
    return config

def test_upload_csv():
    """Test CSV upload (requires a CSV file)"""
    csv_path = Path("test_tickets.csv")
    
    if not csv_path.exists():
        print("\n3. Skipping CSV upload test (no test_tickets.csv found)")
        print("   To test upload: create a CSV with columns like:")
        print("   ticket_id, resume, cause, solution, date_debut, groupe, statut")
        return None
    
    print(f"\n3. Testing POST /upload with {csv_path}...")
    with open(csv_path, 'rb') as f:
        files = {'file': ('test_tickets.csv', f, 'text/csv')}
        response = requests.post(f"{BASE_URL}/upload", files=files)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Columns: {data['columns']}")
        print(f"Rows: {data['n_rows']}")
        print(f"Detected columns: {data['detected_columns']}")
        return data
    else:
        print(f"Error: {response.text}")
        return None

def test_exec_summary():
    """Test executive summary (requires uploaded data)"""
    print("\n4. Testing GET /exec-summary...")
    response = requests.get(f"{BASE_URL}/exec-summary")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        summary = response.json()
        print(f"Volume: {summary['volume']}")
        print(f"MTTR median: {summary['mttr_med']}")
        print(f"Top causes: {len(summary['top_causes'])}")
        print(f"Highlights: {len(summary['highlights'])}")
        return summary
    else:
        print(f"Error: {response.text}")
        return None

def main():
    print("=" * 60)
    print("Classification ML API Tests")
    print("=" * 60)
    print("\nMake sure backend is running on http://localhost:8000")
    print("Run: uvicorn app.main:app --reload")
    
    try:
        # Test 1: Model Info
        model_info = test_model_info()
        
        # Test 2: Keywords Config
        keywords = test_keywords_config()
        
        # Test 3: Upload CSV (optional)
        upload_result = test_upload_csv()
        
        # Test 4: Exec Summary (if data uploaded)
        if upload_result:
            exec_summary = test_exec_summary()
        
        print("\n" + "=" * 60)
        print("✅ Basic tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend!")
        print("Make sure the backend is running:")
        print("  cd backend")
        print("  uvicorn app.main:app --reload")
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    main()
