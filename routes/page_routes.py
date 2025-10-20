from flask import Blueprint, render_template, request

page_bp = Blueprint('pages', __name__)

@page_bp.route('/')
def index():
    return render_template('landing_page.html')

@page_bp.route('/dashboard')
def dashboard():
    section = request.args.get('section', 'overview')
    return render_template('dashboard.html', active_section=section)

@page_bp.route('/viability')
def viability():
    return render_template('viability.html')

@page_bp.route('/matching')
def matching():
    return render_template('matching.html')

@page_bp.route('/transport')
def transport():
    return render_template('transport.html')

@page_bp.route('/analytics')
def analytics():
    return render_template('analytics.html')

@page_bp.route('/assistant')
def assistant():
    return render_template('assistant.html')
