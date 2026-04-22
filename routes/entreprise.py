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
    entreprise = current_user.entreprise
    offres_actives = entreprise.offres.filter_by(statut='ACTIVE').all()
    offres_all = entreprise.offres.all()

    candidatures_attente = []
    for offre in offres_actives:
        for c in offre.candidatures.filter_by(statut='EN_ATTENTE').order_by(
                Candidature.score_matching.desc()).all():
            candidatures_attente.append(c)
    candidatures_attente.sort(key=lambda c: c.score_matching, reverse=True)

    nb_total = sum(o.candidatures.count() for o in offres_all)
    nb_attente = sum(o.candidatures.filter_by(statut='EN_ATTENTE').count() for o in offres_all)
    nb_acceptee = sum(o.candidatures.filter_by(statut='ACCEPTEE').count() for o in offres_all)
    scores = [c.score_matching for o in offres_all for c in o.candidatures.all() if c.score_matching]
    score_moyen = round(sum(scores) / len(scores)) if scores else 0

    nb_sans_feedback = 0
    for o in offres_all:
        for c in o.candidatures.filter_by(statut='REFUSEE').all():
            if not c.feedback:
                nb_sans_feedback += 1

    nb_offres_fermees = entreprise.offres.filter_by(statut='FERMEE').count()

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

    offres = entreprise.offres.all()
    all_candidatures = []
    for offre in offres:
        q = offre.candidatures.order_by(Candidature.score_matching.desc())
        if statut_filter:
            q = q.filter_by(statut=statut_filter)
        if offre_id and str(offre.id) == str(offre_id):
            all_candidatures.extend(q.all())
        elif not offre_id:
            all_candidatures.extend(q.all())

    all_candidatures.sort(key=lambda c: c.score_matching, reverse=True)

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
        type='info'
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
