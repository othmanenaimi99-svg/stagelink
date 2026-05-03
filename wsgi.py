import os
from app import create_app
from models import db, Utilisateur, Admin, Competence

app = create_app()

COMPETENCES = [
    ('Finance', 'Finance'), ('Excel', 'Bureautique'), ('Reporting', 'Analyse'),
    ('ERP', 'Logiciel'), ('Power BI', 'Analyse'), ('Analyse financière', 'Finance'),
    ('Comptabilité', 'Finance'), ('Audit', 'Finance'), ('SAP', 'Logiciel'),
    ('Python', 'Informatique'), ('SQL', 'Informatique'), ('Marketing digital', 'Marketing'),
    ('SEO', 'Marketing'), ('Gestion de projet', 'Management'), ('Logistique', 'Logistique'),
    ('Supply chain', 'Logistique'), ('Risk management', 'Finance'), ('Bloomberg', 'Finance'),
    ('Modélisation financière', 'Finance'), ('RH', 'Management'),
    ('Java', 'Informatique'), ('JavaScript', 'Informatique'), ('React', 'Informatique'),
    ('Communication', 'Management'), ('Anglais', 'Langue'), ('Français', 'Langue'),
]

with app.app_context():
    db.create_all()

    # Créer les compétences si elles n'existent pas
    for nom, categorie in COMPETENCES:
        if not Competence.query.filter_by(nom=nom).first():
            db.session.add(Competence(nom=nom, categorie=categorie))
    db.session.commit()

    # Créer ou mettre à jour le compte admin
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@stagelink.ma').strip()
    admin_password = os.environ.get('ADMIN_PASSWORD', '').strip()

    if admin_password:
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
