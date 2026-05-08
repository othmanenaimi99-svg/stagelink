import os
import random
import json
import urllib.request


def generate_code():
    return str(random.randint(100000, 999999))


def send_verification_code(to_email, code, nom=''):
    api_key = os.environ.get('BREVO_API_KEY')

    print(f"[EMAIL] to={to_email} key_set={bool(api_key)}")

    if not api_key:
        print("[EMAIL] BREVO_API_KEY manquant")
        return False

    payload = {
        "sender": {"name": "StageLink MA", "email": "othmanenaimi99@gmail.com"},
        "to": [{"email": to_email}],
        "subject": f"{code} — Code de vérification StageLink MA",
        "htmlContent": f"""
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
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            'https://api.brevo.com/v3/smtp/email',
            data=data,
            headers={
                'api-key': api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            result = response.read()
            print(f"[EMAIL] Success: {result}")
            return True
    except Exception as e:
        print(f"[EMAIL] Error {type(e).__name__}: {e}")
        return False
