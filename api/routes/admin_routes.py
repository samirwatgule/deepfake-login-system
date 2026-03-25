from flask import Blueprint, request, jsonify
import json
from api.utils.helpers import admin_required
from api.database import get_connection

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/api/admin/logs', methods=['GET'])
@admin_required
def get_login_logs():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        status_filter = request.args.get('status', '').upper()
        offset = (page - 1) * limit

        conn = get_connection()
        cur = conn.cursor()

        if status_filter in ('ALLOW', 'FLAG', 'BLOCK'):
            cur.execute("""
                SELECT id, user_id, email, ip_address, device_info, city, country,
                       typing_speed, device_risk, location_risk, behavior_risk, face_risk,
                       total_risk, decision, face_verdict, face_confidence,
                       face_image_path, is_suspicious, timestamp
                FROM login_logs WHERE decision = ?
                ORDER BY timestamp DESC LIMIT ? OFFSET ?
            """, (status_filter, limit, offset))
        else:
            cur.execute("""
                SELECT id, user_id, email, ip_address, device_info, city, country,
                       typing_speed, device_risk, location_risk, behavior_risk, face_risk,
                       total_risk, decision, face_verdict, face_confidence,
                       face_image_path, is_suspicious, timestamp
                FROM login_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?
            """, (limit, offset))

        rows = cur.fetchall()

        if status_filter in ('ALLOW', 'FLAG', 'BLOCK'):
            cur.execute("SELECT COUNT(*) as cnt FROM login_logs WHERE decision = ?", (status_filter,))
        else:
            cur.execute("SELECT COUNT(*) as cnt FROM login_logs")
        total = cur.fetchone()['cnt']

        conn.close()

        logs = [{
            'id': r['id'], 'user_id': r['user_id'], 'email': r['email'],
            'ip_address': r['ip_address'], 'device_info': r['device_info'],
            'city': r['city'], 'country': r['country'],
            'typing_speed': r['typing_speed'], 'device_risk': r['device_risk'],
            'location_risk': r['location_risk'], 'behavior_risk': r['behavior_risk'],
            'face_risk': r['face_risk'], 'total_risk': r['total_risk'],
            'decision': r['decision'], 'face_verdict': r['face_verdict'],
            'face_confidence': r['face_confidence'],
            'face_image_path': r['face_image_path'],
            'is_suspicious': bool(r['is_suspicious']),
            'timestamp': r['timestamp']
        } for r in rows]

        return jsonify({
            'logs': logs, 'total': total, 'page': page,
            'limit': limit, 'pages': (total + limit - 1) // limit
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch logs: {str(e)}"}), 500


@admin_bp.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_stats():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as cnt FROM login_logs")
        total = cur.fetchone()['cnt']

        cur.execute("SELECT decision, COUNT(*) as cnt FROM login_logs GROUP BY decision")
        decision_counts = {r['decision']: r['cnt'] for r in cur.fetchall()}

        cur.execute("SELECT AVG(total_risk) as avg_r FROM login_logs")
        avg_risk_row = cur.fetchone()
        avg_risk = round(avg_risk_row['avg_r'], 1) if avg_risk_row['avg_r'] else 0

        cur.execute("""
            SELECT AVG(device_risk) as a, AVG(location_risk) as b,
                   AVG(behavior_risk) as c, AVG(face_risk) as d
            FROM login_logs
        """)
        avg_row = cur.fetchone()

        cur.execute("SELECT COUNT(*) as cnt FROM login_logs WHERE face_verdict = 'FAKE'")
        deepfakes_blocked = cur.fetchone()['cnt']

        cur.execute("SELECT COUNT(*) as cnt FROM login_logs WHERE face_verdict = 'REAL'")
        real_faces = cur.fetchone()['cnt']

        cur.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'user'")
        total_users = cur.fetchone()['cnt']

        cur.execute("SELECT COUNT(*) as cnt FROM users WHERE is_blocked = 1")
        blocked_users = cur.fetchone()['cnt']

        cur.execute("SELECT COUNT(*) as cnt FROM login_logs WHERE is_suspicious = 1")
        suspicious_logins = cur.fetchone()['cnt']

        cur.execute("""
            SELECT id, email, total_risk, decision, city, country,
                   face_verdict, face_confidence, is_suspicious, timestamp
            FROM login_logs WHERE decision IN ('FLAG', 'BLOCK')
            ORDER BY timestamp DESC LIMIT 10
        """)
        suspicious = [{
            'id': r['id'], 'email': r['email'], 'total_risk': r['total_risk'],
            'decision': r['decision'], 'city': r['city'], 'country': r['country'],
            'face_verdict': r['face_verdict'], 'face_confidence': r['face_confidence'],
            'is_suspicious': bool(r['is_suspicious']),
            'timestamp': r['timestamp']
        } for r in cur.fetchall()]

        conn.close()

        return jsonify({
            'total_logins': total,
            'allowed': decision_counts.get('ALLOW', 0),
            'flagged': decision_counts.get('FLAG', 0),
            'blocked': decision_counts.get('BLOCK', 0),
            'avg_risk': avg_risk,
            'avg_device_risk': round(avg_row['a'], 1) if avg_row['a'] else 0,
            'avg_location_risk': round(avg_row['b'], 1) if avg_row['b'] else 0,
            'avg_behavior_risk': round(avg_row['c'], 1) if avg_row['c'] else 0,
            'avg_face_risk': round(avg_row['d'], 1) if avg_row['d'] else 0,
            'deepfakes_blocked': deepfakes_blocked,
            'real_faces': real_faces,
            'total_users': total_users,
            'blocked_users': blocked_users,
            'suspicious_logins': suspicious_logins,
            'recent_suspicious': suspicious
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch stats: {str(e)}"}), 500


@admin_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, email, role, is_blocked, home_city, home_country,
                   login_count, is_face_verified, face_attributes_json, created_at
            FROM users ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        conn.close()

        users = [{
            'id': r['id'],
            'name': r['name'] or '',
            'email': r['email'],
            'role': r['role'],
            'is_blocked': bool(r['is_blocked']),
            'home_city': r['home_city'],
            'home_country': r['home_country'],
            'login_count': r['login_count'],
            'is_face_verified': bool(r['is_face_verified']),
            'face_attributes': json.loads(r['face_attributes_json'] or '{}'),
            'created_at': r['created_at']
        } for r in rows]

        return jsonify({'users': users}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch users: {str(e)}"}), 500


@admin_bp.route('/api/admin/users/<int:user_id>/block', methods=['POST'])
@admin_required
def toggle_block_user(user_id):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT role, is_blocked FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify({"error": "User not found"}), 404
        if row['role'] == 'admin':
            conn.close()
            return jsonify({"error": "Cannot block admin users"}), 403

        new_status = 0 if row['is_blocked'] else 1
        cur.execute("UPDATE users SET is_blocked = ? WHERE id = ?", (new_status, user_id))
        conn.commit()
        conn.close()

        return jsonify({
            "message": f"User {'blocked' if new_status else 'unblocked'} successfully",
            "is_blocked": bool(new_status)
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update user: {str(e)}"}), 500


@admin_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Permanently delete a user and all associated logs."""
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()

        if not row:
            conn.close()
            return jsonify({"error": "User not found"}), 404
        if row['role'] == 'admin':
            conn.close()
            return jsonify({"error": "Cannot delete admin users"}), 403

        # Delete user (login_logs will cascade delete because of ON DELETE CASCADE in schema)
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500


@admin_bp.route('/api/admin/users/<int:user_id>/logs', methods=['GET'])
@admin_required
def get_user_logs(user_id):
    """Return all login logs for a specific user (admin view)."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        limit = int(request.args.get('limit', 30))

        cur.execute("""
            SELECT id, email, ip_address, city, country, device_risk, location_risk,
                   behavior_risk, face_risk, total_risk, decision, face_verdict,
                   face_confidence, face_image_path, is_suspicious, timestamp
            FROM login_logs WHERE user_id = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (user_id, limit))
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
            'timestamp': r['timestamp']
        } for r in rows]

        return jsonify({'logs': logs, 'user_id': user_id}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch user logs: {str(e)}"}), 500
