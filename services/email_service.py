import os
import random


def generate_code():
    return str(random.randint(100000, 999999))


def send_verification_code(to_email, code, nom=''):
    api_key = os.environ.get('RESEND_API_KEY')
    mail_from = os.environ.get('MAIL_FROM', 'onboarding@resend.dev')

    print(f"[EMAIL] Sending to={to_email} from={mail_from} api_key_set={bool(api_key)}")

    if not api_key:
        print("[EMAIL] RESEND_API_KEY non défini")
        return False

    try:
        import resend
        resend.api_key = api_key
        result = resend.Emails.send({
            "from": mail_from,
            "to": [to_email],
            "subject": f"{code} — Votre code de vérification StageLink MA",
            "html": f"""
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
                <div style="display:inline-block;background:#EAF3FC;border:2px solid #185FA5;border-radius:12px;padding:18px 40px">
                  <span style="font-size:36px;font-weight:700;letter-spacing:10px;color:#185FA5">{code}</span>
                </div>
              </div>
              <p style="color:#9ca3af;font-size:12px;text-align:center;margin-top:24px">
                Ce code expire dans <strong>10 minutes</strong>.<br>
                Si vous n'avez pas créé de compte, ignorez cet email.
              </p>
              <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
              <p style="color:#9ca3af;font-size:11px;text-align:center">© 2026 StageLink MA · stagelinkma.com</p>
            </div>
            """
        })
        print(f"[EMAIL] Success: {result}")
        return True
    except Exception as e:
        print(f"[EMAIL] Error type={type(e).__name__} msg={e}")
        return False
