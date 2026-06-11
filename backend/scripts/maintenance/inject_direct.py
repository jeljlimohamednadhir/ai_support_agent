"""
Script d'injection directe dans Qdrant (sans dépendances app)
"""
import asyncio
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import uuid

# Configuration
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "code_knowledge"

# Exemples de code
SAMPLES = [
    {
        "id": "auth-user-1",
        "name": "UserService.authenticate",
        "language": "python",
        "file_path": "services/user_service.py",
        "code": """
class UserService:
    def authenticate(self, email: str, password: str) -> Optional[User]:
        \"\"\"
        Authentifie un utilisateur avec email et mot de passe.
        
        Règles métier:
        - L'utilisateur doit exister dans la BDD
        - Le compte doit être actif (is_active=True)
        - Le mot de passe doit correspondre au hash
        - Si l'utilisateur a role_id=1 (admin) et is_verified=False, erreur UnverifiedAdminError
        \"\"\"
        user = self.db.query(User).filter(User.email == email).first()
        
        if not user:
            raise UserNotFoundError(f"Utilisateur {email} non trouvé")
        
        if not user.is_active:
            raise UserInactiveError("Compte désactivé")
        
        if not verify_password(password, user.hashed_password):
            raise InvalidPasswordError("Mot de passe incorrect")
        
        if user.role_id == 1 and not user.is_verified:
            raise UnverifiedAdminError("Admin non vérifié")
        
        return user
"""
    },
    {
        "id": "order-create-1",
        "name": "OrderService.create_order",
        "language": "python",
        "file_path": "services/order_service.py",
        "code": """
class OrderService:
    def create_order(self, user_id: int, items: List[OrderItem]) -> Order:
        \"\"\"
        Crée une nouvelle commande.
        
        Règles métier:
        - Montant minimum: 10€
        - Maximum 50 articles par commande
        - Stock vérifié avant validation
        - Notification email envoyée après création
        \"\"\"
        if len(items) > 50:
            raise TooManyItemsError("Maximum 50 articles")
        
        total = sum(item.price * item.quantity for item in items)
        
        if total < 10:
            raise MinimumAmountError("Montant minimum: 10€")
        
        for item in items:
            product = self.product_repo.get(item.product_id)
            if product.stock < item.quantity:
                raise InsufficientStockError(f"Stock insuffisant: {product.name}")
        
        order = Order(user_id=user_id, total=total, status="pending")
        self.db.add(order)
        self.db.commit()
        
        self.notification_service.send_order_confirmation(order)
        return order
"""
    },
    {
        "id": "payment-process-1",
        "name": "PaymentService.process_payment",
        "language": "python",
        "file_path": "services/payment_service.py",
        "code": """
class PaymentService:
    def process_payment(self, order_id: int, payment_method: str) -> PaymentResult:
        \"\"\"
        Traite le paiement d'une commande.
        
        Flow:
        1. Valider que la commande existe et est en statut "pending"
        2. Vérifier que payment_method est dans ["card", "paypal", "bank_transfer"]
        3. Appeler le provider de paiement externe
        4. Si succès: order.status = "paid"
        5. Si échec: order.status = "payment_failed"
        \"\"\"
        order = self.order_repo.get(order_id)
        
        if not order:
            raise OrderNotFoundError(f"Commande {order_id} non trouvée")
        
        if order.status != "pending":
            raise InvalidOrderStatusError(f"Commande en statut {order.status}")
        
        valid_methods = ["card", "paypal", "bank_transfer"]
        if payment_method not in valid_methods:
            raise InvalidPaymentMethodError(f"Méthode {payment_method} non supportée")
        
        try:
            result = self.payment_provider.charge(
                amount=order.total,
                currency="EUR",
                method=payment_method
            )
        except PaymentProviderError as e:
            order.status = "payment_failed"
            self.db.commit()
            raise PaymentFailedError(str(e))
        
        order.status = "paid"
        order.payment_id = result.transaction_id
        self.db.commit()
        
        return result
"""
    },
    {
        "id": "api-login-1",
        "name": "POST /api/v1/users/login",
        "language": "python",
        "file_path": "api/v1/endpoints/auth.py",
        "code": """
@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    \"\"\"
    Endpoint de connexion utilisateur.
    
    Errors:
    - 401: Credentials invalides (UserNotFoundError, InvalidPasswordError)
    - 403: Compte désactivé (UserInactiveError) ou admin non vérifié (UnverifiedAdminError)
    - 429: Trop de tentatives (rate limit)
    \"\"\"
    user_service = UserService(db)
    
    try:
        user = user_service.authenticate(credentials.email, credentials.password)
    except (UserNotFoundError, InvalidPasswordError):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    except UserInactiveError:
        raise HTTPException(status_code=403, detail="Compte désactivé")
    except UnverifiedAdminError:
        raise HTTPException(status_code=403, detail="Compte admin non vérifié")
    
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "role": user.role.name}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
"""
    },
    {
        "id": "user-model-1",
        "name": "User Model",
        "language": "python",
        "file_path": "models/user.py",
        "code": """
class User(Base):
    \"\"\"
    Modèle utilisateur.
    
    Champs:
    - id: Primary key
    - email: Unique, indexé
    - hashed_password: Hash bcrypt
    - is_active: Boolean (default True)
    - is_verified: Boolean (default False)
    - role_id: Foreign key vers Role (1=admin, 2=user, 3=guest)
    - last_login: DateTime nullable
    \"\"\"
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    role_id = Column(Integer, ForeignKey("roles.id"), default=2, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    role = relationship("Role", back_populates="users")
    orders = relationship("Order", back_populates="user")
"""
    }
]


async def main():
    print("=" * 70)
    print("🚀 INJECTION DIRECTE DANS QDRANT")
    print("=" * 70)
    
    # 1. Connexion à Qdrant
    print(f"\n📦 Connexion à Qdrant ({QDRANT_HOST}:{QDRANT_PORT})...")
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=5)
        client.get_collections()
        print("✅ Connecté à Qdrant")
    except Exception as e:
        print(f"❌ Impossible de se connecter à Qdrant: {e}")
        print(f"\n💡 Vérifiez que Qdrant est démarré :")
        print(f"   wsl -d Ubuntu-24.04 -- podman ps | grep qdrant")
        return
    
    # 2. Créer/vérifier la collection
    print(f"\n📁 Vérification de la collection '{COLLECTION_NAME}'...")
    try:
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if COLLECTION_NAME not in collection_names:
            print(f"   Création de la collection '{COLLECTION_NAME}'...")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            print(f"   ✅ Collection '{COLLECTION_NAME}' créée")
        else:
            print(f"   ✅ Collection '{COLLECTION_NAME}' existe déjà")
    except Exception as e:
        print(f"❌ Erreur avec la collection: {e}")
        return
    
    # 3. Charger le modèle d'embeddings
    print(f"\n🤖 Chargement du modèle d'embeddings...")
    try:
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print("✅ Modèle chargé")
    except Exception as e:
        print(f"❌ Erreur de chargement du modèle: {e}")
        return
    
    # 4. Injecter les exemples
    print(f"\n📝 Injection de {len(SAMPLES)} exemples de code...\n")
    
    success_count = 0
    for sample in SAMPLES:
        try:
            # Générer l'embedding
            embedding = model.encode(sample["code"]).tolist()
            
            # Créer le point
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "snippet_id": sample["id"],
                    "name": sample["name"],
                    "language": sample["language"],
                    "file_path": sample["file_path"],
                    "code": sample["code"]
                }
            )
            
            # Insérer dans Qdrant
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=[point]
            )
            
            print(f"   ✅ {sample['name']}")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ {sample['name']} - Erreur: {e}")
    
    # 5. Résumé
    print(f"\n{'=' * 70}")
    print(f"📊 RÉSULTAT: {success_count}/{len(SAMPLES)} exemples injectés")
    print("=" * 70)
    
    if success_count > 0:
        print("\n🎉 Données injectées avec succès !")
        print("\n📌 Testez le chatbot avec des questions comme:")
        print('   - "Comment fonctionne l\'authentification des utilisateurs ?"')
        print('   - "Que se passe-t-il si un admin non vérifié essaie de se connecter ?"')
        print('   - "Quelles sont les règles pour créer une commande ?"')
        print('   - "Comment gérer un paiement échoué ?"')
        print('   - "Quels sont les champs du modèle User ?"')


if __name__ == "__main__":
    asyncio.run(main())
