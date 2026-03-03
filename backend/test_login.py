import requests
from passlib.context import CryptContext

# Configuration
BASE_URL = "http://localhost:8000"  # Ajuste si ton backend tourne sur un autre port
LOGIN_ENDPOINT = f"{BASE_URL}/api/v1/auth/login"

# Credentials à tester
USERNAME = "admin"
PASSWORD = "Admin@123"

print("=" * 80)
print("Test de connexion au backend")
print("=" * 80)
print(f"URL: {LOGIN_ENDPOINT}")
print(f"Username: {USERNAME}")
print(f"Password: {PASSWORD}")
print("-" * 80)

# Test 1: Vérifier que le backend est accessible
print("\n[1] Vérification de l'accessibilité du backend...")
try:
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    if response.status_code == 200:
        print(f"✓ Backend accessible (status: {response.status_code})")
    else:
        print(f"✗ Backend répond avec status: {response.status_code}")
except Exception as e:
    print(f"✗ Backend inaccessible: {e}")
    print("\nAssurez-vous que le backend est démarré (uvicorn app.main:app --reload)")
    exit(1)

# Test 2: Tentative de connexion avec form-data (OAuth2PasswordRequestForm)
print("\n[2] Tentative de connexion avec form-data (OAuth2)...")
try:
    response = requests.post(
        LOGIN_ENDPOINT,
        data={  # Utiliser 'data' pour form-data, pas 'json'
            "username": USERNAME,
            "password": PASSWORD
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        },
        timeout=10
    )
    
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code == 200:
        print("\n✓ Connexion réussie!")
        data = response.json()
        print(f"Token d'accès reçu: {data.get('access_token', 'N/A')[:50]}...")
        print(f"Type de token: {data.get('token_type', 'N/A')}")
    elif response.status_code == 401:
        print("\n✗ Erreur 401 - Unauthorized")
        print("Causes possibles:")
        print("  - Username incorrect (vérifier la casse)")
        print("  - Mot de passe incorrect")
        print("  - Hash du mot de passe corrompu en base")
    else:
        print(f"\n✗ Erreur {response.status_code}")
        
except Exception as e:
    print(f"✗ Erreur lors de la requête: {e}")

# Test 3: Vérifier le hash du mot de passe directement
print("\n[3] Vérification directe du hash bcrypt...")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Hash connu de l'admin dans PostgreSQL (récupéré du script précédent)
known_hash = "$2b$12$GT8TAH/A5Q8/0iHUk9IWhuNK0XcTq6ExPBI8w.Z3fFbDLbwVPeyde"
try:
    is_valid = pwd_context.verify(PASSWORD, known_hash)
    print(f"Hash bcrypt valide pour '{PASSWORD}': {'✓ OUI' if is_valid else '✗ NON'}")
except Exception as e:
    print(f"✗ Erreur lors de la vérification: {e}")

print("\n" + "=" * 80)
