"""
Script pour injecter des données d'exemple dans le Knowledge Graph
Permet de tester le RAG complet (Qdrant + Neo4j)
"""
import asyncio
import sys
from pathlib import Path

# Ajouter le chemin du backend
sys.path.insert(0, str(Path(__file__).parent))

from app.services.knowledge.vector_service import VectorService
from app.services.knowledge.graph_service import GraphService
from app.core.config import settings

# Exemples de code à injecter
SAMPLE_CODE = [
    {
        "id": "user_service_1",
        "name": "authenticate_user",
        "type": "function",
        "language": "python",
        "file_path": "app/services/auth/user_service.py",
        "code": '''
async def authenticate_user(email: str, password: str) -> Optional[User]:
    """
    Authentifie un utilisateur avec email et mot de passe.
    
    Règles métier:
    - L'utilisateur doit exister dans la base de données
    - Le mot de passe doit correspondre au hash stocké
    - Le compte doit être actif (is_active=True)
    - Si l'utilisateur est bloqué, retourne None
    
    Returns:
        User si authentification réussie, None sinon
    """
    user = await db.query(User).filter(User.email == email).first()
    
    if not user:
        logger.warning(f"Tentative de connexion avec email inconnu: {email}")
        return None
    
    if not user.is_active:
        logger.warning(f"Compte désactivé: {email}")
        return None
    
    if user.is_blocked:
        logger.warning(f"Compte bloqué: {email}")
        return None
    
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Mot de passe incorrect pour: {email}")
        await increment_failed_attempts(user)
        return None
    
    # Réinitialiser les tentatives échouées
    await reset_failed_attempts(user)
    return user
''',
        "description": "Fonction d'authentification utilisateur avec vérification du mot de passe et gestion des comptes bloqués"
    },
    {
        "id": "order_service_1",
        "name": "create_order",
        "type": "function",
        "language": "python",
        "file_path": "app/services/orders/order_service.py",
        "code": '''
async def create_order(user_id: str, items: List[OrderItem], shipping_address: Address) -> Order:
    """
    Crée une nouvelle commande pour un utilisateur.
    
    Règles métier:
    - L'utilisateur doit être vérifié (email confirmé)
    - Le panier ne doit pas être vide
    - Tous les produits doivent être en stock
    - Le total doit être > 0
    - L'adresse de livraison doit être valide
    
    Raises:
        UserNotVerifiedError: Si l'utilisateur n'a pas confirmé son email
        EmptyCartError: Si le panier est vide
        OutOfStockError: Si un produit n'est pas disponible
        InvalidAddressError: Si l'adresse est invalide
    """
    user = await get_user(user_id)
    
    if not user.is_verified:
        raise UserNotVerifiedError("Veuillez confirmer votre email avant de commander")
    
    if not items:
        raise EmptyCartError("Le panier est vide")
    
    # Vérifier le stock pour chaque article
    for item in items:
        product = await get_product(item.product_id)
        if product.stock < item.quantity:
            raise OutOfStockError(f"Stock insuffisant pour {product.name}")
    
    # Valider l'adresse
    if not await validate_address(shipping_address):
        raise InvalidAddressError("Adresse de livraison invalide")
    
    # Calculer le total
    total = sum(item.price * item.quantity for item in items)
    
    # Créer la commande
    order = Order(
        user_id=user_id,
        items=items,
        total=total,
        shipping_address=shipping_address,
        status=OrderStatus.PENDING
    )
    
    await db.add(order)
    await db.commit()
    
    # Envoyer notification
    await send_order_confirmation(user.email, order)
    
    return order
''',
        "description": "Création de commande avec validation du stock, de l'adresse et envoi de confirmation"
    },
    {
        "id": "admin_check_1",
        "name": "check_admin_access",
        "type": "function",
        "language": "python",
        "file_path": "app/middleware/auth_middleware.py",
        "code": '''
async def check_admin_access(user: User, resource: str) -> bool:
    """
    Vérifie si un utilisateur a accès à une ressource admin.
    
    Règles métier:
    - L'utilisateur doit avoir le rôle ADMIN ou SUPER_ADMIN
    - L'utilisateur doit être vérifié (is_verified=True)
    - L'utilisateur ne doit pas être bloqué
    - Pour certaines ressources sensibles, seul SUPER_ADMIN a accès
    
    Ressources sensibles (SUPER_ADMIN only):
    - user_management
    - system_config
    - audit_logs
    
    Returns:
        True si accès autorisé, False sinon
    """
    # Vérifications de base
    if not user.is_verified:
        logger.warning(f"Accès admin refusé - utilisateur non vérifié: {user.email}")
        return False
    
    if user.is_blocked:
        logger.warning(f"Accès admin refusé - utilisateur bloqué: {user.email}")
        return False
    
    # Vérifier le rôle
    if user.role not in [Role.ADMIN, Role.SUPER_ADMIN]:
        logger.warning(f"Accès admin refusé - rôle insuffisant: {user.email} ({user.role})")
        return False
    
    # Ressources sensibles
    sensitive_resources = ["user_management", "system_config", "audit_logs"]
    
    if resource in sensitive_resources:
        if user.role != Role.SUPER_ADMIN:
            logger.warning(f"Accès ressource sensible refusé: {user.email} -> {resource}")
            return False
    
    logger.info(f"Accès admin autorisé: {user.email} -> {resource}")
    return True
''',
        "description": "Vérification des droits d'accès admin avec gestion des ressources sensibles"
    },
    {
        "id": "payment_processor_1",
        "name": "process_payment",
        "type": "function",
        "language": "python",
        "file_path": "app/services/payments/payment_processor.py",
        "code": '''
async def process_payment(order_id: str, payment_method: PaymentMethod) -> PaymentResult:
    """
    Traite le paiement d'une commande.
    
    Règles métier:
    - La commande doit exister et être en statut PENDING
    - Le montant doit être > 0
    - La méthode de paiement doit être valide
    - En cas d'échec, la commande passe en statut PAYMENT_FAILED
    - En cas de succès, la commande passe en statut PAID
    
    Flow:
    1. Valider la commande
    2. Créer la transaction
    3. Appeler le processeur de paiement externe
    4. Mettre à jour le statut
    5. Envoyer les notifications
    
    Returns:
        PaymentResult avec le statut et les détails
    """
    order = await get_order(order_id)
    
    if not order:
        raise OrderNotFoundError(f"Commande {order_id} introuvable")
    
    if order.status != OrderStatus.PENDING:
        raise InvalidOrderStatusError(f"Commande {order_id} n'est pas en attente de paiement")
    
    if order.total <= 0:
        raise InvalidAmountError("Le montant doit être supérieur à 0")
    
    # Créer la transaction
    transaction = Transaction(
        order_id=order_id,
        amount=order.total,
        method=payment_method,
        status=TransactionStatus.PENDING
    )
    await db.add(transaction)
    
    try:
        # Appeler le processeur externe (Stripe, PayPal, etc.)
        external_result = await payment_gateway.charge(
            amount=order.total,
            currency="EUR",
            method=payment_method,
            metadata={"order_id": order_id}
        )
        
        if external_result.success:
            transaction.status = TransactionStatus.SUCCESS
            transaction.external_id = external_result.transaction_id
            order.status = OrderStatus.PAID
            
            await send_payment_confirmation(order.user.email, order)
            logger.info(f"Paiement réussi: {order_id}")
            
            return PaymentResult(success=True, transaction_id=transaction.id)
        else:
            transaction.status = TransactionStatus.FAILED
            transaction.error_message = external_result.error
            order.status = OrderStatus.PAYMENT_FAILED
            
            logger.error(f"Paiement échoué: {order_id} - {external_result.error}")
            
            return PaymentResult(success=False, error=external_result.error)
            
    except PaymentGatewayError as e:
        transaction.status = TransactionStatus.ERROR
        order.status = OrderStatus.PAYMENT_FAILED
        logger.error(f"Erreur gateway paiement: {order_id} - {e}")
        raise
    
    finally:
        await db.commit()
''',
        "description": "Traitement des paiements avec gestion des erreurs et notifications"
    },
    {
        "id": "log_analyzer_1",
        "name": "analyze_error_logs",
        "type": "function",
        "language": "python",
        "file_path": "app/services/monitoring/log_analyzer.py",
        "code": '''
async def analyze_error_logs(time_range: TimeRange) -> LogAnalysisResult:
    """
    Analyse les logs d'erreur pour détecter des patterns.
    
    Détection de patterns:
    - Erreurs répétées (même message > 10 fois)
    - Pics d'erreurs (> 100 erreurs/minute)
    - Erreurs critiques (niveau CRITICAL)
    - Erreurs de timeout (connexion DB, API externe)
    - Erreurs d'authentification (tentatives échouées)
    
    Returns:
        LogAnalysisResult avec les patterns détectés et recommandations
    """
    logs = await fetch_logs(
        level=["ERROR", "CRITICAL"],
        start_time=time_range.start,
        end_time=time_range.end
    )
    
    patterns = []
    
    # Grouper par message d'erreur
    error_groups = group_by_message(logs)
    
    for message, occurrences in error_groups.items():
        if len(occurrences) > 10:
            patterns.append(Pattern(
                type="REPEATED_ERROR",
                message=message,
                count=len(occurrences),
                severity="HIGH",
                recommendation="Investiguer la cause racine de cette erreur récurrente"
            ))
    
    # Détecter les pics
    error_rate = calculate_error_rate(logs, interval="1m")
    for timestamp, rate in error_rate.items():
        if rate > 100:
            patterns.append(Pattern(
                type="ERROR_SPIKE",
                timestamp=timestamp,
                rate=rate,
                severity="CRITICAL",
                recommendation="Vérifier les déploiements ou changements récents"
            ))
    
    # Erreurs critiques
    critical_errors = [log for log in logs if log.level == "CRITICAL"]
    if critical_errors:
        patterns.append(Pattern(
            type="CRITICAL_ERRORS",
            count=len(critical_errors),
            severity="CRITICAL",
            recommendation="Action immédiate requise - vérifier les services critiques"
        ))
    
    return LogAnalysisResult(
        total_errors=len(logs),
        patterns=patterns,
        time_range=time_range
    )
''',
        "description": "Analyse des logs d'erreur avec détection de patterns et recommandations"
    }
]


async def inject_to_qdrant():
    """Injecter les exemples dans Qdrant (recherche vectorielle)"""
    print("\n📊 Injection dans Qdrant (vecteurs)...")
    
    try:
        vector_service = VectorService(
            qdrant_host=settings.QDRANT_HOST,
            qdrant_port=settings.QDRANT_PORT
        )
        
        if not vector_service.is_available():
            print("   ⚠️  Qdrant non disponible - skip")
            return False
        
        for sample in SAMPLE_CODE:
            success = await vector_service.add_code_snippet(
                code=sample["code"],
                metadata={
                    "name": sample["name"],
                    "type": sample["type"],
                    "language": sample["language"],
                    "file_path": sample["file_path"],
                    "description": sample["description"]
                },
                snippet_id=sample["id"]
            )
            if success:
                print(f"   ✅ {sample['name']} ajouté à Qdrant")
            else:
                print(f"   ❌ Erreur: {sample['name']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur Qdrant: {e}")
        return False


async def inject_to_neo4j():
    """Injecter les exemples dans Neo4j (graphe de connaissances)"""
    print("\n🔗 Injection dans Neo4j (graphe)...")
    
    try:
        graph_service = GraphService(
            uri=settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        
        if not graph_service.is_available():
            print("   ⚠️  Neo4j non disponible - skip")
            return False
        
        for sample in SAMPLE_CODE:
            success = await graph_service.add_code_node(
                node_id=sample["id"],
                node_type=sample["type"],
                name=sample["name"],
                content=sample["code"],
                metadata={
                    "language": sample["language"],
                    "file_path": sample["file_path"],
                    "description": sample["description"]
                }
            )
            if success:
                print(f"   ✅ {sample['name']} ajouté à Neo4j")
            else:
                print(f"   ❌ Erreur: {sample['name']}")
        
        # Créer quelques relations
        relations = [
            ("admin_check_1", "user_service_1", "USES"),
            ("order_service_1", "user_service_1", "USES"),
            ("payment_processor_1", "order_service_1", "PROCESSES"),
        ]
        
        print("\n   📎 Création des relations...")
        for from_id, to_id, rel_type in relations:
            await graph_service.add_relationship(from_id, to_id, rel_type)
            print(f"   ✅ {from_id} --[{rel_type}]--> {to_id}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur Neo4j: {e}")
        return False


async def main():
    print("=" * 60)
    print("🚀 INJECTION DE DONNÉES D'EXEMPLE")
    print("=" * 60)
    print(f"\n📁 {len(SAMPLE_CODE)} fichiers de code à injecter")
    
    # Injection Qdrant
    qdrant_ok = await inject_to_qdrant()
    
    # Injection Neo4j
    neo4j_ok = await inject_to_neo4j()
    
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    print(f"   Qdrant (vecteurs): {'✅ OK' if qdrant_ok else '❌ Échec'}")
    print(f"   Neo4j (graphe):    {'✅ OK' if neo4j_ok else '❌ Échec'}")
    
    if qdrant_ok or neo4j_ok:
        print("\n🎉 Données injectées ! Testez maintenant le chatbot avec:")
        print('   "Que se passe-t-il quand un utilisateur non vérifié tente de commander ?"')
        print('   "Comment fonctionne l\'authentification ?"')
        print('   "Quelles sont les règles pour accéder à l\'admin ?"')
    else:
        print("\n⚠️  Aucune donnée injectée - vérifiez que Qdrant et Neo4j sont lancés")


if __name__ == "__main__":
    asyncio.run(main())
