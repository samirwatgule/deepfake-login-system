from api.config import Config

def compute_total_risk(device_result, behavior_result, face_result):
    """
    Aggregate all risk scores and determine the authentication decision.
    
    Formula:
      Total Risk = device_risk (0-40) + behavior_risk (0-30) + face_risk (0-30)
    
    Decision:
      0-30  → ALLOW
      31-70 → FLAG (step-up verification / OTP)
      71-100→ BLOCK
    """
    device_risk = device_result.get('device_risk', 0)
    location_risk = device_result.get('location_risk', 0)
    behavior_risk = behavior_result.get('behavior_risk', 0)
    face_risk = face_result.get('face_risk', 0)
    
    # Combined device + location risk (already capped at 40)
    device_combined = device_result.get('combined', device_risk + location_risk)
    
    # Total risk (capped at 100)
    total = min(device_combined + behavior_risk + face_risk, 100)
    total = round(total, 1)
    
    # Decision logic
    if face_result.get('face_verdict') == 'FAKE':
        decision = 'BLOCK'
        total = 100.0
    elif total <= Config.RISK_ALLOW_MAX:
        decision = 'ALLOW'
    elif total <= Config.RISK_FLAG_MAX:
        decision = 'FLAG'
    else:
        decision = 'BLOCK'
    
    # Collect all details
    all_details = []
    all_details.extend(device_result.get('details', []))
    all_details.extend(behavior_result.get('details', []))
    all_details.extend(face_result.get('details', []))
    
    return {
        'device_risk': round(device_risk, 1),
        'location_risk': round(location_risk, 1),
        'behavior_risk': round(behavior_risk, 1),
        'face_risk': round(face_risk, 1),
        'total_risk': total,
        'decision': decision,
        'details': all_details
    }
