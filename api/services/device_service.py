import hashlib
import json
import requests
import os

def compute_device_hash(device_info):
    """Generate SHA-256 hash from device metadata for fingerprinting."""
    if isinstance(device_info, str):
        try:
            device_info = json.loads(device_info)
        except (json.JSONDecodeError, TypeError):
            device_info = {"raw": device_info}

    fingerprint = '|'.join([
        str(device_info.get('userAgent', '')),
        str(device_info.get('platform', '')),
        str(device_info.get('screenResolution', '')),
        str(device_info.get('language', '')),
        str(device_info.get('timezone', ''))
    ])

    return hashlib.sha256(fingerprint.encode('utf-8')).hexdigest()


def _reverse_geocode(lat, lon):
    """
    Use OpenStreetMap Nominatim reverse geocoding API to resolve
    GPS coordinates to city/state/country.
    Returns dict with city, country (and state if available).
    """
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=10"
        response = requests.get(
            url,
            timeout=5,
            headers={'User-Agent': 'QuantumShield-Auth/1.0 (educational project)'}
        )
        if response.status_code == 200:
            data = response.json()
            addr = data.get('address', {})
            # Nominatim has many granularity levels; pick the most useful
            city = (
                addr.get('city')
                or addr.get('town')
                or addr.get('village')
                or addr.get('suburb')
                or addr.get('county')
                or f"({lat:.3f}, {lon:.3f})"
            )
            state = addr.get('state', '')
            country = addr.get('country', 'Unknown')
            display = f"{city}, {state}" if state and state != city else city
            return {'city': display, 'country': country}
    except Exception as e:
        print(f"[GEO] Nominatim reverse geocode error: {e}")

    # Fallback: just use GPS label
    return {'city': f"GPS ({lat:.4f}, {lon:.4f})", 'country': 'Unknown'}


def get_geolocation(ip_address, coords=None):
    """
    Get geolocation data.
    If coords (lat, lon) are provided, uses OpenStreetMap Nominatim for
    real city/country. Otherwise falls back to ipapi.co IP-based lookup.
    """
    if coords and isinstance(coords, dict):
        lat = coords.get('latitude')
        lon = coords.get('longitude')
        if lat and lon:
            geo = _reverse_geocode(lat, lon)
            return {
                'city': geo['city'],
                'country': geo['country'],
                'ip': ip_address,
                'coords': coords
            }

    geo_url = os.environ.get('GEO_API_URL', 'https://ipapi.co')

    # For localhost / private IPs: try to get real public IP for geolocation
    if (
        ip_address in ('127.0.0.1', 'localhost', '::1', '')
        or ip_address.startswith('192.168.')
        or ip_address.startswith('10.')
        or ip_address.startswith('172.')
    ):
        try:
            # Fetch real public IP
            pub_resp = requests.get('https://api.ipify.org?format=json', timeout=3)
            if pub_resp.status_code == 200:
                public_ip = pub_resp.json().get('ip', '')
                if public_ip:
                    geo_resp = requests.get(
                        f"{geo_url}/{public_ip}/json/",
                        timeout=5,
                        headers={'User-Agent': 'QuantumShield/1.0'}
                    )
                    if geo_resp.status_code == 200:
                        data = geo_resp.json()
                        return {
                            'city': data.get('city', 'Unknown'),
                            'country': data.get('country_name', 'Unknown'),
                            'ip': public_ip
                        }
        except Exception as e:
            print(f"[GEO] Public IP lookup failed: {e}")
        return {'city': 'Local', 'country': 'Local', 'ip': ip_address}

    try:
        response = requests.get(
            f"{geo_url}/{ip_address}/json/",
            timeout=5,
            headers={'User-Agent': 'QuantumShield/1.0'}
        )
        if response.status_code == 200:
            data = response.json()
            return {
                'city': data.get('city', 'Unknown'),
                'country': data.get('country_name', 'Unknown'),
                'ip': ip_address
            }
    except Exception as e:
        print(f"[GEO] Geolocation API error: {e}")

    return {'city': 'Unknown', 'country': 'Unknown', 'ip': ip_address}


def compute_device_risk(user, current_device_hash, current_location):
    """
    Compute device + location risk score (0-40).
    Rules:
      - New device: +20
      - New city:   +15
      - New country:+25
      - Max: 40
    """
    risk = 0
    details = []

    # Parse stored device hash
    registered_device = user.get('registered_device', '')
    if isinstance(registered_device, str):
        try:
            registered_device_data = json.loads(registered_device)
            stored_hash = compute_device_hash(registered_device_data)
        except (json.JSONDecodeError, TypeError):
            stored_hash = registered_device
    else:
        stored_hash = compute_device_hash(registered_device)

    # Device comparison
    if stored_hash and current_device_hash != stored_hash:
        risk += 20
        details.append("New device detected (+20)")

    # Location comparison
    home_city = user.get('home_city', 'Unknown')
    home_country = user.get('home_country', 'Unknown')
    current_city = current_location.get('city', 'Unknown')
    current_country = current_location.get('country', 'Unknown')

    if home_country not in ('Unknown', 'Local') and current_country not in ('Unknown', 'Local'):
        if current_country != home_country:
            risk += 25
            details.append(f"New country: {current_country} vs {home_country} (+25)")
        elif current_city != home_city:
            risk += 15
            details.append(f"New city: {current_city} vs {home_city} (+15)")

    total = min(risk, 40)
    device_risk = 20 if (stored_hash and current_device_hash != stored_hash) else 0
    location_risk = total - device_risk

    return {
        'device_risk': min(device_risk, 20),
        'location_risk': min(max(location_risk, 0), 25),
        'combined': total,
        'details': details
    }
