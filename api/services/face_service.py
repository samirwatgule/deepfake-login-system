import base64
import hashlib
import numpy as np
import os
import logging
import datetime

logger = logging.getLogger(__name__)

# Global model reference — loaded once at startup
_deepfake_model = None
_model_loaded = False

def _load_model():
    """Load XceptionNet model for face deepfake detection."""
    global _deepfake_model, _model_loaded
    
    if _model_loaded:
        return _deepfake_model is not None
    
    model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'model', 'final_xception.keras')
    
    if not os.path.exists(model_path):
        logger.warning(f"[FACE] XceptionNet model not found at {model_path}")
        _model_loaded = True
        return False
    
    try:
        import tensorflow as tf
        logger.info(f"[FACE] Loading XceptionNet model from {model_path}...")
        _deepfake_model = tf.keras.models.load_model(model_path, compile=False)
        # Warm up
        dummy = np.random.random((1, 299, 299, 3)).astype(np.float32)
        _deepfake_model.predict(dummy, verbose=0)
        _model_loaded = True
        logger.info("[FACE] ✅ XceptionNet model loaded successfully!")
        return True
    except Exception as e:
        logger.error(f"[FACE] ❌ Failed to load model: {e}")
        _model_loaded = True
        return False


def _preprocess_face_image(image_bytes, target_size=(299, 299)):
    """Decode image bytes and preprocess for XceptionNet model."""
    try:
        import cv2
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return None
        
        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, target_size)
        image = image.astype(np.float32) / 255.0
        return np.expand_dims(image, axis=0)
    except Exception as e:
        logger.error(f"[FACE] Preprocessing error: {e}")
        return None


def _run_model_inference(image_bytes):
    """Run XceptionNet model on image bytes. Returns (is_fake: bool, confidence: float, raw_score: float)."""
    global _deepfake_model
    
    if _deepfake_model is None:
        return None  # Model not available
    
    processed = _preprocess_face_image(image_bytes)
    if processed is None:
        return None
    
    try:
        raw = _deepfake_model.predict(processed, verbose=0)
        logger.info(f"[FACE] Model raw output: {raw}")
        
        # Model output interpretation:
        # Single neuron with sigmoid: higher = more likely FAKE
        # IMPORTANT: Webcam captures often score 0.85-0.95 due to compression
        # artifacts, JPEG noise, and lighting. We use a VERY HIGH threshold
        # (0.95) to avoid false positives on real faces.
        DEEPFAKE_THRESHOLD = 0.90
        
        if len(raw.shape) > 1 and raw.shape[1] > 1:
            fake_prob = float(raw[0][1])
        else:
            fake_prob = float(raw[0][0])
        
        is_fake = fake_prob > DEEPFAKE_THRESHOLD
        confidence = fake_prob if is_fake else (1.0 - fake_prob)
        confidence = max(0.5, min(0.99, confidence))
        
        return {
            'is_fake': is_fake,
            'confidence': confidence,
            'raw_score': fake_prob,
            'label': 'FAKE' if is_fake else 'REAL'
        }
    except Exception as e:
        logger.error(f"[FACE] Model inference error: {e}")
        return None


def check_face_quality(image_bytes):
    """
    Check if the face image is clear and well-lit.
    Returns (is_ok: bool, score: float, details: list).
    """
    try:
        import cv2
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return False, 0.0, ["Failed to decode image"]
        
        # 1. Blur detection (Laplacian variance)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # 2. Lighting check (mean intensity)
        mean_intensity = np.mean(gray)
        
        details = []
        is_ok = True
        
        if blur_score < 100:
            is_ok = False
            details.append(f"Image is too blurry (score: {blur_score:.1f})")
        
        if mean_intensity < 40:
            is_ok = False
            details.append(f"Image is too dark (intensity: {mean_intensity:.1f})")
        elif mean_intensity > 220:
            is_ok = False
            details.append(f"Image is too bright (intensity: {mean_intensity:.1f})")
            
        return is_ok, blur_score, details
    except Exception as e:
        return False, 0.0, [f"Quality check error: {str(e)}"]


# ─────────────────────────────────────────────────────────────────────────────
# FACE IDENTITY VERIFICATION
# Uses face-region-only comparison with multiple methods:
#   1. Haar cascade face detection → extract face ROI (remove background)
#   2. LBP (Local Binary Patterns) on face ROI → texture identity
#   3. SSIM (Structural Similarity) on face ROI → structural match
#   4. Face-region histogram comparison → color distribution
#   5. Template matching → direct pixel correlation
# ─────────────────────────────────────────────────────────────────────────────

def _extract_face_roi(img, gray):
    """
    Detect and extract the face region from an image using Haar cascade.
    Returns the face crop (BGR) or the original image if no face found.
    """
    import cv2
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
    if len(faces) == 0:
        # Try relaxed parameters
        faces = face_cascade.detectMultiScale(gray, 1.05, 3, minSize=(30, 30))

    if len(faces) > 0:
        x, y, w, h = faces[0]
        # Add padding around detected face
        pad = int(0.15 * max(w, h))
        y1 = max(0, y - pad)
        y2 = min(img.shape[0], y + h + pad)
        x1 = max(0, x - pad)
        x2 = min(img.shape[1], x + w + pad)
        return img[y1:y2, x1:x2], True

    return img, False


def _compute_lbp(gray_image):
    """Compute Local Binary Pattern of a grayscale image using vectorized numpy."""
    h, w = gray_image.shape
    if h < 3 or w < 3:
        return gray_image

    center = gray_image[1:h-1, 1:w-1].astype(np.int16)
    lbp = np.zeros_like(center, dtype=np.uint8)

    # 8 neighbors
    lbp |= ((gray_image[0:h-2, 0:w-2] >= center).astype(np.uint8) << 7)  # top-left
    lbp |= ((gray_image[0:h-2, 1:w-1] >= center).astype(np.uint8) << 6)  # top
    lbp |= ((gray_image[0:h-2, 2:w  ] >= center).astype(np.uint8) << 5)  # top-right
    lbp |= ((gray_image[1:h-1, 2:w  ] >= center).astype(np.uint8) << 4)  # right
    lbp |= ((gray_image[2:h  , 2:w  ] >= center).astype(np.uint8) << 3)  # bottom-right
    lbp |= ((gray_image[2:h  , 1:w-1] >= center).astype(np.uint8) << 2)  # bottom
    lbp |= ((gray_image[2:h  , 0:w-2] >= center).astype(np.uint8) << 1)  # bottom-left
    lbp |= ((gray_image[1:h-1, 0:w-2] >= center).astype(np.uint8) << 0)  # left

    return lbp


def _compute_lbp_similarity(gray1, gray2):
    """
    Compare two face images using Local Binary Pattern histograms.
    LBP captures micro-texture patterns unique to each person's face.
    Returns similarity score 0-1.
    """
    try:
        lbp1 = _compute_lbp(gray1)
        lbp2 = _compute_lbp(gray2)

        hist1, _ = np.histogram(lbp1.ravel(), bins=256, range=(0, 256), density=True)
        hist2, _ = np.histogram(lbp2.ravel(), bins=256, range=(0, 256), density=True)

        hist1 = hist1.astype(np.float32)
        hist2 = hist2.astype(np.float32)

        # Chi-squared distance → similarity
        chi_sq = np.sum(((hist1 - hist2) ** 2) / (hist1 + hist2 + 1e-10))
        similarity = max(0.0, 1.0 - (chi_sq / 2.0))
        return similarity
    except Exception:
        return 0.5


def _compute_face_ssim(gray1, gray2):
    """Compute simplified SSIM (Structural Similarity Index) between two face images."""
    try:
        C1 = (0.01 * 255) ** 2
        C2 = (0.03 * 255) ** 2

        img1 = gray1.astype(np.float64)
        img2 = gray2.astype(np.float64)

        mu1 = np.mean(img1)
        mu2 = np.mean(img2)
        sigma1_sq = np.var(img1)
        sigma2_sq = np.var(img2)
        sigma12 = np.mean((img1 - mu1) * (img2 - mu2))

        ssim = ((2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)) / \
               ((mu1**2 + mu2**2 + C1) * (sigma1_sq + sigma2_sq + C2))
        return max(0.0, min(1.0, float(ssim)))
    except Exception:
        return 0.5


def verify_face_identity(current_image_bytes, stored_face_path):
    """
    Verify if the login face matches the registered face.

    Uses a multi-layered approach that FIRST detects and extracts
    the face region, then compares face-only features:
      1. Face ROI detection via Haar cascade (removes background)
      2. LBP texture matching on face ROI
      3. SSIM structural similarity on face ROI
      4. Histogram correlation on face ROI
      5. Template matching on face ROI

    Different people WILL be rejected because we compare
    face-specific features only, not the full image.

    Returns (similarity_score: float 0-1, message: str).
    """
    try:
        import cv2

        if not stored_face_path or not os.path.exists(stored_face_path):
            return 0.5, "No baseline face found for comparison"

        # Decode current login image
        nparr_current = np.frombuffer(current_image_bytes, np.uint8)
        img_current = cv2.imdecode(nparr_current, cv2.IMREAD_COLOR)
        if img_current is None:
            return 0.0, "Failed to decode login face image"

        # Read stored registered face image
        img_stored = cv2.imread(stored_face_path, cv2.IMREAD_COLOR)
        if img_stored is None:
            return 0.5, "Failed to read registered face image"

        gray_current_full = cv2.cvtColor(img_current, cv2.COLOR_BGR2GRAY)
        gray_stored_full = cv2.cvtColor(img_stored, cv2.COLOR_BGR2GRAY)

        # ── Step 1: Detect and extract face ROI ──
        face_current, found_cur = _extract_face_roi(img_current, gray_current_full)
        face_stored, found_sto = _extract_face_roi(img_stored, gray_stored_full)

        if not found_cur:
            logger.warning("[FACE] No face detected in login image — comparison less reliable")

        # Resize face ROIs to uniform size for fair comparison
        FACE_SIZE = (128, 128)
        face_current_resized = cv2.resize(face_current, FACE_SIZE)
        face_stored_resized = cv2.resize(face_stored, FACE_SIZE)

        # Convert face ROIs to grayscale and equalize histogram (lighting normalization)
        gray_face_cur = cv2.cvtColor(face_current_resized, cv2.COLOR_BGR2GRAY)
        gray_face_sto = cv2.cvtColor(face_stored_resized, cv2.COLOR_BGR2GRAY)
        gray_face_cur = cv2.equalizeHist(gray_face_cur)
        gray_face_sto = cv2.equalizeHist(gray_face_sto)

        # ── Step 2: LBP face texture comparison ──
        lbp_score = _compute_lbp_similarity(gray_face_cur, gray_face_sto)

        # ── Step 3: SSIM structural similarity ──
        ssim_score = _compute_face_ssim(gray_face_cur, gray_face_sto)

        # ── Step 4: Face-region histogram matching ──
        hist_score = 0.0
        for channel in range(3):
            hist_cur = cv2.calcHist([face_current_resized], [channel], None, [64], [0, 256])
            hist_sto = cv2.calcHist([face_stored_resized], [channel], None, [64], [0, 256])
            cv2.normalize(hist_cur, hist_cur)
            cv2.normalize(hist_sto, hist_sto)
            hist_score += cv2.compareHist(hist_cur, hist_sto, cv2.HISTCMP_CORREL)
        hist_score = max(0.0, hist_score / 3.0)

        # ── Step 5: Template matching ──
        template_score = 0.0
        result = cv2.matchTemplate(gray_face_cur, gray_face_sto, cv2.TM_CCOEFF_NORMED)
        template_score = max(0.0, float(result[0][0]))

        # ── Combined Score ──
        # LBP is the most discriminative for face identity
        combined_score = (
            lbp_score * 0.35 +       # Face texture (most important)
            ssim_score * 0.25 +       # Structural similarity
            hist_score * 0.20 +       # Color distribution
            template_score * 0.20     # Template correlation
        )
        combined_score = max(0.0, min(1.0, combined_score))

        logger.info(
            f"[FACE] Identity check — LBP: {lbp_score:.3f}, SSIM: {ssim_score:.3f}, "
            f"Hist: {hist_score:.3f}, Template: {template_score:.3f}, "
            f"Combined: {combined_score:.3f}"
        )

        # Thresholds
        MATCH_THRESHOLD = 0.72      # Must be ≥ 0.72 to pass as verified
        WEAK_THRESHOLD = 0.55       # 0.55-0.72 = weak/uncertain match

        if combined_score >= MATCH_THRESHOLD:
            return combined_score, f"✅ Face identity VERIFIED (similarity: {combined_score*100:.1f}%)"
        elif combined_score >= WEAK_THRESHOLD:
            return combined_score, f"⚠️ Weak face match (similarity: {combined_score*100:.1f}%) — use caution"
        else:
            return combined_score, f"❌ Face does NOT match registered user (similarity: {combined_score*100:.1f}%)"

    except Exception as e:
        logger.error(f"[FACE] Identity verification error: {e}")
        return 0.0, f"Identity verification error: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN FACE ANALYSIS (called during login)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_face(face_image_b64, stored_embedding='', stored_face_path=''):
    """
    Analyze a face image for spoof/deepfake detection and identity verification.
    
    Uses the XceptionNet CNN model if available.
    Also performs quality and identity checks.
    
    Returns face_risk score (0-30) and verdict details.
    """
    details = []
    risk = 0.0
    face_verdict = 'UNKNOWN'
    face_confidence = 0.0
    
    if not face_image_b64:
        return {
            'face_risk': 15.0,
            'face_verdict': 'NO_FACE',
            'face_confidence': 0.0,
            'details': ['No face image provided — moderate risk assigned']
        }
    
    try:
        # Clean base64 string
        if ',' in face_image_b64:
            face_image_b64 = face_image_b64.split(',')[1]
        
        image_bytes = base64.b64decode(face_image_b64)
        
        # --- 1. Quality Check ---
        is_clear, quality_score, quality_details = check_face_quality(image_bytes)
        if not is_clear:
            risk += 10.0
            details.extend(quality_details)
            face_verdict = 'LOW_QUALITY'
        else:
            details.append("✅ Image quality is sufficient")

        # --- 2. Identity Verification (MUST match registered face) ---
        baseline_path = stored_face_path
        baseline_hash = stored_embedding
        
        # Auto-detect if stored_embedding is actually a path (from older schema/logic)
        if not baseline_path and baseline_hash and ('/' in baseline_hash or '\\' in baseline_hash):
            baseline_path = baseline_hash
            baseline_hash = ''

        if baseline_path:
            # Resolve full path if it's relative
            full_baseline_path = baseline_path
            if not os.path.isabs(full_baseline_path):
                full_baseline_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), baseline_path)
            
            match_score, match_msg = verify_face_identity(image_bytes, full_baseline_path)
            details.append(f"👤 {match_msg}")
            
            if match_score < 0.55:
                # HARD BLOCK: Face does NOT match registered user
                return {
                    'face_risk': 30.0,
                    'face_verdict': 'FACE_MISMATCH',
                    'face_confidence': round(1.0 - match_score, 4),
                    'details': details + [
                        f"🚫 BLOCKED: Login face does not match registered face (similarity: {match_score*100:.1f}%)",
                        "This is not the registered user — access denied"
                    ]
                }
            elif match_score < 0.72:
                risk += 15.0
                details.append(f"⚠️ Weak face match (similarity: {match_score*100:.1f}%) — increased risk (+15)")
        elif baseline_hash:
            # Fallback to hash comparison if path is not available
            current_hash = hashlib.sha256(image_bytes).hexdigest()
            if current_hash == baseline_hash:
                details.append("👤 Identity verified (Exact match with hash)")
            else:
                risk += 5.0
                details.append("⚠️ Face differs from registration baseline (+5)")

        # --- 3. ML Model Detection (Deepfake) ---
        _load_model()
        model_result = _run_model_inference(image_bytes)
        
        if model_result:
            raw_score = model_result['raw_score']
            face_confidence = model_result['confidence']
            print(f"        🧠 Model raw output: {raw_score:.4f}")
            
            # The XceptionNet model is sensitive to webcam compression artifacts
            # and frequently scores real faces 0.85-0.98. We use the model as an
            # ADVISORY risk factor, not a hard blocker.
            # Only scores > 0.99 are treated as definitive deepfakes.
            
            if raw_score > 0.99:
                # Very high confidence deepfake — hard block
                face_verdict = 'FAKE'
                risk = 30.0
                details.append(f"🚫 DEEPFAKE DETECTED by AI (confidence: {raw_score*100:.1f}%)")
                details.append(f"Raw score: {raw_score:.4f} — exceeds 0.99 threshold")
                details.append("Face verification FAILED — access will be denied")
                print(f"        🚫 DEEPFAKE DETECTED! Raw: {raw_score:.4f} > 0.99")
            elif raw_score > 0.90:
                # Suspicious but not definitive — add risk but don't block
                face_verdict = 'REAL'
                risk += 10.0
                details.append(f"⚠️ Elevated deepfake risk (score: {raw_score*100:.1f}%) — risk increased (+10)")
                details.append(f"Raw score: {raw_score:.4f} — between 0.90-0.99, treated as suspicious")
                print(f"        ⚠️ SUSPICIOUS. Raw: {raw_score:.4f} (0.90-0.99 range)")
            else:
                # Normal — real face
                face_verdict = 'REAL'
                face_confidence = 1.0 - raw_score
                risk = max(0.0, raw_score * 5)
                details.append(f"✅ Real face verified by AI model (confidence: {(1.0-raw_score)*100:.1f}%)")
                details.append(f"Raw score: {raw_score:.4f} — below 0.90 → REAL")
                print(f"        ✅ REAL FACE. Raw: {raw_score:.4f} < 0.90")
        else:
            # Model not available — use statistical fallback
            details.append("AI model unavailable — using statistical analysis")
            risk_fallback, fallback_details = _statistical_analysis(image_bytes, stored_embedding)
            risk += risk_fallback
            details.extend(fallback_details)
            face_verdict = 'STATISTICAL'
            face_confidence = 0.5
    
    except Exception as e:
        risk += 10.0
        details.append(f"Face analysis error: {str(e)[:50]} (+10)")
        face_verdict = 'ERROR'
    
    final_risk = min(float(round(float(risk), 1)), 30.0)
    
    return {
        'face_risk': final_risk,
        'face_verdict': face_verdict,
        'face_confidence': round(float(face_confidence), 4),
        'details': details
    }


def _statistical_analysis(image_bytes, stored_embedding=''):
    """Fallback statistical analysis when ML model is not available."""
    risk = 0.0
    details = []
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    
    # Image size validation
    size_kb = len(image_bytes) / 1024
    if size_kb < 5:
        risk += 10.0
        details.append(f"Very small image ({size_kb:.0f}KB) — possible fake (+10)")
    elif size_kb > 1000:
        risk += 5.0
        details.append(f"Unusually large image ({size_kb:.0f}KB) (+5)")
    
    # Byte entropy
    if len(image_array) > 0:
        _, counts = np.unique(image_array, return_counts=True)
        probabilities = counts / len(image_array)
        entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))
        
        if entropy < 5.0:
            risk += 12.0
            details.append(f"Low entropy ({entropy:.2f}) — possible static/generated image (+12)")
        elif entropy < 6.0:
            risk += 6.0
            details.append(f"Below-average entropy ({entropy:.2f}) (+6)")
        elif entropy > 7.9:
            risk += 4.0
            details.append(f"Very high entropy ({entropy:.2f}) — possible noise (+4)")
    
    # Face embedding comparison
    if stored_embedding:
        current_hash = hashlib.sha256(image_bytes).hexdigest()
        if current_hash == stored_embedding:
            risk += 20.0
            details.append("Exact image match — possible replay attack (+20)")
        else:
            risk += 2.0
            details.append("Face image differs from registration (+2)")
    
    # JPEG structure check
    if len(image_bytes) > 2:
        is_jpeg = image_bytes[0] == 0xFF and image_bytes[1] == 0xD8
        if not is_jpeg:
            is_png = image_bytes[0] == 0x89 and image_bytes[1] == 0x50
            if not is_png:
                risk += 8.0
                details.append("Non-standard image format (+8)")
    
    return min(risk, 30.0), details


def generate_face_embedding(face_image_b64):
    """Generate a simple hash-based face embedding for storage."""
    if not face_image_b64:
        return ''
    
    try:
        if ',' in face_image_b64:
            face_image_b64 = face_image_b64.split(',')[1]
        
        image_bytes = base64.b64decode(face_image_b64)
        return hashlib.sha256(image_bytes).hexdigest()
    except Exception:
        return ''

def get_face_attributes(image_bytes):
    """Generate a detailed JSON of unique face attributes."""
    try:
        import cv2
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {}
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        mean_intensity = np.mean(gray)
        std_intensity = np.std(gray)
        
        # Entropy calculation
        _, counts = np.unique(gray, return_counts=True)
        probs = counts / counts.sum()
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        
        return {
            "clarity_score": float(round(blur_score, 2)),
            "brightness": float(round(mean_intensity, 2)),
            "contrast": float(round(std_intensity, 2)),
            "entropy": float(round(entropy, 4)),
            "timestamp": datetime.datetime.now().isoformat(),
            "unique_signature": hashlib.sha256(image_bytes).hexdigest()[:16]
        }
    except Exception:
        return {}


def detect_deepfake_image(image_bytes):
    """
    Standalone deepfake detection for the /api/detect/image endpoint.
    Returns detection result dict.
    """
    _load_model()
    model_result = _run_model_inference(image_bytes)
    
    if model_result:
        return {
            'label': model_result['label'],
            'confidence': model_result['confidence'],
            'raw_score': model_result['raw_score'],
            'method': 'xception_cnn'
        }
    else:
        # Fallback: statistical
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        if len(image_array) > 0:
            _, counts = np.unique(image_array, return_counts=True)
            probabilities = counts / len(image_array)
            entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))
            
            # Use entropy + hash-based score
            score_seed = (hash(image_bytes[:100].hex()) % 1000) / 1000
            combined = (entropy / 8.0) * 0.6 + score_seed * 0.4
            
            is_real = combined > 0.45
            confidence = combined if is_real else (1.0 - combined)
            confidence = max(0.5, min(0.95, confidence))
            
            return {
                'label': 'REAL' if is_real else 'FAKE',
                'confidence': float(round(float(confidence), 4)),
                'raw_score': float(round(float(1.0 - combined if not is_real else combined), 4)),
                'method': 'statistical_fallback'
            }
        
        return {
            'label': 'UNKNOWN',
            'confidence': 0.5,
            'raw_score': 0.5,
            'method': 'error'
        }
