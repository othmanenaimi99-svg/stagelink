import os
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

PRIMARY = colors.HexColor('#185FA5')
GREEN = colors.HexColor('#1D9E75')
GRAY = colors.HexColor('#888780')
LIGHT = colors.HexColor('#F8F9FA')
BORDER = colors.HexColor('#D3D1C7')


def generer_convention_pdf(convention, candidature, etudiant, entreprise, offre, base_dir):
    os.makedirs(os.path.join(base_dir, 'static', 'uploads', 'conventions'), exist_ok=True)
    filename = f'convention_{candidature.id}.pdf'
    filepath = os.path.join(base_dir, 'static', 'uploads', 'conventions', filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm
    )

    styles = getSampleStyleSheet()

    s_title = ParagraphStyle('T', parent=styles['Title'],
        textColor=PRIMARY, fontSize=20, spaceAfter=4, alignment=TA_CENTER, fontName='Helvetica-Bold')
    s_sub = ParagraphStyle('S', parent=styles['Normal'],
        textColor=GRAY, fontSize=10, spaceAfter=18, alignment=TA_CENTER)
    s_section = ParagraphStyle('SEC', parent=styles['Normal'],
        textColor=PRIMARY, fontSize=11, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6)
    s_body = ParagraphStyle('B', parent=styles['Normal'],
        fontSize=10, spaceAfter=5, leading=16)
    s_footer = ParagraphStyle('F', parent=styles['Normal'],
        fontSize=8, textColor=GRAY, alignment=TA_CENTER)

    story = []

    story.append(Paragraph('CONVENTION DE STAGE', s_title))
    story.append(Paragraph('StageLink MA — Plateforme nationale de stages · Maroc', s_sub))
    story.append(HRFlowable(width='100%', thickness=1.5, color=PRIMARY))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph('ARTICLE 1 — PARTIES CONTRACTANTES', s_section))
    parties = [
        ['', 'ÉTUDIANT(E)', 'ENTREPRISE'],
        ['Nom', etudiant.nom_complet, entreprise.nom],
        ['Email', etudiant.utilisateur.email, entreprise.utilisateur.email],
        ['Ville', etudiant.ville or '—', entreprise.ville or '—'],
        ['Filière / Secteur', etudiant.filiere or '—', entreprise.secteur or '—'],
        ['Université / Taille', etudiant.universite or '—', entreprise.taille or '—'],
    ]
    t = Table(parties, colWidths=[3.5 * cm, 7.5 * cm, 7.5 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F4FA')]),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph('ARTICLE 2 — OBJET ET DESCRIPTION DU STAGE', s_section))
    story.append(Paragraph(f'Le présent stage a pour objet : <b>{offre.titre}</b>.', s_body))
    if offre.description:
        desc = offre.description[:600] + ('...' if len(offre.description) > 600 else '')
        story.append(Paragraph(desc, s_body))

    if offre.missions_list:
        story.append(Paragraph('Missions principales :', s_body))
        for m in offre.missions_list[:5]:
            story.append(Paragraph(f'• {m}', s_body))

    story.append(Paragraph('ARTICLE 3 — DURÉE ET PÉRIODE DU STAGE', s_section))
    debut = convention.date_debut.strftime('%d/%m/%Y') if convention.date_debut else '___________'
    fin = convention.date_fin.strftime('%d/%m/%Y') if convention.date_fin else '___________'
    story.append(Paragraph(
        f'Le stage se déroulera du <b>{debut}</b> au <b>{fin}</b>, '
        f'soit une durée de <b>{offre.duree} mois</b>, dans les locaux de '
        f'{entreprise.nom} situés à <b>{offre.ville}</b>.', s_body))

    story.append(Paragraph('ARTICLE 4 — COMPÉTENCES ET DOMAINES DÉVELOPPÉS', s_section))
    comps = ', '.join(c.nom for c in offre.competences)
    story.append(Paragraph(
        f'Compétences ciblées : {comps if comps else "À définir avec l\'encadrant."}', s_body))

    story.append(Paragraph('ARTICLE 5 — ENGAGEMENTS DES PARTIES', s_section))
    engagements = [
        "L'entreprise s'engage à désigner un encadrant référent et à fournir à l'étudiant(e) les ressources nécessaires à la réalisation de ses missions.",
        "L'étudiant(e) s'engage à respecter le règlement intérieur de l'établissement d'accueil, à faire preuve de professionnalisme et à remettre un rapport de stage à l'issue de la période.",
        "Les deux parties s'engagent à respecter la confidentialité des informations auxquelles l'étudiant(e) aura accès durant le stage.",
        "Aucune rémunération n'est garantie par la présente convention sauf accord distinct entre les parties.",
    ]
    for eng in engagements:
        story.append(Paragraph(f'• {eng}', s_body))

    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.4 * cm))

    sig_data = [
        ["L'Étudiant(e)", '', "L'Entreprise"],
        [etudiant.nom_complet, '', entreprise.nom],
        ['', '', ''],
        ['Date : _______________', '', 'Date : _______________'],
        ['', '', ''],
        ['Signature :', '', 'Signature / Cachet :'],
        ['\n\n\n________________________', '', '\n\n\n________________________'],
    ]
    t2 = Table(sig_data, colWidths=[6 * cm, 5 * cm, 6 * cm])
    t2.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('TEXTCOLOR', (0, 0), (0, 0), PRIMARY),
        ('TEXTCOLOR', (2, 0), (2, 0), GREEN),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t2)

    story.append(Spacer(1, 0.6 * cm))
    gen_date = convention.date_generation.strftime('%d/%m/%Y') if convention.date_generation else date.today().strftime('%d/%m/%Y')
    story.append(Paragraph(
        f'Convention générée automatiquement par StageLink MA • {gen_date} • www.stagelink.ma',
        s_footer))

    doc.build(story)
    return os.path.join('static', 'uploads', 'conventions', filename)


def generer_rapport_admin_pdf(stats, base_dir):
    os.makedirs(os.path.join(base_dir, 'static', 'uploads'), exist_ok=True)
    filename = f'rapport_admin_{date.today().strftime("%Y%m%d")}.pdf'
    filepath = os.path.join(base_dir, 'static', 'uploads', filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2.5 * cm, rightMargin=2.5 * cm)
    styles = getSampleStyleSheet()

    s_title = ParagraphStyle('T', parent=styles['Title'],
        textColor=PRIMARY, fontSize=18, spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Bold')
    s_sub = ParagraphStyle('S', parent=styles['Normal'],
        textColor=GRAY, fontSize=10, spaceAfter=14, alignment=TA_CENTER)
    s_section = ParagraphStyle('SEC', parent=styles['Normal'],
        textColor=PRIMARY, fontSize=11, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6)
    s_body = ParagraphStyle('B', parent=styles['Normal'], fontSize=10, spaceAfter=4, leading=15)
    s_footer = ParagraphStyle('F', parent=styles['Normal'],
        fontSize=8, textColor=GRAY, alignment=TA_CENTER)

    story = []
    story.append(Paragraph('RAPPORT STATISTIQUES', s_title))
    story.append(Paragraph(f'StageLink MA — Généré le {date.today().strftime("%d/%m/%Y")}', s_sub))
    story.append(HRFlowable(width='100%', thickness=1.5, color=PRIMARY))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph('INDICATEURS GLOBAUX', s_section))
    metrics = [
        ['Indicateur', 'Valeur'],
        ['Étudiants inscrits', str(stats.get('nb_etudiants', 0))],
        ['Entreprises vérifiées', str(stats.get('nb_entreprises', 0))],
        ['Offres actives', str(stats.get('nb_offres', 0))],
        ['Candidatures totales', str(stats.get('nb_candidatures', 0))],
        ['Stages conclus (Acceptés)', str(stats.get('nb_acceptees', 0))],
        ['Taux de conversion', f"{stats.get('taux', 0)}%"],
    ]
    t = Table(metrics, colWidths=[10 * cm, 7 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F4FA')]),
        ('GRID', (0, 0), (-1, -1), 0.4, BORDER),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t)

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        'Rapport généré automatiquement par StageLink MA', s_footer))

    doc.build(story)
    return os.path.join('static', 'uploads', filename)
