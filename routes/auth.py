import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Utilisateur, Etudiant, Entreprise, Competence

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = Utilisateur.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.actif:
            login_user(user)
            return _redirect_by_role(user)
        flash("Email ou mot de passe incorrect.", 'error')
    return render_template('auth/login.html', tab='login', step=0)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('register_data', None)
    return redirect(url_for('index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register_step1():
    if current_user.is_authenticated:
        return _redirect_by_role(current_user)
    if request.method == 'POST':
        role = request.form.get('role', '')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        nom = request.form.get('nom', '').strip()

        if not all([role, email, password, nom]):
            flash("Tous les champs sont obligatoires.", 'error')
            return render_template('auth/login.html', tab='register', step=1)
        if role not in ('ETUDIANT', 'ENTREPRISE'):
            flash("Rôle invalide.", 'error')
            return render_template('auth/login.html', tab='register', step=1)
        if Utilisateur.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé. Veuillez vous connecter.", 'error')
            return render_template('auth/login.html', tab='register', step=1)
        if len(password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", 'error')
            return render_template('auth/login.html', tab='register', step=1)

        session['register_data'] = {'role': role, 'email': email, 'password': password, 'nom': nom}
        return redirect(url_for('auth.register_step2'))
    return render_template('auth/login.html', tab='register', step=1)


@auth_bp.route('/register/2', methods=['GET', 'POST'])
def register_step2():
    if 'register_data' not in session:
        return redirect(url_for('auth.register_step1'))
    data = session['register_data']

    if request.method == 'POST':
        if data['role'] == 'ETUDIANT':
            data.update({
                'universite': request.form.get('universite', '').strip(),
                'filiere': request.form.get('filiere', '').strip(),
                'niveau': request.form.get('niveau', '').strip(),
                'ville': request.form.get('ville', '').strip(),
            })
        else:
            data.update({
                'secteur': request.form.get('secteur', '').strip(),
                'ville': request.form.get('ville', '').strip(),
                'taille': request.form.get('taille', '').strip(),
                'rc': request.form.get('rc', '').strip(),
            })
        session['register_data'] = data
        return redirect(url_for('auth.register_step3'))
    return render_template('auth/login.html', tab='register', step=2, data=data)


@auth_bp.route('/register/3', methods=['GET', 'POST'])
def register_step3():
    if 'register_data' not in session:
        return redirect(url_for('auth.register_step1'))
    data = session['register_data']

    if request.method == 'POST':
        if data['role'] == 'ETUDIANT':
            competences_ids = request.form.getlist('competences')
            data['competences'] = competences_ids
        else:
            data['description'] = request.form.get('description', '').strip()
        session['register_data'] = data
        return redirect(url_for('auth.register_step4'))
    competences = Competence.query.order_by(Competence.categorie, Competence.nom).all()
    return render_template('auth/login.html', tab='register', step=3, data=data, competences=competences)


@auth_bp.route('/register/4', methods=['GET', 'POST'])
def register_step4():
    if 'register_data' not in session:
        return redirect(url_for('auth.register_step1'))
    data = session['register_data']

    if request.method == 'POST':
        from flask import current_app
        u = Utilisateur(email=data['email'], role=data['role'])
        u.set_password(data['password'])
        db.session.add(u)
        db.session.flush()

        if data['role'] == 'ETUDIANT':
            cv_path = None
            cv_file = request.files.get('cv')
            if cv_file and cv_file.filename and allowed_file(cv_file.filename):
                try:
                    import cloudinary
                    import cloudinary.uploader
                    cloudinary.config(
                        cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
                        api_key=current_app.config['CLOUDINARY_API_KEY'],
                        api_secret=current_app.config['CLOUDINARY_API_SECRET']
                    )
                    result = cloudinary.uploader.upload(
                        cv_file,
                        resource_type='raw',
                        folder='stagelink/cvs',
                        public_id=f'cv_{u.id}',
                        overwrite=True
                    )
                    cv_path = result['secure_url']
                except Exception:
                    cv_path = None

            etudiant = Etudiant(
                utilisateur_id=u.id,
                nom_complet=data['nom'],
                universite=data.get('universite'),
                filiere=data.get('filiere'),
                niveau=data.get('niveau'),
                ville=data.get('ville'),
                cv_path=cv_path
            )
            comps = Competence.query.filter(
                Competence.id.in_([int(x) for x in data.get('competences', [])])
            ).all()
            etudiant.competences = comps
            db.session.add(etudiant)

        else:
            entreprise = Entreprise(
                utilisateur_id=u.id,
                nom=data['nom'],
                secteur=data.get('secteur'),
                ville=data.get('ville'),
                taille=data.get('taille'),
                description=data.get('description'),
                rc=data.get('rc'),
                est_verifiee=False
            )
            db.session.add(entreprise)

        db.session.commit()
        session.pop('register_data', None)

        from services.email_service import generate_verification_token, send_verification_email
        token = generate_verification_token(u.email)
        verification_url = url_for('auth.verify_email', token=token, _external=True)
        send_verification_email(u.email, verification_url)

        session['pending_verify_email'] = u.email
        return redirect(url_for('auth.check_email'))

    return render_template('auth/login.html', tab='register', step=4, data=data)


@auth_bp.route('/check-email')
def check_email():
    email = session.get('pending_verify_email', '')
    return render_template('auth/check_email.html', email=email)


@auth_bp.route('/verify/<token>')
def verify_email(token):
    from services.email_service import verify_token
    email = verify_token(token)
    if not email:
        flash("Lien de vérification invalide ou expiré.", 'error')
        return redirect(url_for('auth.login'))
    user = Utilisateur.query.filter_by(email=email).first()
    if not user:
        flash("Compte introuvable.", 'error')
        return redirect(url_for('auth.login'))
    user.email_verifie = True
    db.session.commit()
    login_user(user)
    flash("Email vérifié ! Bienvenue sur StageLink MA.", 'success')
    return _redirect_by_role(user)


@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    email = request.form.get('email', '').strip()
    user = Utilisateur.query.filter_by(email=email).first()
    if user and not user.email_verifie:
        from services.email_service import generate_verification_token, send_verification_email
        token = generate_verification_token(user.email)
        verification_url = url_for('auth.verify_email', token=token, _external=True)
        send_verification_email(user.email, verification_url)
    flash("Email de vérification renvoyé.", 'success')
    return redirect(url_for('auth.check_email'))


def _redirect_by_role(user):
    if user.role == 'ETUDIANT':
        return redirect(url_for('etudiant.dashboard'))
    elif user.role == 'ENTREPRISE':
        return redirect(url_for('entreprise.dashboard'))
    elif user.role == 'ADMIN':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('index'))
