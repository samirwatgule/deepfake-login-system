import os
import sys

# Add project root to sys.path so `api` package imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify
from flask_cors import CORS

from api.routes.auth_routes import auth_bp
from api.routes.admin_routes import admin_bp
from api.routes.detect_routes import detect_bp
from api.database import init_db

def create_app():
    app = Flask(__name__)
    
    # CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5173", "http://localhost:3000", "*"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Load config
    app.config['JWT_SECRET'] = os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-production')
    app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:1234@localhost:5432/quantumshield')
    app.config['GEO_API_URL'] = os.environ.get('GEO_API_URL', 'https://ipapi.co')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
    
    # Initialize database tables
    with app.app_context():
        try:
            init_db(app.config['DATABASE_URL'])
        except Exception as e:
            print(f"[DB] Warning: Could not initialize database: {e}")
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(detect_bp)
    
    # Health check
    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({
            "status": "ok", 
            "service": "QuantumShield API",
            "features": ["auth", "admin", "deepfake_detection", "risk_engine"]
        }), 200
    
    # Global error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "message": str(e)}), 400
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File too large. Maximum size is 16MB."}), 413
    
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500
    
    return app

# Entry point
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
