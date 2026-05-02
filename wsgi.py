import os
from app import create_app
from models import db, Utilisateur, Admin

app = create_app()

with app.app_context():
    db.create_all()

    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@stagelink.ma')
    admin_password = os.environ.get('ADMIN_PASSWORD')

    if admin_password:
        if os.environ.get('FORCE_RESET', '').lower() == 'true':
            db.drop_all()
            db.create_all()

        existing = Utilisateur.query.filter_by(email=admin_email).first()
        if existing:
            existing.set_password(admin_password)
            existing.actif = True
            db.session.commit()
        else:
            u = Utilisateur(email=admin_email, role='ADMIN', actif=True)
            u.set_password(admin_password)
            db.session.add(u)
            db.session.flush()
            db.session.add(Admin(utilisateur_id=u.id, nom='Administrateur StageLink', niveau_acces=1))
            db.session.commit()
