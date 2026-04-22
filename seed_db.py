"""
Peuple la base de données avec des données de test.
Usage : python seed_db.py
"""
from app import create_app
from models import (db, Utilisateur, Etudiant, Entreprise, Admin,
                    Offre, Candidature, Competence, Feedback, Convention, Notification)
from datetime import date, timedelta

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    # --- Compétences ---
    competences_data = [
        ('Finance', 'Finance'), ('Excel', 'Bureautique'), ('Reporting', 'Analyse'),
        ('ERP', 'Logiciel'), ('Power BI', 'Analyse'), ('Analyse financière', 'Finance'),
        ('Comptabilité', 'Finance'), ('Audit', 'Finance'), ('SAP', 'Logiciel'),
        ('Python', 'Informatique'), ('SQL', 'Informatique'), ('Marketing digital', 'Marketing'),
        ('SEO', 'Marketing'), ('Gestion de projet', 'Management'), ('Logistique', 'Logistique'),
        ('Supply chain', 'Logistique'), ('Risk management', 'Finance'), ('Bloomberg', 'Finance'),
        ('Modélisation financière', 'Finance'), ('RH', 'Management'),
    ]
    comps = {}
    for nom, cat in competences_data:
        c = Competence(nom=nom, categorie=cat)
        db.session.add(c)
        comps[nom] = c
    db.session.flush()

    # --- Admin ---
    u_admin = Utilisateur(email='admin@stagelink.ma', role='ADMIN')
    u_admin.set_password('admin123')
    db.session.add(u_admin)
    db.session.flush()
    admin = Admin(utilisateur_id=u_admin.id, nom='Administrateur StageLink', niveau_acces=1)
    db.session.add(admin)

    # --- Entreprises ---
    def make_entreprise(email, mdp, nom, secteur, ville, taille, desc, rc, verifie=True):
        u = Utilisateur(email=email, role='ENTREPRISE')
        u.set_password(mdp)
        db.session.add(u)
        db.session.flush()
        e = Entreprise(utilisateur_id=u.id, nom=nom, secteur=secteur,
                       ville=ville, taille=taille, description=desc,
                       rc=rc, est_verifiee=verifie)
        db.session.add(e)
        db.session.flush()
        return e

    cih = make_entreprise('cih@stagelink.ma', 'cih123', 'CIH Bank', 'Banque & Finance',
        'Marrakech', 'GE', 'CIH Bank est une banque marocaine de référence, proposant des services bancaires innovants.', 'RC-CIH-001')
    marjane = make_entreprise('marjane@stagelink.ma', 'marjane123', 'Marjane Holding', 'Grande distribution',
        'Marrakech', 'GE', 'Leader de la grande distribution au Maroc avec plus de 30 hypermarchés.', 'RC-MJ-002')
    ocp = make_entreprise('ocp@stagelink.ma', 'ocp123', 'OCP Group', 'Industrie minière',
        'Khouribga', 'GE', 'OCP Group est le leader mondial de la production de phosphate.', 'RC-OCP-003')
    atw = make_entreprise('atw@stagelink.ma', 'atw123', 'Attijariwafa Bank', 'Banque & Finance',
        'Casablanca', 'GE', 'Premier groupe bancaire et financier du Maghreb.', 'RC-ATW-004')
    bmce = make_entreprise('bmce@stagelink.ma', 'bmce123', 'BMCE Bank', 'Banque & Finance',
        'Casablanca', 'GE', 'Banque marocaine du commerce extérieur, présente dans 20 pays.', 'RC-BMC-005')

    # Entreprises en attente de vérification
    sopriam = make_entreprise('sopriam@stagelink.ma', 'sopriam123', 'Sopriam SA', 'Automobile',
        'Casablanca', 'GE', 'Importateur officiel de véhicules Peugeot au Maroc.', 'RC-SPR-006', verifie=False)
    cdanone = make_entreprise('danone@stagelink.ma', 'danone123', 'Centrale Danone', 'Agroalimentaire',
        'Casablanca', 'GE', 'Leader des produits laitiers frais au Maroc.', 'RC-CD-007', verifie=False)
    totalenergies = make_entreprise('total@stagelink.ma', 'total123', 'TotalEnergies Maroc', 'Énergie',
        'Rabat', 'GE', 'Acteur majeur de l\'énergie au Maroc.', 'RC-TE-008', verifie=False)
    pharma5 = make_entreprise('pharma5@stagelink.ma', 'pharma123', 'Pharma 5', 'Pharmacie',
        'Rabat', 'PME', 'Laboratoire pharmaceutique marocain innovant.', 'RC-P5-009', verifie=False)

    # --- Étudiants ---
    def make_etudiant(email, mdp, nom, univ, filiere, niveau, ville, comps_list):
        u = Utilisateur(email=email, role='ETUDIANT')
        u.set_password(mdp)
        db.session.add(u)
        db.session.flush()
        e = Etudiant(utilisateur_id=u.id, nom_complet=nom, universite=univ,
                     filiere=filiere, niveau=niveau, ville=ville)
        e.competences = [comps[c] for c in comps_list if c in comps]
        db.session.add(e)
        db.session.flush()
        return e

    othmane = make_etudiant('othmane@stagelink.ma', 'othmane123',
        'Othmane Benali', 'ENCG Marrakech', 'Finance', 'S6', 'Marrakech',
        ['Finance', 'Excel', 'Reporting', 'Analyse financière', 'Comptabilité'])

    hamza = make_etudiant('hamza@stagelink.ma', 'hamza123',
        'Hamza Khalil', 'FSJES Marrakech', 'Finance', 'M1', 'Marrakech',
        ['Finance', 'Excel', 'Comptabilité', 'Audit', 'Reporting'])

    sara = make_etudiant('sara@stagelink.ma', 'sara123',
        'Sara Meskine', 'ENCG Agadir', 'Gestion', 'L3', 'Agadir',
        ['Finance', 'Comptabilité', 'Gestion de projet', 'Excel'])

    amine = make_etudiant('amine@stagelink.ma', 'amine123',
        'Amine Zeroual', 'ISCAE', 'Finance', 'S6', 'Casablanca',
        ['Finance', 'Excel', 'Reporting', 'Risk management'])

    nadia = make_etudiant('nadia@stagelink.ma', 'nadia123',
        'Nadia Benchekroun', 'ENCG Casablanca', 'Marketing', 'M1', 'Casablanca',
        ['Marketing digital', 'SEO', 'Gestion de projet', 'Excel'])

    # --- Offres ---
    def make_offre(entreprise, titre, desc, missions, duree, ville, filiere, debut, comps_list):
        o = Offre(entreprise_id=entreprise.id, titre=titre, description=desc,
                  missions=missions, duree=duree, ville=ville,
                  filiere_requise=filiere, statut='ACTIVE', date_debut=debut)
        o.competences = [comps[c] for c in comps_list if c in comps]
        db.session.add(o)
        db.session.flush()
        return o

    offre1 = make_offre(cih, 'Stage contrôle de gestion',
        'Dans le cadre du développement de son département contrôle de gestion, CIH Bank recrute un(e) stagiaire pour rejoindre l\'équipe basée à Marrakech. Vous serez accompagné(e) par un encadrant expérimenté tout au long de votre stage.',
        'Participation à l\'élaboration des tableaux de bord mensuels\nAnalyse des écarts budgétaires et préparation des rapports\nContribution au suivi des indicateurs de performance (KPIs)\nAide à la préparation des clôtures trimestrielles',
        2, 'Marrakech', 'Finance', 'Dès mars 2025',
        ['Finance', 'Excel', 'Reporting', 'ERP', 'Power BI', 'Analyse financière'])

    offre2 = make_offre(cih, 'Analyse financière',
        'CIH Bank recherche un(e) stagiaire pour renforcer son équipe d\'analyse financière à Marrakech.',
        'Analyse des états financiers des clients\nPréparer des notes de synthèse\nSuivi des ratios financiers\nSupport à l\'équipe crédit',
        3, 'Marrakech', 'Finance', 'Dès avril 2025',
        ['Finance', 'Analyse financière', 'Excel', 'Reporting'])

    offre3 = make_offre(cih, 'Gestion trésorerie',
        'Stage dans le département trésorerie de CIH Bank Marrakech.',
        'Suivi des flux de trésorerie\nRapprochements bancaires\nPrévisions de trésorerie\nSupport gestion du risque de liquidité',
        2, 'Marrakech', 'Finance', 'Dès mai 2025',
        ['Finance', 'Excel', 'Comptabilité'])

    offre4 = make_offre(marjane, 'Audit interne et comptabilité',
        'Marjane Holding recrute un(e) stagiaire pour son département audit interne.',
        'Participation aux missions d\'audit interne\nRevue des procédures comptables\nPréparation des rapports d\'audit\nSupport à la clôture annuelle',
        3, 'Marrakech', 'Finance', 'Dès avril 2025',
        ['Finance', 'Comptabilité', 'Audit', 'SAP', 'Excel'])

    offre5 = make_offre(ocp, 'Contrôle de gestion industriel',
        'OCP Group propose un stage en contrôle de gestion au sein de ses installations à Khouribga.',
        'Analyse des coûts de production\nSuivi du budget d\'exploitation\nTableaux de bord industriels\nAmélioration des processus de reporting',
        2, 'Khouribga', 'Finance', 'Dès mai 2025',
        ['Finance', 'Power BI', 'Excel', 'Reporting', 'ERP'])

    offre6 = make_offre(atw, 'Analyse financière et risques',
        'Attijariwafa Bank recherche un(e) stagiaire en analyse financière et gestion des risques.',
        'Analyse du risque de crédit\nModélisation financière\nPréparer des rapports de risque\nSupport équipe Risk Management',
        3, 'Casablanca', 'Finance', 'Dès juin 2025',
        ['Finance', 'Risk management', 'Bloomberg', 'Modélisation financière', 'Excel'])

    offre7 = make_offre(bmce, 'Marketing digital',
        'BMCE Bank propose un stage en marketing digital au sein de sa direction communication.',
        'Gestion des réseaux sociaux\nCréation de contenus digitaux\nAnalyse des campagnes SEO/SEM\nReporting des performances',
        2, 'Casablanca', 'Marketing', 'Dès mars 2025',
        ['Marketing digital', 'SEO', 'Excel', 'Gestion de projet'])

    offre8 = make_offre(marjane, 'Logistique et supply chain',
        'Stage au sein de la direction logistique de Marjane Holding Marrakech.',
        'Optimisation des flux logistiques\nGestion des stocks\nRelations fournisseurs\nTableaux de bord supply chain',
        3, 'Marrakech', 'Gestion', 'Dès avril 2025',
        ['Logistique', 'Supply chain', 'Excel', 'Gestion de projet'])

    # --- Candidatures ---
    def make_candidature(etudiant, offre, statut, score, lettre=None, jours_avant=0):
        from services.matching import generer_lettre_motivation
        c = Candidature(
            etudiant_id=etudiant.id,
            offre_id=offre.id,
            statut=statut,
            score_matching=score,
            lettre_motivation=lettre or generer_lettre_motivation(etudiant, offre),
            date_postulation=date.today() - timedelta(days=jours_avant)
        )
        db.session.add(c)
        db.session.flush()
        return c

    c1 = make_candidature(othmane, offre1, 'EN_ATTENTE', 92.0, jours_avant=2)
    c2 = make_candidature(othmane, offre4, 'ACCEPTEE', 78.0, jours_avant=10)
    c3 = make_candidature(othmane, offre5, 'EN_ATTENTE', 61.0, jours_avant=7)
    c4 = make_candidature(othmane, offre6, 'REFUSEE', 54.0, jours_avant=15)

    c5 = make_candidature(hamza, offre1, 'EN_ATTENTE', 85.0, jours_avant=3)
    c6 = make_candidature(hamza, offre2, 'EN_ATTENTE', 80.0, jours_avant=5)

    c7 = make_candidature(sara, offre1, 'EN_ATTENTE', 73.0, jours_avant=4)
    c8 = make_candidature(sara, offre8, 'ACCEPTEE', 82.0, jours_avant=8)

    c9 = make_candidature(amine, offre1, 'EN_ATTENTE', 68.0, jours_avant=6)
    c10 = make_candidature(amine, offre6, 'REFUSEE', 75.0, jours_avant=12)

    c11 = make_candidature(nadia, offre7, 'ACCEPTEE', 88.0, jours_avant=9)

    # --- Feedbacks (pour les refusées) ---
    fb1 = Feedback(candidature_id=c4.id,
        commentaire='Votre profil est intéressant mais nous recherchons un candidat avec une expérience en Bloomberg et en modélisation financière.',
        note=3, date=date.today() - timedelta(days=13))
    db.session.add(fb1)

    # c10 (Amine refusé) sans feedback — alerte admin
    # c9 (Amine EN_ATTENTE chez CIH) sans feedback — pour demo alerte manquant

    # --- Conventions pour les acceptées ---
    conv1 = Convention(candidature_id=c2.id,
        date_debut=date.today() + timedelta(days=10),
        date_fin=date.today() + timedelta(days=100),
        pdf_path='', date_generation=date.today())
    db.session.add(conv1)
    db.session.flush()

    # Génère le PDF de convention pour c2
    try:
        from services.pdf_gen import generer_convention_pdf
        import os
        base_dir = os.path.abspath(os.path.dirname(__file__))
        path = generer_convention_pdf(conv1, c2, othmane, marjane, offre4, base_dir)
        conv1.pdf_path = path
    except Exception as e:
        print(f'PDF convention skipped: {e}')

    # --- Notifications ---
    def notif(utilisateur, message, type_='info'):
        n = Notification(utilisateur_id=utilisateur.id, message=message, type=type_)
        db.session.add(n)

    notif(othmane.utilisateur, 'Votre candidature chez Marjane Holding a été acceptée ! Téléchargez votre convention.', 'success')
    notif(othmane.utilisateur, 'Attijariwafa Bank a refusé votre candidature avec un feedback.', 'info')
    notif(cih.utilisateur, 'Nouvelle candidature reçue pour le stage contrôle de gestion.', 'info')
    notif(cih.utilisateur, 'Feedback manquant pour 2 candidats refusés.', 'warning')
    notif(u_admin, '4 entreprises en attente de vérification.', 'warning')
    notif(u_admin, '2 signalements en attente de modération.', 'warning')

    db.session.commit()
    print("Base de données initialisée avec succès !")
    print("Admin : admin@stagelink.ma / admin123")
    print("Étudiant : othmane@stagelink.ma / othmane123")
    print("Entreprise : cih@stagelink.ma / cih123")
