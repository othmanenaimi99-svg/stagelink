"""
Réinitialise complètement la base de données et recrée le compte admin.
ATTENTION : supprime toutes les données existantes.
Usage : python reset_db.py
Ne jamais exécuter automatiquement au démarrage.
"""
import os
from app import create_app
from models import db, Utilisateur, Admin

confirm = input("⚠️  Ceci va supprimer TOUTES les données. Confirmer ? (oui/non) : ")
if confirm.strip().lower() != 'oui':
    print("Annulé.")
    exit(0)

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()
    print("Base de données réinitialisée.")

    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@stagelink.ma')
    admin_password = os.environ.get('ADMIN_PASSWORD')

    if not admin_password:
        print("ERREUR : variable d'environnement ADMIN_PASSWORD non définie.")
        exit(1)

    u = Utilisateur(email=admin_email, role='ADMIN')
    u.set_password(admin_password)
    db.session.add(u)
    db.session.flush()
    admin = Admin(utilisateur_id=u.id, nom='Administrateur StageLink', niveau_acces=1)
    db.session.add(admin)
    db.session.commit()
    print(f"Admin créé : {admin_email}")
