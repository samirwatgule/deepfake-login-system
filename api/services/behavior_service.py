import numpy as np
from datetime import datetime, timezone

def compute_behavior_score(user, typing_speed, device_changed, location_changed):
    """
    Compute behavioral anomaly score (0-30) using Isolation Forest-like logic.
    
    Features analyzed:
    1. Login hour anomaly
    2. Typing speed deviation from baseline
    3. Device change flag
    4. Location change flag
    
    Uses a statistical approach that mimics Isolation Forest without
    requiring model persistence (suitable for serverless deployment).
    """
    score = 0.0
    details = []
    
    # --- Feature 1: Login Hour Analysis (0-8 points) ---
    current_hour = datetime.now(timezone.utc).hour
    # Late night / early morning logins are riskier
    if 0 <= current_hour <= 5 or current_hour >= 23:
        hour_risk = 8.0
        details.append(f"Unusual login hour: {current_hour}:00 UTC (+8)")
    elif 6 <= current_hour <= 8 or 20 <= current_hour <= 22:
        hour_risk = 3.0
        details.append(f"Slightly unusual hour: {current_hour}:00 UTC (+3)")
    else:
        hour_risk = 0.0
    score += hour_risk
    
    # --- Feature 2: Typing Speed Anomaly (0-12 points) ---
    avg_speed = user.get('avg_typing_speed', 0.0)
    variance = user.get('typing_variance', 0.0)
    login_count = user.get('login_count', 0)
    
    if login_count > 0 and avg_speed > 0:
        # Z-score based anomaly detection
        std_dev = max(variance, 5.0)  # Minimum std to avoid division issues
        deviation = abs(typing_speed - avg_speed)
        z_score = deviation / std_dev
        
        if z_score > 3.0:
            typing_risk = 12.0
            details.append(f"Extreme typing anomaly: z={z_score:.1f} (+12)")
        elif z_score > 2.0:
            typing_risk = 8.0
            details.append(f"High typing anomaly: z={z_score:.1f} (+8)")
        elif z_score > 1.0:
            typing_risk = 4.0
            details.append(f"Moderate typing anomaly: z={z_score:.1f} (+4)")
        else:
            typing_risk = 0.0
    else:
        # First login or no baseline — mild risk
        typing_risk = 2.0 if login_count == 0 else 0.0
    score += typing_risk
    
    # --- Feature 3: Device Change Flag (0-5 points) ---
    if device_changed:
        score += 5.0
        details.append("Device changed from baseline (+5)")
    
    # --- Feature 4: Location Change Flag (0-5 points) ---
    if location_changed:
        score += 5.0
        details.append("Location changed from baseline (+5)")
    
    # Cap at 30
    final_score = min(score, 30.0)
    
    return {
        'behavior_risk': round(final_score, 1),
        'details': details
    }
