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
            if not user.email_verifie:
                # Compte non vérifié → renvoyer un code et rediriger
                from services.email_service import generate_code, send_verification_code
                from datetime import datetime, timedelta
                code = generate_code()
                user.code_verification = code
                user.code_expiry = datetime.utcnow() + timedelta(minutes=30)
                db.session.commit()
                send_verification_code(user.email, code)
                session['verify_user_id'] = user.id
                flash("Votre email n'est pas encore vérifié. Un nouveau code a été envoyé.", 'info')
                return redirect(url_for('auth.verify_code'))
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
        from sqlalchemy.exc import IntegrityError

        # Vérifier si email déjà utilisé
        if Utilisateur.query.filter_by(email=data['email']).first():
            flash("Cet email est déjà utilisé. Veuillez vous connecter.", 'error')
            session.pop('register_data', None)
            return redirect(url_for('auth.login'))

        u = Utilisateur(email=data['email'], role=data['role'])
        u.set_password(data['password'])
        db.session.add(u)
        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            flash("Cet email est déjà utilisé. Veuillez vous connecter.", 'error')
            session.pop('register_data', None)
            return redirect(url_for('auth.login'))

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

        # Générer et envoyer le code de vérification
        from services.email_service import generate_code, send_verification_code
        from datetime import datetime, timedelta
        code = generate_code()
        u.code_verification = code
        u.code_expiry = datetime.utcnow() + timedelta(minutes=30)
        db.session.commit()

        nom = data.get('nom', '')
        send_verification_code(u.email, code, nom)

        session['verify_user_id'] = u.id
        return redirect(url_for('auth.verify_code'))

    return render_template('auth/login.html', tab='register', step=4, data=data)



@auth_bp.route('/verify-code', methods=['GET', 'POST'])
def verify_code():
    user_id = session.get('verify_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    user = Utilisateur.query.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))

    # Si pas de code en attente, en envoyer un automatiquement
    if not user.code_verification and request.method == 'GET':
        from services.email_service import generate_code, send_verification_code
        from datetime import datetime, timedelta
        code = generate_code()
        user.code_verification = code
        user.code_expiry = datetime.utcnow() + timedelta(minutes=30)
        db.session.commit()
        send_verification_code(user.email, code)

    if request.method == 'POST':
        from datetime import datetime
        code_saisi = request.form.get('code', '').strip()

        if not user.code_expiry or datetime.utcnow() > user.code_expiry:
            flash("Code expiré. Veuillez en demander un nouveau.", 'error')
            return render_template('auth/verify_code.html', email=user.email)

        if code_saisi == user.code_verification:
            user.email_verifie = True
            user.code_verification = None
            user.code_expiry = None
            db.session.commit()
            session.pop('verify_user_id', None)
            login_user(user)
            flash("Email vérifié ! Bienvenue sur StageLink MA.", 'success')
            return _redirect_by_role(user)
        else:
            flash("Code incorrect. Vérifiez votre email.", 'error')

    return render_template('auth/verify_code.html', email=user.email)


@auth_bp.route('/resend-code', methods=['POST'])
def resend_code():
    user_id = session.get('verify_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    user = Utilisateur.query.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))

    from services.email_service import generate_code, send_verification_code
    from datetime import datetime, timedelta
    code = generate_code()
    user.code_verification = code
    user.code_expiry = datetime.utcnow() + timedelta(minutes=30)
    db.session.commit()
    send_verification_code(user.email, code)
    flash("Nouveau code envoyé.", 'success')
    return redirect(url_for('auth.verify_code'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        print(f"[RESET] Demande reset pour: {email}")
        try:
            user = Utilisateur.query.filter_by(email=email).first()
            print(f"[RESET] User trouvé: {user is not None}")
        except Exception as e:
            print(f"[RESET] Erreur DB: {e}")
            flash("Erreur serveur. Réessayez.", 'error')
            return render_template('auth/forgot_password.html')
        if user and user.actif:
            import secrets
            from datetime import datetime, timedelta
            from services.email_service import send_reset_email
            token = secrets.token_urlsafe(48)
            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(minutes=30)
            db.session.commit()
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            nom = user.nom if user.nom != user.email else ''
            send_reset_email(user.email, reset_url, nom)
        flash("Lien envoyé ! Vérifiez votre boîte email ainsi que vos spams.", 'success')
        return redirect(url_for('auth.forgot_password'))
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    from datetime import datetime
    user = Utilisateur.query.filter_by(reset_token=token).first()
    if not user or not user.reset_token_expiry or datetime.utcnow() > user.reset_token_expiry:
        flash("Lien invalide ou expiré. Demandez-en un nouveau.", 'error')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if len(password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", 'error')
            return render_template('auth/reset_password.html', token=token)
        if password != confirm:
            flash("Les mots de passe ne correspondent pas.", 'error')
            return render_template('auth/reset_password.html', token=token)
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        flash("Mot de passe mis à jour. Vous pouvez vous connecter.", 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', token=token)


def _redirect_by_role(user):
    if user.role == 'ETUDIANT':
        return redirect(url_for('etudiant.dashboard'))
    elif user.role == 'ENTREPRISE':
        return redirect(url_for('entreprise.dashboard'))
    elif user.role == 'ADMIN':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('index'))
