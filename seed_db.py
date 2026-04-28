"""
Initialise la base de données avec uniquement le compte admin.
Usage : python seed_db.py
"""
import os
from app import create_app
from models import db, Utilisateur, Admin

app = create_app()

with app.app_context():
    db.create_all()

    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@stagelink.ma')
    admin_password = os.environ.get('ADMIN_PASSWORD')

    if not admin_password:
        print("ERREUR : variable d'environnement ADMIN_PASSWORD non définie.")
        exit(1)

    if Utilisateur.query.filter_by(email=admin_email).first():
        print(f"Admin déjà existant : {admin_email}")
    else:
        u = Utilisateur(email=admin_email, role='ADMIN')
        u.set_password(admin_password)
        db.session.add(u)
        db.session.flush()
        admin = Admin(utilisateur_id=u.id, nom='Administrateur StageLink', niveau_acces=1)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin créé : {admin_email}")
