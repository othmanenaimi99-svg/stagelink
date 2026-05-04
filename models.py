from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

db = SQLAlchemy()

etudiant_competence = db.Table('etudiant_competence',
    db.Column('etudiant_id', db.Integer, db.ForeignKey('etudiant.id'), primary_key=True),
    db.Column('competence_id', db.Integer, db.ForeignKey('competence.id'), primary_key=True)
)

offre_competence = db.Table('offre_competence',
    db.Column('offre_id', db.Integer, db.ForeignKey('offre.id'), primary_key=True),
    db.Column('competence_id', db.Integer, db.ForeignKey('competence.id'), primary_key=True)
)


class Utilisateur(UserMixin, db.Model):
    __tablename__ = 'utilisateur'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    mot_de_passe = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    actif = db.Column(db.Boolean, default=True)
    email_verifie = db.Column(db.Boolean, default=False)

    etudiant = db.relationship('Etudiant', backref='utilisateur', uselist=False, cascade='all, delete-orphan')
    entreprise = db.relationship('Entreprise', backref='utilisateur', uselist=False, cascade='all, delete-orphan')
    admin = db.relationship('Admin', backref='utilisateur', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='utilisateur', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.mot_de_passe = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.mot_de_passe, password)

    @property
    def is_active(self):
        return self.actif

    @property
    def nom(self):
        if self.etudiant:
            return self.etudiant.nom_complet
        if self.entreprise:
            return self.entreprise.nom
        if self.admin:
            return self.admin.nom
        return self.email


class Etudiant(db.Model):
    __tablename__ = 'etudiant'
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    nom_complet = db.Column(db.String(150), nullable=False)
    universite = db.Column(db.String(150))
    filiere = db.Column(db.String(100))
    niveau = db.Column(db.String(20))
    ville = db.Column(db.String(100))
    cv_path = db.Column(db.String(256))
    date_inscription = db.Column(db.Date, default=date.today)

    competences = db.relationship('Competence', secondary=etudiant_competence, backref='etudiants')
    candidatures = db.relationship('Candidature', backref='etudiant', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def initiales(self):
        parts = self.nom_complet.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return self.nom_complet[:2].upper()

    @property
    def completion_profil(self):
        score = 0
        if self.nom_complet: score += 20
        if self.universite: score += 15
        if self.filiere: score += 15
        if self.niveau: score += 10
        if self.ville: score += 10
        if self.cv_path: score += 15
        if self.competences: score += 15
        return score


class Entreprise(db.Model):
    __tablename__ = 'entreprise'
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    nom = db.Column(db.String(150), nullable=False)
    secteur = db.Column(db.String(100))
    ville = db.Column(db.String(100))
    taille = db.Column(db.String(20))
    description = db.Column(db.Text)
    rc = db.Column(db.String(100))
    est_verifiee = db.Column(db.Boolean, default=False)
    date_inscription = db.Column(db.Date, default=date.today)

    offres = db.relationship('Offre', backref='entreprise', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def initiales(self):
        words = self.nom.split()
        if len(words) >= 2:
            return (words[0][0] + words[1][0]).upper()
        return self.nom[:3].upper()

    @property
    def nb_candidatures_en_attente(self):
        from sqlalchemy import text
        count = 0
        for offre in self.offres:
            count += offre.candidatures.filter_by(statut='EN_ATTENTE').count()
        return count

    @property
    def verifie(self):
        return self.est_verifiee

    @property
    def taux_acceptation(self):
        total = 0
        acceptees = 0
        for offre in self.offres:
            for c in offre.candidatures:
                if c.statut in ('ACCEPTEE', 'REFUSEE'):
                    total += 1
                    if c.statut == 'ACCEPTEE':
                        acceptees += 1
        if total == 0:
            return 0
        return round(acceptees / total * 100)


class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    nom = db.Column(db.String(150), nullable=False)
    niveau_acces = db.Column(db.Integer, default=1)


class Offre(db.Model):
    __tablename__ = 'offre'
    id = db.Column(db.Integer, primary_key=True)
    entreprise_id = db.Column(db.Integer, db.ForeignKey('entreprise.id'), nullable=False)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    missions = db.Column(db.Text)
    duree = db.Column(db.Integer)
    ville = db.Column(db.String(100))
    filiere_requise = db.Column(db.String(100))
    remuneration = db.Column(db.Integer, nullable=True)
    statut = db.Column(db.String(20), default='ACTIVE')
    date_publication = db.Column(db.Date, default=date.today)
    date_debut = db.Column(db.String(50))

    competences = db.relationship('Competence', secondary=offre_competence, backref='offres')
    candidatures = db.relationship('Candidature', backref='offre', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def active(self):
        return self.statut == 'ACTIVE'

    @property
    def filieres_requises(self):
        return [self.filiere_requise] if self.filiere_requise else []

    @property
    def nb_candidatures(self):
        return self.candidatures.count()

    @property
    def missions_list(self):
        if not self.missions:
            return []
        return [m.strip() for m in self.missions.split('\n') if m.strip()]


class Candidature(db.Model):
    __tablename__ = 'candidature'
    id = db.Column(db.Integer, primary_key=True)
    etudiant_id = db.Column(db.Integer, db.ForeignKey('etudiant.id'), nullable=False)
    offre_id = db.Column(db.Integer, db.ForeignKey('offre.id'), nullable=False)
    statut = db.Column(db.String(20), default='EN_ATTENTE')
    lettre_motivation = db.Column(db.Text)
    score_matching = db.Column(db.Float, default=0.0)
    date_postulation = db.Column(db.Date, default=date.today)

    feedback = db.relationship('Feedback', backref='candidature', uselist=False, cascade='all, delete-orphan')
    convention = db.relationship('Convention', backref='candidature', uselist=False, cascade='all, delete-orphan')

    @property
    def statut_label(self):
        labels = {'EN_ATTENTE': 'En attente', 'ACCEPTEE': 'Acceptée', 'REFUSEE': 'Refusée'}
        return labels.get(self.statut, self.statut)

    @property
    def statut_class(self):
        classes = {'EN_ATTENTE': 'badge-attente', 'ACCEPTEE': 'badge-acceptee', 'REFUSEE': 'badge-refusee'}
        return classes.get(self.statut, '')


class Competence(db.Model):
    __tablename__ = 'competence'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    categorie = db.Column(db.String(100))


class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    candidature_id = db.Column(db.Integer, db.ForeignKey('candidature.id'), nullable=False)
    commentaire = db.Column(db.Text, nullable=False)
    note = db.Column(db.Integer)
    date = db.Column(db.Date, default=date.today)


class Convention(db.Model):
    __tablename__ = 'convention'
    id = db.Column(db.Integer, primary_key=True)
    candidature_id = db.Column(db.Integer, db.ForeignKey('candidature.id'), nullable=False)
    date_debut = db.Column(db.Date)
    date_fin = db.Column(db.Date)
    pdf_path = db.Column(db.String(256))
    date_generation = db.Column(db.Date, default=date.today)


class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    utilisateur_id = db.Column(db.Integer, db.ForeignKey('utilisateur.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    est_lue = db.Column(db.Boolean, default=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    type = db.Column(db.String(50), default='info')
