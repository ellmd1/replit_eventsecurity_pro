# Make routes a proper Python package
from flask import Blueprint

# Import blueprints
from .auth import bp as auth_bp

# Register blueprints
blueprints = [auth_bp]

# This is the main routes blueprint that will contain non-auth routes
main = Blueprint('main', __name__)

@main.route('/')
def index():
    from flask import redirect, url_for
    return redirect(url_for('auth.login'))

blueprints.append(main)