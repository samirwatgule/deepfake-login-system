import re
import json
import functools
from flask import request, jsonify
import jwt
import os

def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength: min 6 chars."""
    if not password or len(password) < 6:
        return False
    return True

def _decode_token():
    """Extract and decode JWT from Authorization header."""
    auth_header = request.headers.get('Authorization', '')
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
    
    if not token:
        return None, (jsonify({"error": "Token is required"}), 401)
    
    try:
        secret = os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-production')
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, (jsonify({"error": "Token has expired"}), 401)
    except jwt.InvalidTokenError:
        return None, (jsonify({"error": "Invalid token"}), 401)

def jwt_required(f):
    """Decorator to require valid JWT token for protected routes."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        payload, error = _decode_token()
        if error:
            return error
        
        request.user_id = payload.get('user_id')
        request.user_email = payload.get('email')
        request.user_role = payload.get('role', 'user')
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Decorator to require valid JWT token with admin role."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        payload, error = _decode_token()
        if error:
            return error
        
        if payload.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        
        request.user_id = payload.get('user_id')
        request.user_email = payload.get('email')
        request.user_role = 'admin'
        return f(*args, **kwargs)
    return decorated

def get_client_ip():
    """Extract real client IP from request headers."""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    real_ip = request.headers.get('X-Real-IP', '')
    if real_ip:
        return real_ip
    return request.remote_addr or '127.0.0.1'
