import os
import resend
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature


def _serializer():
    return URLSafeTimedSerializer(os.environ.get('SECRET_KEY', 'dev-key'))


def generate_verification_token(email):
    return _serializer().dumps(email, salt='email-verify')


def verify_token(token, max_age=86400):
    try:
        return _serializer().loads(token, salt='email-verify', max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None


def send_verification_email(to_email, verification_url):
    api_key = os.environ.get('RESEND_API_KEY')
    mail_from = os.environ.get('MAIL_FROM', 'onboarding@resend.dev')
    if not api_key:
        print("[EMAIL] RESEND_API_KEY non défini")
        return False
    resend.api_key = api_key
    try:
        resend.Emails.send({
            'from': mail_from,
            'to': to_email,
            'subject': 'Vérifiez votre adresse email — StageLink MA',
            'html': f"""
            <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;padding:32px;border:1px solid #e5e7eb;border-radius:12px">
              <div style="text-align:center;margin-bottom:24px">
                <h2 style="color:#1e40af;margin:0">Stage<span style="color:#3b82f6">Link</span> MA</h2>
              </div>
              <h3 style="color:#111827">Confirmez votre adresse email</h3>
              <p style="color:#6b7280">Merci de vous être inscrit sur StageLink MA. Cliquez sur le bouton ci-dessous pour vérifier votre adresse email.</p>
              <div style="text-align:center;margin:32px 0">
                <a href="{verification_url}"
                   style="background:#1e40af;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:15px">
                  Vérifier mon email
                </a>
              </div>
              <p style="color:#9ca3af;font-size:12px">Ce lien expire dans 24 heures. Si vous n'avez pas créé de compte, ignorez cet email.</p>
              <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
              <p style="color:#9ca3af;font-size:11px;text-align:center">© 2026 StageLink MA · stagelinkma.com</p>
            </div>
            """
        })
        return True
    except Exception as e:
        print(f"[EMAIL] Erreur envoi: {e}")
        return False
