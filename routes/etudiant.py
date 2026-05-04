import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app, abort
from flask_login import login_required, current_user
from functools import wraps
from models import db, Etudiant, Offre, Candidature, Convention, Competence, Notification
from services.matching import get_offres_avec_scores, get_score_detail, generer_lettre_motivation

etudiant_bp = Blueprint('etudiant', __name__, url_prefix='/etudiant')


def get_notif_count():
    return current_user.notifications.filter_by(est_lue=False).count()


def etudiant_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'ETUDIANT':
            abort(403)
        if not current_user.email_verifie:
            flash("Veuillez vérifier votre email avant d'accéder à votre compte.", 'error')
            return redirect(url_for('auth.check_email'))
        return f(*args, **kwargs)
    return login_required(decorated)


@etudiant_bp.route('/dashboard')
@etudiant_required
def dashboard():
    etudiant = current_user.etudiant
    candidatures_recentes = (etudiant.candidatures
        .order_by(Candidature.date_postulation.desc()).limit(5).all())

    offres_actives = Offre.query.filter_by(statut='ACTIVE').join(
        Offre.entreprise).filter_by(est_verifiee=True).all()
    offres_avec_scores = get_offres_avec_scores(etudiant, offres_actives)[:3]
    nb_offres_count = Offre.query.filter_by(statut='ACTIVE').join(
        Offre.entreprise).filter_by(est_verifiee=True).count()

    feedbacks = []
    for c in etudiant.candidatures.filter_by(statut='REFUSEE').all():
        if c.feedback:
            feedbacks.append(c)

    nb_total = etudiant.candidatures.count()
    nb_attente = etudiant.candidatures.filter_by(statut='EN_ATTENTE').count()
    nb_acceptee = etudiant.candidatures.filter_by(statut='ACCEPTEE').count()
    nb_refusee = etudiant.candidatures.filter_by(statut='REFUSEE').count()

    scores = [c.score_matching for c in etudiant.candidatures.all() if c.score_matching]
    score_moyen = round(sum(scores) / len(scores)) if scores else 0

    convention_dispo = None
    for c in etudiant.candidatures.filter_by(statut='ACCEPTEE').all():
        if c.convention and c.convention.pdf_path:
            convention_dispo = c
            break

    return render_template('etudiant/dashboard.html',
        etudiant=etudiant,
        candidatures_recentes=candidatures_recentes,
        offres_recommandees=offres_avec_scores,
        feedbacks=feedbacks,
        nb_total=nb_total, nb_attente=nb_attente,
        nb_acceptee=nb_acceptee, nb_refusee=nb_refusee,
        score_moyen=score_moyen,
        convention_dispo=convention_dispo,
        nb_offres_count=nb_offres_count,
        notif_count=get_notif_count())


@etudiant_bp.route('/offres')
@etudiant_required
def offres():
    etudiant = current_user.etudiant
    filiere_filter = request.args.get('filiere', '')
    ville_filter = request.args.get('ville', '')
    duree_filter = request.args.get('duree', '')
    tri = request.args.get('tri', 'score')
    q = request.args.get('q', '')

    query = Offre.query.filter_by(statut='ACTIVE').join(
        Offre.entreprise).filter_by(est_verifiee=True)

    if filiere_filter:
        query = query.filter(Offre.filiere_requise == filiere_filter)
    if ville_filter:
        query = query.filter(Offre.ville == ville_filter)
    if duree_filter:
        try:
            query = query.filter(Offre.duree == int(duree_filter))
        except ValueError:
            pass
    if q:
        query = query.filter(
            Offre.titre.ilike(f'%{q}%') |
            Offre.ville.ilike(f'%{q}%')
        )

    offres_list = query.all()
    offres_avec_scores = get_offres_avec_scores(etudiant, offres_list)

    if tri == 'date':
        offres_avec_scores.sort(key=lambda x: x[0].date_publication, reverse=True)

    nb_offres_count = Offre.query.filter_by(statut='ACTIVE').join(
        Offre.entreprise).filter_by(est_verifiee=True).count()

    return render_template('etudiant/offres.html',
        etudiant=etudiant,
        offres=offres_avec_scores,
        nb_offres_count=nb_offres_count,
        notif_count=get_notif_count())


@etudiant_bp.route('/offres/<int:offre_id>')
@etudiant_required
def detail_offre(offre_id):
    offre = Offre.query.get_or_404(offre_id)
    if not offre.entreprise.est_verifiee or offre.statut != 'ACTIVE':
        abort(404)
    etudiant = current_user.etudiant
    score_detail = get_score_detail(etudiant, offre)

    candidature_existante = etudiant.candidatures.filter_by(offre_id=offre_id).first()
    lettre_auto = generer_lettre_motivation(etudiant, offre)

    autres_candidatures = (Candidature.query
        .join(Candidature.offre)
        .filter(Offre.entreprise_id == offre.entreprise_id,
                Candidature.statut == 'ACCEPTEE')
        .limit(3).all())

    return render_template('etudiant/detail_offre.html',
        offre=offre,
        etudiant=etudiant,
        detail=score_detail,
        deja_postule=candidature_existante,
        lettre_auto=lettre_auto,
        notif_count=get_notif_count())


@etudiant_bp.route('/postuler/<int:offre_id>', methods=['POST'])
@etudiant_required
def postuler(offre_id):
    offre = Offre.query.get_or_404(offre_id)
    if not offre.entreprise.est_verifiee or offre.statut != 'ACTIVE':
        abort(400)
    etudiant = current_user.etudiant

    existant = etudiant.candidatures.filter_by(offre_id=offre_id).first()
    if existant:
        flash("Vous avez déjà postulé à cette offre.", 'error')
        return redirect(url_for('etudiant.detail_offre', offre_id=offre_id))

    if not etudiant.cv_path:
        flash("Vous devez uploader votre CV avant de postuler.", 'error')
        return redirect(url_for('etudiant.profil'))

    lettre = request.form.get('lettre_motivation', '').strip()
    if not lettre:
        flash("La lettre de motivation est obligatoire.", 'error')
        return redirect(url_for('etudiant.detail_offre', offre_id=offre_id))

    from services.matching import calculer_score
    score = calculer_score(etudiant, offre)

    candidature = Candidature(
        etudiant_id=etudiant.id,
        offre_id=offre_id,
        statut='EN_ATTENTE',
        lettre_motivation=lettre,
        score_matching=score
    )
    db.session.add(candidature)
    db.session.flush()

    notif = Notification(
        utilisateur_id=offre.entreprise.utilisateur_id,
        message=f"Nouvelle candidature de {etudiant.nom_complet} pour « {offre.titre} ».",
        type='candidature'
    )
    db.session.add(notif)
    db.session.commit()

    flash("Votre candidature a été envoyée avec succès !", 'success')
    return redirect(url_for('etudiant.candidatures'))


@etudiant_bp.route('/candidatures')
@etudiant_required
def candidatures():
    etudiant = current_user.etudiant
    statut_filter = request.args.get('statut', '')
    cands = etudiant.candidatures.order_by(Candidature.date_postulation.desc())
    if statut_filter:
        cands = cands.filter_by(statut=statut_filter)
    return render_template('etudiant/candidatures.html',
        etudiant=etudiant,
        candidatures=cands.all(),
        statut_filtre=statut_filter,
        notif_count=get_notif_count())


@etudiant_bp.route('/convention/<int:candidature_id>/telecharger')
@etudiant_required
def telecharger_convention(candidature_id):
    candidature = Candidature.query.get_or_404(candidature_id)
    if candidature.etudiant_id != current_user.etudiant.id:
        abort(403)
    if candidature.statut != 'ACCEPTEE':
        abort(403)

    if not candidature.convention or not candidature.convention.pdf_path:
        from services.pdf_gen import generer_convention_pdf
        from datetime import timedelta
        import datetime
        base_dir = os.path.abspath(os.path.join(current_app.root_path))
        if not candidature.convention:
            conv = Convention(
                candidature_id=candidature.id,
                date_debut=datetime.date.today() + datetime.timedelta(days=14),
                date_fin=datetime.date.today() + datetime.timedelta(days=14 + 30 * (candidature.offre.duree or 2))
            )
            db.session.add(conv)
            db.session.flush()
            candidature_conv = conv
        else:
            candidature_conv = candidature.convention

        path = generer_convention_pdf(
            candidature_conv, candidature,
            candidature.etudiant, candidature.offre.entreprise,
            candidature.offre, base_dir)
        candidature_conv.pdf_path = path
        db.session.commit()

    full_path = os.path.join(current_app.root_path, candidature.convention.pdf_path)
    if not os.path.exists(full_path):
        flash("Erreur lors de la génération de la convention.", 'error')
        return redirect(url_for('etudiant.dashboard'))

    return send_file(full_path, as_attachment=True,
        download_name=f'convention_stage_{candidature.offre.entreprise.nom}.pdf')


@etudiant_bp.route('/profil', methods=['GET', 'POST'])
@etudiant_required
def profil():
    etudiant = current_user.etudiant
    competences_all = Competence.query.order_by(Competence.categorie, Competence.nom).all()

    if request.method == 'POST':
        nom = request.form.get('nom', etudiant.nom_complet).strip()
        if nom:
            etudiant.nom_complet = nom
        etudiant.universite = request.form.get('universite', '').strip()
        etudiant.filiere = request.form.get('filiere', '').strip()
        etudiant.niveau = request.form.get('niveau', '').strip()
        etudiant.ville = request.form.get('ville', '').strip()

        competences_ids = request.form.getlist('competences')
        etudiant.competences = Competence.query.filter(
            Competence.id.in_([int(x) for x in competences_ids])
        ).all()

        cv_file = request.files.get('cv')
        if cv_file and cv_file.filename:
            ext = cv_file.filename.rsplit('.', 1)[-1].lower() if '.' in cv_file.filename else ''
            if ext != 'pdf':
                flash("Seuls les fichiers PDF sont acceptés pour le CV.", 'error')
                return redirect(url_for('etudiant.profil'))
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
                public_id=f'cv_{etudiant.id}',
                overwrite=True
            )
            etudiant.cv_path = result['secure_url']

        db.session.commit()
        flash("Profil mis à jour avec succès.", 'success')
        return redirect(url_for('etudiant.profil'))

    return render_template('etudiant/profil.html',
        etudiant=etudiant,
        toutes_competences=competences_all,
        notif_count=get_notif_count())


@etudiant_bp.route('/notifications/lire')
@etudiant_required
def marquer_notifications_lues():
    current_user.notifications.update({'est_lue': True})
    db.session.commit()
    return redirect(request.referrer or url_for('etudiant.dashboard'))
