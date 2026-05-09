import os
import random
import resend


def generate_code():
    return str(random.randint(100000, 999999))


def send_verification_code(to_email, code, nom=''):
    api_key = os.environ.get('RESEND_API_KEY')

    print(f"[EMAIL] to={to_email} key_set={bool(api_key)}")

    if not api_key:
        print("[EMAIL] RESEND_API_KEY manquant")
        return False

    resend.api_key = api_key

    html_body = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:480px;margin:auto;padding:40px 32px;border:1px solid #e5e7eb;border-radius:16px;background:#fff">
      <div style="text-align:center;margin-bottom:28px">
        <h2 style="color:#185FA5;margin:0;font-size:22px">Stage<span style="color:#1D9E75">Link</span> MA</h2>
      </div>
      <h3 style="color:#111827;font-size:18px;margin-bottom:8px">Vérifiez votre adresse email</h3>
      <p style="color:#6b7280;font-size:14px;margin-bottom:28px">
        {'Bonjour ' + nom + ',' if nom else 'Bonjour,'}<br>
        Utilisez le code ci-dessous pour activer votre compte StageLink MA.
      </p>
      <div style="text-align:center;margin:32px 0">
        <div style="display:inline-block;background:#EAF3FC;border:2px solid #185FA5;border-radius:12px;padding:18px 48px;min-width:260px">
          <span style="font-size:32px;font-weight:700;letter-spacing:6px;color:#185FA5;white-space:nowrap">{' '.join(code)}</span>
        </div>
      </div>
      <p style="color:#9ca3af;font-size:12px;text-align:center;margin-top:24px">
        Ce code expire dans <strong>30 minutes</strong>.<br>
        Si vous n'avez pas créé de compte, ignorez cet email.
      </p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
      <p style="color:#9ca3af;font-size:11px;text-align:center">© 2026 StageLink MA · stagelinkma.com</p>
    </div>
    """

    try:
        result = resend.Emails.send({
            "from": "StageLink MA <noreply@stagelinkma.com>",
            "to": [to_email],
            "subject": f"{code} — Code de vérification StageLink MA",
            "html": html_body
        })
        print(f"[EMAIL] Success: {result}")
        return True
    except Exception as e:
        print(f"[EMAIL] Error {type(e).__name__}: {e}")
        return False


def send_company_status_email(to_email, nom_entreprise, approved, motif=''):
    api_key = os.environ.get('RESEND_API_KEY')
    if not api_key:
        return False

    resend.api_key = api_key

    if approved:
        subject = "✅ Votre compte entreprise a été approuvé — StageLink MA"
        color = "#1D9E75"
        icon = "✅"
        title = "Compte approuvé !"
        message = "Bonne nouvelle ! Votre compte entreprise a été vérifié et approuvé par notre équipe. Vous pouvez dès maintenant publier vos offres de stage et consulter les candidatures."
        btn_text = "Accéder à mon espace"
        btn_url = "https://stagelinkma.com/auth/login"
        extra = ""
    else:
        subject = "❌ Votre demande de vérification — StageLink MA"
        color = "#E24B4A"
        icon = "❌"
        title = "Demande non approuvée"
        message = "Après examen de votre dossier, nous ne sommes pas en mesure d'approuver votre compte pour le moment."
        btn_text = "Contacter le support"
        btn_url = "https://stagelinkma.com"
        extra = f'<p style="color:#6b7280;font-size:13px;margin-top:16px"><strong>Motif :</strong> {motif}</p>' if motif else ''

    html_body = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:480px;margin:auto;padding:40px 32px;border:1px solid #e5e7eb;border-radius:16px;background:#fff">
      <div style="text-align:center;margin-bottom:28px">
        <h2 style="color:#185FA5;margin:0;font-size:22px">Stage<span style="color:#1D9E75">Link</span> MA</h2>
      </div>
      <div style="text-align:center;font-size:40px;margin-bottom:16px">{icon}</div>
      <h3 style="color:#111827;font-size:18px;margin-bottom:12px;text-align:center">{title}</h3>
      <p style="color:#6b7280;font-size:14px;margin-bottom:8px">Bonjour <strong>{nom_entreprise}</strong>,</p>
      <p style="color:#6b7280;font-size:14px;line-height:1.6">{message}</p>
      {extra}
      <div style="text-align:center;margin:32px 0">
        <a href="{btn_url}" style="display:inline-block;background:{color};color:#fff;text-decoration:none;padding:13px 32px;border-radius:10px;font-size:14px;font-weight:600">{btn_text}</a>
      </div>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
      <p style="color:#9ca3af;font-size:11px;text-align:center">© 2026 StageLink MA · stagelinkma.com</p>
    </div>
    """

    try:
        result = resend.Emails.send({
            "from": "StageLink MA <noreply@stagelinkma.com>",
            "to": [to_email],
            "subject": subject,
            "html": html_body
        })
        print(f"[COMPANY EMAIL] Success: {result}")
        return True
    except Exception as e:
        print(f"[COMPANY EMAIL] Error {type(e).__name__}: {e}")
        return False
