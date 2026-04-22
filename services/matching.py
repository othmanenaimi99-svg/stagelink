def calculer_score(etudiant, offre):
    score = 0.0
    if etudiant.filiere in offre.filieres_requises:
        score += 40
    competences_offre = set(c.nom for c in offre.competences)
    if competences_offre:
        ratio = len(set(c.nom for c in etudiant.competences) & competences_offre) / len(competences_offre)
        score += 40 * ratio
    if etudiant.ville == offre.ville:
        score += 20
    return round(score, 2)


def get_score_color(score):
    if score >= 80:
        return 'primary'
    elif score >= 60:
        return 'green'
    return 'orange'


def get_score_detail(etudiant, offre):
    filiere_score = 40 if etudiant.filiere in offre.filieres_requises else 0

    offre_comps = {c.nom: c for c in offre.competences}
    etudiant_noms = set(c.nom for c in etudiant.competences)
    if offre_comps:
        match_count = len(etudiant_noms & set(offre_comps.keys()))
        ratio = match_count / len(offre_comps)
        competence_score = round(40 * ratio, 2)
    else:
        competence_score = 0

    ville_score = 20 if etudiant.ville == offre.ville else 0
    total = round(filiere_score + competence_score + ville_score, 2)

    competences_match = [c for c in offre.competences if c.nom in etudiant_noms]
    competences_missing = [c for c in offre.competences if c.nom not in etudiant_noms]

    return {
        'total': total,
        'filiere': filiere_score,
        'competences': competence_score,
        'ville': ville_score,
        'color': get_score_color(total),
        'is_top_match': total >= 85,
        'competences_match': competences_match,
        'competences_missing': competences_missing,
    }


def get_offres_avec_scores(etudiant, offres):
    result = []
    for offre in offres:
        detail = get_score_detail(etudiant, offre)
        result.append((offre, detail))
    result.sort(key=lambda x: x[1]['total'], reverse=True)
    return result


def generer_lettre_motivation(etudiant, offre):
    entreprise_nom = offre.entreprise.nom
    return f"""Madame, Monsieur,

Étudiant(e) en {etudiant.niveau or 'formation'} {etudiant.filiere or ''} à {etudiant.universite or 'mon établissement'}, je souhaite vous adresser ma candidature pour le stage « {offre.titre} » au sein de {entreprise_nom}.

Votre entreprise, reconnue dans le secteur {offre.entreprise.secteur or ''}, représente pour moi une opportunité exceptionnelle de mettre en pratique mes connaissances théoriques et de développer mes compétences professionnelles dans un environnement stimulant.

Motivé(e) et rigoureux(se), je suis convaincu(e) que mon profil correspond aux attentes de votre équipe. Je reste disponible pour un entretien à votre convenance.

Dans l'attente de votre retour, veuillez agréer, Madame, Monsieur, l'expression de mes salutations distinguées.

{etudiant.nom_complet}"""
