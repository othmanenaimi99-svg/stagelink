import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file, current_app
from flask_login import login_required, current_user
from functools import wraps
from models import db, Utilisateur, Etudiant, Entreprise, Offre, Candidature, Notification

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'ADMIN':
            abort(403)
        return f(*args, **kwargs)
    return login_required(decorated)


@admin_bp.route('/')
@admin_required
def dashboard():
    nb_etudiants = Etudiant.query.count()
    nb_entreprises = Entreprise.query.filter_by(est_verifiee=True).count()
    nb_offres = Offre.query.filter_by(statut='ACTIVE').count()
    nb_candidatures = Candidature.query.count()
    nb_acceptees = Candidature.query.filter_by(statut='ACCEPTEE').count()
    taux = round(nb_acceptees / nb_candidatures * 100) if nb_candidatures else 0

    entreprises_attente = Entreprise.query.filter_by(est_verifiee=False).order_by(
        Entreprise.date_inscription.desc()).limit(10).all()

    refusees_sans_feedback = (Candidature.query.filter_by(statut='REFUSEE')
        .filter(~Candidature.feedback.has()).limit(10).all())

    derniers_utilisateurs = Utilisateur.query.order_by(
        Utilisateur.id.desc()).limit(6).all()

    from sqlalchemy import func
    stats_filiere = (db.session.query(Etudiant.filiere, func.count(Etudiant.id))
        .group_by(Etudiant.filiere)
        .order_by(func.count(Etudiant.id).desc())
        .limit(5).all())
    max_count = max((s[1] for s in stats_filiere), default=1)

    nb_entreprises_total = Entreprise.query.count()
    nb_offres_total = Offre.query.count()
    stats = {
        'nb_etudiants': nb_etudiants,
        'nb_entreprises': nb_entreprises,
        'nb_entreprises_verifiees': nb_entreprises,
        'nb_offres_actives': nb_offres,
        'nb_offres_total': nb_offres_total,
        'nb_candidatures': nb_candidatures,
        'nb_acceptees': nb_acceptees,
        'taux': taux,
        'entreprises_en_attente': Entreprise.query.filter_by(est_verifiee=False).count(),
    }

    return render_template('admin/dashboard.html',
        stats=stats,
        entreprises_attente=entreprises_attente,
        feedbacks_manquants=refusees_sans_feedback,
        utilisateurs_recents=derniers_utilisateurs,
        stats_filieres=stats_filiere)


@admin_bp.route('/entreprise/<int:entreprise_id>/approuver', methods=['POST'])
@admin_required
def approuver_entreprise(entreprise_id):
    entreprise = Entreprise.query.get_or_404(entreprise_id)
    entreprise.est_verifiee = True
    notif = Notification(
        utilisateur_id=entreprise.utilisateur_id,
        message="Votre compte entreprise a été vérifié. Vous pouvez désormais publier des offres.",
        type='success'
    )
    db.session.add(notif)
    db.session.commit()
    flash(f"Entreprise « {entreprise.nom} » approuvée.", 'success')
    return redirect(url_for('admin.entreprises'))


@admin_bp.route('/entreprise/<int:entreprise_id>/rejeter', methods=['POST'])
@admin_required
def rejeter_entreprise(entreprise_id):
    entreprise = Entreprise.query.get_or_404(entreprise_id)
    motif = request.form.get('motif', 'Dossier incomplet.')
    notif = Notification(
        utilisateur_id=entreprise.utilisateur_id,
        message=f"Votre demande de vérification a été rejetée. Motif : {motif}",
        type='error'
    )
    db.session.add(notif)
    db.session.commit()
    flash(f"Entreprise « {entreprise.nom} » rejetée.", 'success')
    return redirect(url_for('admin.entreprises'))


@admin_bp.route('/entreprises')
@admin_required
def entreprises():
    statut = request.args.get('statut', '')
    if statut == 'verifiee':
        liste = Entreprise.query.filter_by(est_verifiee=True).order_by(Entreprise.date_inscription.desc()).all()
    elif statut == 'suspendue':
        liste = [e for e in Entreprise.query.all() if not e.utilisateur.actif]
    elif statut == 'en_attente':
        liste = Entreprise.query.filter_by(est_verifiee=False).order_by(Entreprise.date_inscription.desc()).all()
    else:
        liste = Entreprise.query.order_by(Entreprise.date_inscription.desc()).all()
    return render_template('admin/entreprises.html', entreprises=liste, statut_filtre=statut)


@admin_bp.route('/utilisateurs')
@admin_required
def utilisateurs():
    role_filter = request.args.get('role', '')
    q = request.args.get('q', '')
    query = Utilisateur.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    if q:
        etudiants_ids = [e.utilisateur_id for e in Etudiant.query.filter(
            Etudiant.nom_complet.ilike(f'%{q}%')).all()]
        entreprises_ids = [e.utilisateur_id for e in Entreprise.query.filter(
            Entreprise.nom.ilike(f'%{q}%')).all()]
        query = query.filter(
            Utilisateur.email.ilike(f'%{q}%') |
            Utilisateur.id.in_(etudiants_ids + entreprises_ids)
        )
    users = query.order_by(Utilisateur.id.desc()).all()
    return render_template('admin/utilisateurs.html',
        utilisateurs=users, role_filtre=role_filter, search_query=q)


@admin_bp.route('/utilisateur/<int:utilisateur_id>/suspendre', methods=['POST'])
@admin_required
def suspendre_utilisateur(utilisateur_id):
    user = Utilisateur.query.get_or_404(utilisateur_id)
    if user.role == 'ADMIN':
        abort(403)
    user.actif = not user.actif
    db.session.commit()
    action = "suspendu" if not user.actif else "réactivé"
    flash(f"Compte {action}.", 'success')
    return redirect(url_for('admin.utilisateurs'))


@admin_bp.route('/offres')
@admin_required
def offres():
    statut = request.args.get('statut', '')
    q_offres = Offre.query
    if statut:
        q_offres = q_offres.filter_by(statut=statut.upper())
    all_offres = q_offres.order_by(Offre.date_publication.desc()).all()
    return render_template('admin/offres.html', offres=all_offres, statut_filtre=statut)


@admin_bp.route('/offres/<int:offre_id>/supprimer', methods=['POST'])
@admin_required
def supprimer_offre(offre_id):
    offre = Offre.query.get_or_404(offre_id)
    db.session.delete(offre)
    db.session.commit()
    flash("Offre supprimée.", 'success')
    return redirect(url_for('admin.offres'))


@admin_bp.route('/stats')
@admin_required
def stats():
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/stats/export')
@admin_required
def export_pdf():
    from services.pdf_gen import generer_rapport_admin_pdf
    from models import Etudiant, Entreprise, Offre, Candidature

    stats_data = {
        'nb_etudiants': Etudiant.query.count(),
        'nb_entreprises': Entreprise.query.filter_by(est_verifiee=True).count(),
        'nb_offres': Offre.query.filter_by(statut='ACTIVE').count(),
        'nb_candidatures': Candidature.query.count(),
        'nb_acceptees': Candidature.query.filter_by(statut='ACCEPTEE').count(),
    }
    total = stats_data['nb_candidatures']
    stats_data['taux'] = round(stats_data['nb_acceptees'] / total * 100) if total else 0

    base_dir = os.path.abspath(current_app.root_path)
    filepath = generer_rapport_admin_pdf(stats_data, base_dir)
    full_path = os.path.join(base_dir, filepath)

    if not os.path.exists(full_path):
        flash("Erreur lors de la génération du rapport.", 'error')
        return redirect(url_for('admin.dashboard'))

    return send_file(full_path, as_attachment=True,
        download_name='rapport_stagelink_ma.pdf')
