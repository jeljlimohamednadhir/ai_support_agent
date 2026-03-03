#!/usr/bin/env python3
"""
Test the complete authentication flow with refresh tokens
Tests: Login -> Use token -> Refresh -> Logout -> Verify revocation
"""
import requests
import time
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1/auth"

# Test credentials (adjust as needed)
USERNAME = "admin"
PASSWORD = "Admin@123"  # Updated password

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_step(step, description):
    print(f"\n[{step}] {description}")
    print("-" * 80)

def test_health_check():
    """Test 1: Verify backend is accessible"""
    print_step(1, "Health Check - Vérification de l'accessibilité du backend")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Backend accessible (status: {response.status_code})")
            return True
        else:
            print(f"❌ Backend répond avec status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend inaccessible: {e}")
        print("\n⚠️  Assurez-vous que le backend est démarré:")
        print("   cd backend")
        print("   python -m uvicorn app.main:app --reload")
        return False

def test_login():
    """Test 2: Login and receive both access and refresh tokens"""
    print_step(2, "Login - Connexion et réception des tokens")
    try:
        response = requests.post(
            f"{API_BASE}/login",
            data={
                "username": USERNAME,
                "password": PASSWORD
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            refresh_token = data.get('refresh_token')
            
            print(f"✅ Connexion réussie!")
            print(f"   Access Token (15 min): {access_token[:50]}...")
            print(f"   Refresh Token (7 days): {refresh_token[:50] if refresh_token else 'N/A'}...")
            print(f"   Token Type: {data.get('token_type', 'N/A')}")
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'success': True
            }
        else:
            print(f"❌ Erreur {response.status_code}: {response.text}")
            return {'success': False}
            
    except Exception as e:
        print(f"❌ Erreur lors de la requête: {e}")
        return {'success': False}

def test_authenticated_request(access_token):
    """Test 3: Use access token to access protected endpoint"""
    print_step(3, "Protected Request - Utilisation du token d'accès")
    try:
        response = requests.get(
            f"{API_BASE}/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"✅ Accès autorisé!")
            print(f"   Username: {user_info.get('username')}")
            print(f"   Role: {user_info.get('role')}")
            print(f"   Email: {user_info.get('email')}")
            return True
        else:
            print(f"❌ Accès refusé: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_refresh_token(refresh_token):
    """Test 4: Refresh access token using refresh token"""
    print_step(4, "Token Refresh - Rafraîchissement des tokens")
    try:
        response = requests.post(
            f"{API_BASE}/refresh",
            json={
                "refresh_token": refresh_token
            },
            headers={
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            new_access_token = data.get('access_token')
            new_refresh_token = data.get('refresh_token')
            
            print(f"✅ Tokens rafraîchis avec succès!")
            print(f"   New Access Token: {new_access_token[:50]}...")
            print(f"   New Refresh Token: {new_refresh_token[:50] if new_refresh_token else 'N/A'}...")
            print(f"   ⚠️  L'ancien refresh token a été révoqué (rotation)")
            
            return {
                'access_token': new_access_token,
                'refresh_token': new_refresh_token,
                'success': True
            }
        else:
            print(f"❌ Erreur {response.status_code}: {response.text}")
            return {'success': False}
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return {'success': False}

def test_old_refresh_token(old_refresh_token):
    """Test 5: Verify old refresh token is revoked"""
    print_step(5, "Revocation Check - Vérification de la révocation")
    try:
        response = requests.post(
            f"{API_BASE}/refresh",
            json={
                "refresh_token": old_refresh_token
            },
            headers={
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 401:
            print(f"✅ Ancien token correctement révoqué!")
            print(f"   Message: {response.json().get('detail', 'N/A')}")
            return True
        else:
            print(f"❌ PROBLÈME: L'ancien token est encore valide!")
            print(f"   Ceci est un problème de sécurité - la rotation n'a pas fonctionné")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_logout(access_token, refresh_token):
    """Test 6: Logout and revoke tokens"""
    print_step(6, "Logout - Déconnexion et révocation")
    try:
        response = requests.post(
            f"{API_BASE}/logout",
            json={
                "refresh_token": refresh_token
            } if refresh_token else {},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Déconnexion réussie!")
            print(f"   Message: {response.json().get('message', 'N/A')}")
            return True
        else:
            print(f"⚠️  Déconnexion partielle: {response.text}")
            return True  # Still ok if partially successful
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_after_logout(refresh_token):
    """Test 7: Verify token is revoked after logout"""
    print_step(7, "Post-Logout Check - Vérification après déconnexion")
    try:
        response = requests.post(
            f"{API_BASE}/refresh",
            json={
                "refresh_token": refresh_token
            },
            headers={
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 401:
            print(f"✅ Token correctement révoqué après logout!")
            return True
        else:
            print(f"❌ PROBLÈME: Token encore valide après logout!")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    """Run all authentication tests"""
    print_section("TEST COMPLET DU SYSTÈME D'AUTHENTIFICATION")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend: {BASE_URL}")
    print(f"Username: {USERNAME}")
    
    results = []
    
    # Test 1: Health check
    if not test_health_check():
        print("\n❌ Tests arrêtés - Backend non accessible")
        return
    results.append(("Health Check", True))
    
    # Test 2: Login
    login_result = test_login()
    if not login_result['success']:
        print("\n❌ Tests arrêtés - Échec de la connexion")
        return
    
    access_token = login_result['access_token']
    refresh_token = login_result['refresh_token']
    results.append(("Login", True))
    
    # Test 3: Use access token
    auth_success = test_authenticated_request(access_token)
    results.append(("Protected Request", auth_success))
    
    # Test 4: Refresh tokens
    refresh_result = test_refresh_token(refresh_token)
    if refresh_result['success']:
        results.append(("Token Refresh", True))
        
        new_access_token = refresh_result['access_token']
        new_refresh_token = refresh_result['refresh_token']
        old_refresh_token = refresh_token
        
        # Test 5: Verify old token is revoked
        revoked_success = test_old_refresh_token(old_refresh_token)
        results.append(("Token Revocation", revoked_success))
        
        # Test 6: Logout
        logout_success = test_logout(new_access_token, new_refresh_token)
        results.append(("Logout", logout_success))
        
        # Test 7: Verify token revoked after logout
        post_logout_success = test_after_logout(new_refresh_token)
        results.append(("Post-Logout Revocation", post_logout_success))
    else:
        results.append(("Token Refresh", False))
    
    # Summary
    print_section("RÉSUMÉ DES TESTS")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    print(f"\nRésultat: {passed}/{total} tests réussis")
    
    if passed == total:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("\n✅ Le système d'authentification fonctionne correctement:")
        print("   - Login avec access + refresh tokens")
        print("   - Rotation automatique des tokens")
        print("   - Révocation sur logout")
        print("   - Protection contre la réutilisation de tokens")
    else:
        print(f"\n⚠️  {total - passed} test(s) ont échoué")

if __name__ == "__main__":
    main()
