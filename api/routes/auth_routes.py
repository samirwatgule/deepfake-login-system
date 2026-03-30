import json
import os
import math
from datetime import datetime
from flask import Blueprint, request, jsonify
from api.services.auth_service import (
    register_user, authenticate_user, authenticate_admin,
    generate_token, update_user_baseline, get_user_profile
)
from api.services.device_service import compute_device_hash, get_geolocation, compute_device_risk
from api.services.behavior_service import compute_behavior_score
from api.services.face_service import analyze_face, generate_face_embedding
from api.services.risk_engine import compute_total_risk
from api.utils.helpers import validate_email, validate_password, get_client_ip, jwt_required
from api.database import get_connection, _get_cursor

auth_bp = Blueprint('auth', __name__)


# ─── Haversine distance helper ───────────────────────────────────────────────
def _haversine_km(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance (km) between two GPS coordinates."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _check_impossible_travel(user_id, current_lat, current_lon, current_time):
    """
    Check if current login location is impossibly far from the last login.
    Returns (is_suspicious: bool, message: str).
    """
    if not current_lat or not current_lon:
        return False, ''
    try:
        conn = get_connection()
        cur = _get_cursor(conn)
        cur.execute("""
            SELECT latitude, longitude, timestamp FROM login_logs
            WHERE user_id = %s AND latitude != 0 AND longitude != 0
            ORDER BY timestamp DESC LIMIT 1
        """, (user_id,))
        row = cur.fetchone()
        conn.close()

        if not row or not row['latitude']:
            return False, ''

        prev_lat, prev_lon = row['latitude'], row['longitude']
        prev_time = row['timestamp']
        if isinstance(prev_time, str):
            prev_time = datetime.fromisoformat(prev_time)
        if current_time.tzinfo and prev_time.tzinfo is None:
            prev_time = prev_time.replace(tzinfo=current_time.tzinfo)

        distance_km = _haversine_km(prev_lat, prev_lon, current_lat, current_lon)
        hours_diff = max((current_time - prev_time).total_seconds() / 3600, 0.001)
        speed_kmh = distance_km / hours_diff

        # Human travel: max ~900 km/h (commercial flight)
        if speed_kmh > 900 and distance_km > 200:
            return True, (
                f"⚠️ Impossible travel detected: {distance_km:.0f} km in "
                f"{hours_diff:.1f}h ({speed_kmh:.0f} km/h) — likely account compromise"
            )
    except Exception as e:
        print(f"[AUTH] Impossible travel check error: {e}")
    return False, ''


# ─── Register ─────────────────────────────────────────────────────────────────
@auth_bp.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        face_image = data.get('faceImage', '')
        device_info = data.get('deviceInfo', {})
        typing_speed = data.get('typingSpeed', 0)

        if not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        if not validate_password(password):
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        client_ip = get_client_ip()
        coords = data.get('coords')  # {latitude, longitude}
        location = get_geolocation(client_ip, coords)

        result, error = register_user(
            email=email, password=password, device_info=device_info,
            location=location, typing_speed=float(typing_speed) if typing_speed else 0.0,
            face_image_b64=face_image, name=name
        )

        if error:
            return jsonify({"error": error}), 400

        return jsonify({
            "message": "Registration successful",
            "user_id": result['user_id'],
            "token": result['token'],
            "email": result['email'],
            "name": result.get('name', ''),
            "role": result['role']
        }), 201
    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


# ─── Login ────────────────────────────────────────────────────────────────────
@auth_bp.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        email = data.get('email', '').strip()
        password = data.get('password', '')
        face_image = data.get('faceImage', '')
        device_info = data.get('deviceInfo', {})
        typing_speed = data.get('typingSpeed', 0)

        user, error = authenticate_user(email, password)
        if error:
            return jsonify({"error": error}), 401

        client_ip = get_client_ip()
        coords = data.get('coords')
        current_location = get_geolocation(client_ip, coords)

        current_device_hash = compute_device_hash(device_info)
        device_result = compute_device_risk(user, current_device_hash, current_location)

        device_changed = device_result['device_risk'] > 0
        location_changed = device_result['location_risk'] > 0
        behavior_result = compute_behavior_score(
            user, float(typing_speed) if typing_speed else 0.0,
            device_changed, location_changed
        )

        face_result = analyze_face(face_image, user.get('face_embedding', ''))
        risk_result = compute_total_risk(device_result, behavior_result, face_result)

        # Impossible travel check
        current_lat = coords.get('latitude') if coords else None
        current_lon = coords.get('longitude') if coords else None
        is_suspicious, travel_msg = _check_impossible_travel(
            user['id'], current_lat, current_lon, datetime.utcnow()
        )
        if is_suspicious:
            risk_result['details'].append(travel_msg)
            risk_result['total_risk'] = min(risk_result['total_risk'] + 20, 100)
            if risk_result['decision'] == 'ALLOW':
                risk_result['decision'] = 'FLAG'

        token = generate_token(user['id'], user['email'], user.get('role', 'user'))

        if typing_speed:
            update_user_baseline(user['id'], float(typing_speed))

        # Save login face attempt for audit
        login_face_path = ''
        if face_image:
            try:
                import base64, uuid
                header, encoded = face_image.split(",", 1) if "," in face_image else ("", face_image)
                img_data = base64.b64decode(encoded)
                filename = f"login_{uuid.uuid4()}.jpg"
                upload_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'api', 'static', 'uploads', 'login_attempts'
                )
                os.makedirs(upload_dir, exist_ok=True)
                with open(os.path.join(upload_dir, filename), "wb") as f:
                    f.write(img_data)
                login_face_path = f"api/static/uploads/login_attempts/{filename}"
            except Exception as e:
                print(f"[AUTH] Failed to save login face: {e}")

        log_login_attempt(
            user_id=user['id'], email=email, ip_address=client_ip,
            device_info=json.dumps(device_info),
            city=current_location.get('city', 'Unknown'),
            country=current_location.get('country', 'Unknown'),
            latitude=current_lat or 0.0,
            longitude=current_lon or 0.0,
            typing_speed=float(typing_speed) if typing_speed else 0.0,
            risk_result=risk_result,
            face_verdict=face_result.get('face_verdict', ''),
            face_confidence=face_result.get('face_confidence', 0.0),
            face_image_path=login_face_path,
            is_suspicious=1 if is_suspicious else 0
        )

        return jsonify({
            "message": "Authentication complete",
            "token": token,
            "email": user['email'],
            "name": user.get('name', ''),
            "role": user.get('role', 'user'),
            "risk": {
                "device_risk": risk_result['device_risk'],
                "location_risk": risk_result['location_risk'],
                "behavior_risk": risk_result['behavior_risk'],
                "face_risk": risk_result['face_risk'],
                "total_risk": risk_result['total_risk'],
                "decision": risk_result['decision'],
                "details": risk_result['details'],
                "face_verdict": face_result.get('face_verdict', ''),
                "face_confidence": face_result.get('face_confidence', 0.0)
            }
        }), 200
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500


# ─── Admin Login ──────────────────────────────────────────────────────────────
@auth_bp.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        email = data.get('email', '').strip()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400

        user, error = authenticate_admin(email, password)
        if error:
            return jsonify({"error": error}), 401

        token = generate_token(user['id'], user['email'], 'admin')

        return jsonify({
            "message": "Admin authentication successful",
            "token": token,
            "email": user['email'],
            "name": user.get('name', 'Admin'),
            "role": "admin"
        }), 200
    except Exception as e:
        return jsonify({"error": f"Admin login failed: {str(e)}"}), 500


# ─── User Profile ─────────────────────────────────────────────────────────────
@auth_bp.route('/api/user/profile', methods=['GET'])
@jwt_required
def get_profile():
    try:
        profile, error = get_user_profile(request.user_id)
        if error:
            return jsonify({"error": error}), 404
        return jsonify(profile), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch profile: {str(e)}"}), 500


# ─── User Logs ────────────────────────────────────────────────────────────────
@auth_bp.route('/api/user/logs', methods=['GET'])
@jwt_required
def get_user_logs():
    try:
        conn = get_connection()
        cur = _get_cursor(conn)
        limit = int(request.args.get('limit', 20))

        cur.execute("""
            SELECT id, email, ip_address, city, country, device_risk, location_risk,
                   behavior_risk, face_risk, total_risk, decision, face_verdict,
                   face_confidence, face_image_path, is_suspicious, timestamp
            FROM login_logs
            WHERE user_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """, (request.user_id, limit))

        rows = cur.fetchall()
        conn.close()

        logs = [{
            'id': r['id'], 'email': r['email'], 'ip_address': r['ip_address'],
            'city': r['city'], 'country': r['country'],
            'device_risk': r['device_risk'], 'location_risk': r['location_risk'],
            'behavior_risk': r['behavior_risk'], 'face_risk': r['face_risk'],
            'total_risk': r['total_risk'], 'decision': r['decision'],
            'face_verdict': r['face_verdict'], 'face_confidence': r['face_confidence'],
            'face_image_path': r['face_image_path'],
            'is_suspicious': bool(r['is_suspicious']),
            'timestamp': str(r['timestamp'])
        } for r in rows]

        return jsonify({'logs': logs}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch logs: {str(e)}"}), 500


# ─── Internal: log_login_attempt ─────────────────────────────────────────────
def log_login_attempt(user_id, email, ip_address, device_info, city, country,
                      latitude, longitude, typing_speed, risk_result,
                      face_verdict='', face_confidence=0.0,
                      face_image_path='', is_suspicious=0):
    try:
        conn = get_connection()
        cur = _get_cursor(conn)
        cur.execute("""
            INSERT INTO login_logs
            (user_id, email, ip_address, device_info, city, country,
             latitude, longitude, typing_speed,
             device_risk, location_risk, behavior_risk, face_risk, total_risk, decision,
             face_verdict, face_confidence, face_image_path, is_suspicious)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, email, ip_address, device_info, city, country,
            latitude, longitude, typing_speed,
            risk_result['device_risk'], risk_result['location_risk'],
            risk_result['behavior_risk'], risk_result['face_risk'],
            risk_result['total_risk'], risk_result['decision'],
            face_verdict, face_confidence, face_image_path, is_suspicious
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[LOG] Failed to log login attempt: {e}")
