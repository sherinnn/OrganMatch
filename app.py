from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.secret_key = os.urandom(24)

    # Register blueprints
    from routes.api_routes import api_bp
    from routes.page_routes import page_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(page_bp)

    return app

# Create the app instance for Vercel
app = create_app()

# Vercel handler
def handler(request, *args, **kwargs):
    return app(request, *args, **kwargs)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
