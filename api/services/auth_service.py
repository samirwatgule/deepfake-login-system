import bcrypt
import jwt
import os
import json
from datetime import datetime, timedelta, timezone
from api.database import get_connection, _get_cursor

def hash_password(password):
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def generate_token(user_id, email, role='user'):
    """Generate a JWT token with 24h expiry. Includes role for RBAC."""
    secret = os.environ.get('JWT_SECRET', 'dev-secret-key-change-in-production')
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24),
        'iat': datetime.now(timezone.utc)
    }
    return jwt.encode(payload, secret, algorithm='HS256')

def register_user(email, password, device_info, location, typing_speed, face_image_b64, name=''):
    """Register a new user with all baseline data. Saves face image to disk."""
    conn = get_connection()
    cur = _get_cursor(conn)

    try:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            conn.close()
            return None, "Email already registered"

        password_hash = hash_password(password)
        face_path_relative = ''
        face_embedding = ''
        face_attributes_json = '{}'

        # Save face image to disk if provided
        if face_image_b64:
            try:
                import base64
                import uuid
                from api.services.face_service import generate_face_embedding, get_face_attributes

                # Clean base64 and decode
                header, encoded = face_image_b64.split(",", 1) if "," in face_image_b64 else ("", face_image_b64)
                img_data = base64.b64decode(encoded)

                # Generate unique face attributes JSON
                face_attributes = get_face_attributes(img_data)
                face_attributes_json = json.dumps(face_attributes)

                # ENFORCE AI VERIFICATION ON REGISTRATION
                from api.services.face_service import analyze_face
                face_analysis = analyze_face(face_image_b64)
                if face_analysis.get('face_verdict') == 'FAKE':
                    conn.close()
                    return None, (
                        f"Registration rejected: Biometric identity verification failed. "
                        f"AI/Deepfake signature detected "
                        f"(Confidence: {face_analysis.get('face_confidence', 0)*100:.1f}%)."
                    )

                filename = f"{uuid.uuid4()}.jpg"
                upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'faces')
                os.makedirs(upload_dir, exist_ok=True)

                face_path = os.path.join(upload_dir, filename)
                with open(face_path, "wb") as f:
                    f.write(img_data)

                face_embedding = generate_face_embedding(face_image_b64)
                face_path_relative = f"api/static/uploads/faces/{filename}"

            except Exception as e:
                print(f"[AUTH] Failed to save register face: {e}")

        cur.execute("""
            INSERT INTO users (name, email, password_hash, role, registered_device, home_city, home_country,
                             avg_typing_speed, typing_variance, login_count, face_embedding,
                             face_attributes_json, is_face_verified)
            VALUES (%s, %s, %s, 'user', %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            name.strip() if name else '',
            email,
            password_hash,
            json.dumps(device_info) if isinstance(device_info, dict) else str(device_info),
            location.get('city', 'Unknown') if isinstance(location, dict) else 'Unknown',
            location.get('country', 'Unknown') if isinstance(location, dict) else 'Unknown',
            float(typing_speed) if typing_speed else 0.0,
            0.0,
            0,
            face_path_relative if face_path_relative else face_embedding,
            face_attributes_json,
            1 if face_image_b64 else 0
        ))

        user_id = cur.fetchone()['id']
        conn.commit()
        conn.close()

        token = generate_token(user_id, email, 'user')
        return {"user_id": user_id, "token": token, "email": email, "role": "user", "name": name.strip() if name else ''}, None

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return None, str(e)

def authenticate_user(email, password):
    """Verify user credentials. Returns user data or None."""
    conn = get_connection()
    cur = _get_cursor(conn)

    try:
        cur.execute("""
            SELECT id, name, email, password_hash, role, is_blocked, registered_device, home_city, home_country,
                   avg_typing_speed, typing_variance, login_count, face_embedding, is_face_verified, created_at
            FROM users WHERE email = %s
        """, (email,))

        row = cur.fetchone()
        conn.close()

        if not row:
            return None, "User not found"

        if not verify_password(password, row['password_hash']):
            return None, "Invalid password"

        if row['is_blocked']:
            return None, "Account has been blocked by administrator"

        user = {
            'id': row['id'],
            'name': row['name'] or '',
            'email': row['email'],
            'role': row['role'] or 'user',
            'is_blocked': bool(row['is_blocked']),
            'registered_device': row['registered_device'],
            'home_city': row['home_city'],
            'home_country': row['home_country'],
            'avg_typing_speed': row['avg_typing_speed'],
            'typing_variance': row['typing_variance'],
            'login_count': row['login_count'],
            'face_embedding': row['face_embedding'],
            'is_face_verified': bool(row['is_face_verified']),
            'created_at': str(row['created_at'])
        }

        return user, None

    except Exception as e:
        conn.close()
        return None, str(e)

def authenticate_admin(email, password):
    """Authenticate admin user. Only allows role='admin'."""
    user, error = authenticate_user(email, password)
    if error:
        return None, error
    if not user or user.get('role') != 'admin':
        return None, "Access denied. Admin credentials required."
    return user, None

def update_user_baseline(user_id, typing_speed):
    """Update user typing baseline after successful login."""
    conn = get_connection()
    cur = _get_cursor(conn)

    try:
        cur.execute("SELECT avg_typing_speed, typing_variance, login_count FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()

        if row:
            old_avg = row['avg_typing_speed'] or 0.0
            old_var = row['typing_variance'] or 0.0
            count = row['login_count'] or 0

            alpha = 0.3
            new_avg = alpha * typing_speed + (1 - alpha) * old_avg if count > 0 else typing_speed
            new_var = alpha * abs(typing_speed - new_avg) + (1 - alpha) * old_var if count > 0 else 0.0

            cur.execute("""
                UPDATE users SET avg_typing_speed = %s, typing_variance = %s, login_count = login_count + 1
                WHERE id = %s
            """, (new_avg, new_var, user_id))

            conn.commit()

        conn.close()

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"[AUTH] Baseline update error: {e}")

def get_user_profile(user_id):
    """Fetch full user profile including last login data."""
    conn = get_connection()
    cur = _get_cursor(conn)

    try:
        cur.execute("""
            SELECT id, name, email, role, home_city, home_country,
                   login_count, is_face_verified, is_blocked, created_at
            FROM users WHERE id = %s
        """, (user_id,))
        user = cur.fetchone()

        if not user:
            conn.close()
            return None, "User not found"

        # Get last login log
        cur.execute("""
            SELECT city, country, ip_address, total_risk, decision, face_verdict,
                   face_confidence, timestamp
            FROM login_logs WHERE user_id = %s
            ORDER BY timestamp DESC LIMIT 1
        """, (user_id,))
        last_log = cur.fetchone()

        # Determine security status
        cur.execute("""
            SELECT COUNT(*) as cnt FROM login_logs
            WHERE user_id = %s AND decision IN ('FLAG', 'BLOCK')
        """, (user_id,))
        suspicious_count = cur.fetchone()['cnt']

        conn.close()

        security_status = 'safe'
        if user['is_blocked']:
            security_status = 'blocked'
        elif suspicious_count > 0:
            security_status = 'suspicious'

        profile = {
            'id': user['id'],
            'name': user['name'] or '',
            'email': user['email'],
            'role': user['role'],
            'home_city': user['home_city'] or 'Unknown',
            'home_country': user['home_country'] or 'Unknown',
            'login_count': user['login_count'] or 0,
            'is_face_verified': bool(user['is_face_verified']),
            'is_blocked': bool(user['is_blocked']),
            'created_at': str(user['created_at']),
            'security_status': security_status,
        }

        if last_log:
            profile['last_login'] = {
                'city': last_log['city'],
                'country': last_log['country'],
                'ip_address': last_log['ip_address'],
                'total_risk': last_log['total_risk'],
                'decision': last_log['decision'],
                'face_verdict': last_log['face_verdict'],
                'face_confidence': last_log['face_confidence'],
                'timestamp': str(last_log['timestamp']),
            }

        return profile, None

    except Exception as e:
        conn.close()
        return None, str(e)
