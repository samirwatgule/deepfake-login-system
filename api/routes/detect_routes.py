import base64
import uuid
import os
from flask import Blueprint, request, jsonify
from api.services.face_service import detect_deepfake_image
from api.utils.helpers import jwt_required

detect_bp = Blueprint('detect', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'detect')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@detect_bp.route('/api/detect/image', methods=['POST'])
@jwt_required
def detect_image():
    """
    Deepfake detection on an uploaded image file.
    Uses the XceptionNet CNN model for real inference.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid format. Use JPEG, PNG, WebP, BMP, or TIFF.'}), 400
    
    try:
        image_bytes = file.read()
        
        if len(image_bytes) > 10 * 1024 * 1024:
            return jsonify({'error': 'Image must be under 10MB'}), 400
        
        result = detect_deepfake_image(image_bytes)
        
        return jsonify({
            'label': result['label'],
            'confidence': result['confidence'],
            'raw_score': result['raw_score'],
            'method': result['method']
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500


@detect_bp.route('/api/detect/webcam', methods=['POST'])
@jwt_required
def detect_webcam():
    """
    Deepfake detection on a webcam capture (base64 encoded).
    Uses the XceptionNet CNN model for real inference.
    """
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400
        
        image_b64 = data['image']
        
        # Clean base64 string
        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]
        
        image_bytes = base64.b64decode(image_b64)
        
        result = detect_deepfake_image(image_bytes)
        
        return jsonify({
            'label': result['label'],
            'confidence': result['confidence'],
            'raw_score': result['raw_score'],
            'method': result['method']
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Detection failed: {str(e)}'}), 500
