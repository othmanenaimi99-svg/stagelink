from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from functools import wraps
from models import db, Entreprise, Offre, Candidature, Competence, Notification, Convention
from datetime import date

entreprise_bp = Blueprint('entreprise', __name__, url_prefix='/entreprise')


def entreprise_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'ENTREPRISE':
            abort(403)
        if not current_user.email_verifie:
            from flask import session as flask_session
            flask_session['verify_user_id'] = current_user.id
            flash("Veuillez vérifier votre email pour accéder à votre compte.", 'error')
            return redirect(url_for('auth.verify_code'))
        return f(*args, **kwargs)
    return login_required(decorated)


def verifie_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.entreprise.est_verifiee:
            flash("Votre compte est en attente de vérification par notre équipe.", 'warning')
            return redirect(url_for('entreprise.dashboard'))
        return f(*args, **kwargs)
    return entreprise_required(decorated)


@entreprise_bp.route('/dashboard')
@entreprise_required
def dashboard():
    from sqlalchemy.orm import joinedload
    entreprise = current_user.entreprise

    offres_all = Offre.query.filter_by(entreprise_id=entreprise.id).all()
    offres_actives = [o for o in offres_all if o.statut == 'ACTIVE']

    toutes_cands = (
        Candidature.query
        .options(joinedload(Candidature.etudiant))
        .join(Offre, Candidature.offre_id == Offre.id)
        .filter(Offre.entreprise_id == entreprise.id)
        .all()
    )

    candidatures_attente = sorted(
        [c for c in toutes_cands if c.statut == 'EN_ATTENTE'],
        key=lambda c: c.score_matching, reverse=True
    )

    nb_total    = len(toutes_cands)
    nb_attente  = sum(1 for c in toutes_cands if c.statut == 'EN_ATTENTE')
    nb_acceptee = sum(1 for c in toutes_cands if c.statut == 'ACCEPTEE')
    scores      = [c.score_matching for c in toutes_cands if c.score_matching]
    score_moyen = round(sum(scores) / len(scores)) if scores else 0
    nb_sans_feedback = sum(1 for c in toutes_cands if c.statut == 'REFUSEE' and not c.feedback)
    nb_offres_fermees = sum(1 for o in offres_all if o.statut == 'FERMEE')

    return render_template('entreprise/dashboard.html',
        entreprise=entreprise,
        offres_actives=offres_actives,
        candidatures_recentes=candidatures_attente[:5],
        nb_offres_actives=len(offres_actives),
        nb_candidatures_total=nb_total,
        nb_acceptees=nb_acceptee,
        nb_offres_fermees=nb_offres_fermees,
        nb_sans_feedback=nb_sans_feedback)


@entreprise_bp.route('/candidatures')
@entreprise_required
def candidatures():
    entreprise = current_user.entreprise
    offre_id = request.args.get('offre_id', '')
    statut_filter = request.args.get('statut', '')

    from sqlalchemy.orm import joinedload
    offres = Offre.query.filter_by(entreprise_id=entreprise.id).all()

    cands_query = (
        Candidature.query
        .options(joinedload(Candidature.etudiant))
        .join(Offre, Candidature.offre_id == Offre.id)
        .filter(Offre.entreprise_id == entreprise.id)
    )
    if offre_id:
        cands_query = cands_query.filter(Candidature.offre_id == int(offre_id))
    if statut_filter:
        cands_query = cands_query.filter(Candidature.statut == statut_filter)

    all_candidatures = cands_query.order_by(Candidature.score_matching.desc()).all()

    return render_template('entreprise/candidatures.html',
        entreprise=entreprise,
        candidatures=all_candidatures,
        offres_list=offres,
        offre_id_filtre=offre_id,
        statut_filtre=statut_filter)


@entreprise_bp.route('/candidature/<int:candidature_id>/accepter', methods=['POST'])
@verifie_required
def accepter_candidature(candidature_id):
    c = Candidature.query.get_or_404(candidature_id)
    if c.offre.entreprise_id != current_user.entreprise.id:
        abort(403)
    if c.statut != 'EN_ATTENTE':
        flash("Cette candidature ne peut plus être modifiée.", 'error')
        return redirect(url_for('entreprise.candidatures'))

    c.statut = 'ACCEPTEE'

    notif = Notification(
        utilisateur_id=c.etudiant.utilisateur_id,
        message=f"Félicitations ! Votre candidature pour « {c.offre.titre} » chez {c.offre.entreprise.nom} a été acceptée.",
        type='success'
    )
    db.session.add(notif)
    db.session.commit()
    flash(f"Candidature de {c.etudiant.nom_complet} acceptée.", 'success')
    return redirect(url_for('entreprise.candidatures'))


@entreprise_bp.route('/candidature/<int:candidature_id>/refuser', methods=['POST'])
@verifie_required
def refuser_candidature(candidature_id):
    c = Candidature.query.get_or_404(candidature_id)
    if c.offre.entreprise_id != current_user.entreprise.id:
        abort(403)
    if c.statut != 'EN_ATTENTE':
        flash("Cette candidature ne peut plus être modifiée.", 'error')
        return redirect(url_for('entreprise.candidatures'))

    feedback_text = request.form.get('commentaire', '').strip()
    if not feedback_text:
        abort(400)

    c.statut = 'REFUSEE'
    from models import Feedback
    fb = Feedback(candidature_id=c.id, commentaire=feedback_text)
    db.session.add(fb)

    notif = Notification(
        utilisateur_id=c.etudiant.utilisateur_id,
        message=f"Votre candidature pour « {c.offre.titre} » chez {c.offre.entreprise.nom} a été refusée. Un feedback vous a été laissé.",
        type='error'
    )
    db.session.add(notif)
    db.session.commit()
    flash(f"Candidature de {c.etudiant.nom_complet} refusée avec feedback.", 'success')
    return redirect(url_for('entreprise.candidatures'))


@entreprise_bp.route('/candidature/<int:candidature_id>/feedback', methods=['POST'])
@verifie_required
def ajouter_feedback(candidature_id):
    c = Candidature.query.get_or_404(candidature_id)
    if c.offre.entreprise_id != current_user.entreprise.id:
        abort(403)
    if c.statut != 'REFUSEE':
        abort(400)
    if c.feedback:
        flash("Un feedback existe déjà pour cette candidature.", 'error')
        return redirect(url_for('entreprise.dashboard'))

    feedback_text = request.form.get('feedback', '').strip()
    if not feedback_text:
        abort(400)

    from models import Feedback
    fb = Feedback(candidature_id=c.id, commentaire=feedback_text)
    db.session.add(fb)
    db.session.commit()
    flash("Feedback ajouté avec succès.", 'success')
    return redirect(url_for('entreprise.dashboard'))


@entreprise_bp.route('/offres')
@entreprise_required
def offres():
    entreprise = current_user.entreprise
    toutes_offres = entreprise.offres.order_by(Offre.date_publication.desc()).all()
    return render_template('entreprise/offres.html',
        entreprise=entreprise,
        offres=toutes_offres)


@entreprise_bp.route('/offres/nouvelle', methods=['GET', 'POST'])
@verifie_required
def nouvelle_offre():
    entreprise = current_user.entreprise
    competences_all = Competence.query.order_by(Competence.categorie, Competence.nom).all()

    if request.method == 'POST':
        titre = request.form.get('titre', '').strip()
        description = request.form.get('description', '').strip()
        missions = request.form.get('missions', '').strip()
        duree = request.form.get('duree', '').strip()
        ville = request.form.get('ville', entreprise.ville).strip()
        filiere = request.form.get('filiere_requise', '').strip()
        date_debut = request.form.get('date_debut', '').strip()
        remuneration_str = request.form.get('remuneration', '').strip()
        remuneration = int(remuneration_str) if remuneration_str.isdigit() else None
        competences_ids = request.form.getlist('competences')

        if not all([titre, description, duree, filiere]):
            flash("Les champs titre, description, durée et filière sont obligatoires.", 'error')
            return render_template('entreprise/nouvelle_offre.html',
                entreprise=entreprise, competences=competences_all)

        offre = Offre(
            entreprise_id=entreprise.id,
            titre=titre,
            description=description,
            missions=missions,
            duree=int(duree),
            ville=ville or entreprise.ville,
            filiere_requise=filiere,
            remuneration=remuneration,
            statut='ACTIVE',
            date_publication=date.today(),
            date_debut=date_debut
        )
        offre.competences = Competence.query.filter(
            Competence.id.in_([int(x) for x in competences_ids])
        ).all()
        db.session.add(offre)
        db.session.commit()
        flash("Offre publiée avec succès !", 'success')
        return redirect(url_for('entreprise.offres'))

    return render_template('entreprise/nouvelle_offre.html',
        entreprise=entreprise,
        competences=competences_all)


@entreprise_bp.route('/offres/<int:offre_id>/fermer', methods=['POST'])
@verifie_required
def fermer_offre(offre_id):
    offre = Offre.query.get_or_404(offre_id)
    if offre.entreprise_id != current_user.entreprise.id:
        abort(403)
    offre.statut = 'FERMEE'
    db.session.commit()
    flash("Offre fermée.", 'success')
    return redirect(url_for('entreprise.offres'))


@entreprise_bp.route('/profil', methods=['GET', 'POST'])
@entreprise_required
def profil():
    entreprise = current_user.entreprise
    if request.method == 'POST':
        entreprise.nom = request.form.get('nom', entreprise.nom).strip()
        entreprise.secteur = request.form.get('secteur', '').strip()
        entreprise.ville = request.form.get('ville', '').strip()
        entreprise.taille = request.form.get('taille', '').strip()
        entreprise.description = request.form.get('description', '').strip()
        db.session.commit()
        flash("Profil mis à jour.", 'success')
        return redirect(url_for('entreprise.profil'))
    return render_template('entreprise/profil.html', entreprise=entreprise)


@entreprise_bp.route('/upload-photo', methods=['POST'])
@entreprise_required
def upload_photo():
    from flask import current_app
    entreprise = current_user.entreprise
    file = request.files.get('photo')
    if not file or not file.filename:
        flash("Aucun fichier sélectionné.", 'error')
        return redirect(url_for('entreprise.profil'))
    if not file.filename.lower().rsplit('.', 1)[-1] in {'jpg', 'jpeg', 'png', 'webp'}:
        flash("Format invalide. Utilisez JPG, PNG ou WebP.", 'error')
        return redirect(url_for('entreprise.profil'))
    try:
        import cloudinary, cloudinary.uploader
        cloudinary.config(
            cloud_name=current_app.config['CLOUDINARY_CLOUD_NAME'],
            api_key=current_app.config['CLOUDINARY_API_KEY'],
            api_secret=current_app.config['CLOUDINARY_API_SECRET']
        )
        result = cloudinary.uploader.upload(
            file, folder='stagelink/logos',
            public_id=f'entreprise_{entreprise.id}',
            overwrite=True, resource_type='image',
            transformation=[{'width': 200, 'height': 200, 'crop': 'fill'}]
        )
        entreprise.photo_profil = result['secure_url']
        db.session.commit()
        flash("Logo mis à jour !", 'success')
    except Exception as e:
        flash("Erreur lors de l'upload.", 'error')
    return redirect(url_for('entreprise.profil'))
