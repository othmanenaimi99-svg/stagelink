import os
from app import create_app
from models import db, Utilisateur, Admin

app = create_app()

with app.app_context():
    db.create_all()

    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@stagelink.ma')
    admin_password = os.environ.get('ADMIN_PASSWORD')

    print(f"[WSGI] ADMIN_EMAIL={admin_email!r}")
    print(f"[WSGI] ADMIN_PASSWORD set={bool(admin_password)}")

    if admin_password:
        if os.environ.get('FORCE_RESET', '').lower() == 'true':
            print("[WSGI] FORCE_RESET: drop all tables")
            db.drop_all()
            db.create_all()

        existing = Utilisateur.query.filter_by(email=admin_email).first()
        if existing:
            existing.set_password(admin_password)
            existing.actif = True
            db.session.commit()
            ok = existing.check_password(admin_password)
            print(f"[WSGI] Admin password updated. check={ok}")
        else:
            u = Utilisateur(email=admin_email, role='ADMIN', actif=True)
            u.set_password(admin_password)
            db.session.add(u)
            db.session.flush()
            db.session.add(Admin(utilisateur_id=u.id, nom='Administrateur StageLink', niveau_acces=1))
            db.session.commit()
            ok = u.check_password(admin_password)
            print(f"[WSGI] Admin created. check={ok}")
