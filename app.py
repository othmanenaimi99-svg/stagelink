from flask import Flask, session, redirect, url_for
from flask_login import LoginManager
from models import db, Utilisateur
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'

    @login_manager.user_loader
    def load_user(user_id):
        return Utilisateur.query.get(int(user_id))

    from routes.auth import auth_bp
    from routes.etudiant import etudiant_bp
    from routes.entreprise import entreprise_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(etudiant_bp)
    app.register_blueprint(entreprise_bp)
    app.register_blueprint(admin_bp)

    @app.route('/')
    def index():
        from flask_login import current_user
        if current_user.is_authenticated:
            if current_user.role == 'ETUDIANT':
                return redirect(url_for('etudiant.dashboard'))
            elif current_user.role == 'ENTREPRISE':
                return redirect(url_for('entreprise.dashboard'))
            elif current_user.role == 'ADMIN':
                return redirect(url_for('admin.dashboard'))
        from flask import render_template
        return render_template('index.html')

    @app.route('/lang/<code>')
    def set_lang(code):
        from flask import request
        if code in ('fr', 'en'):
            session['lang'] = code
        return redirect(request.referrer or url_for('index'))

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        notif_count = 0
        if current_user.is_authenticated:
            notif_count = current_user.notifications.filter_by(est_lue=False).count()
        return dict(notif_count=notif_count, lang=session.get('lang', 'fr'))

    return app


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
