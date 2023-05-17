from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = b'!yny\x99{\x88,F\x85\x19y\xd67yL'

    from routes.views import views
    app.register_blueprint(views, url_prefix='/')

    return app