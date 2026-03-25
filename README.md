# ⚛️ Deepfake Detection & Secure Login System (QuantumShield)

> **Production-ready full-stack authentication** powered by XceptionNet deepfake detection, real-time face liveness verification, impossible-travel anomaly detection, and a rich admin command center.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![React](https://img.shields.io/badge/react-18+-61DAFB.svg)
![TensorFlow](https://img.shields.io/badge/tensorflow-2.16+-FF6F00.svg)

---

## 🌟 Key Features

- **Deepfake Detection Engine**: Utilizes XceptionNet model (98% accuracy on FaceForensics++) to identify manipulated images/videos in real-time.
- **Liveness Verification**: Anti-spoofing checks using geometric analysis and blink detection via OpenCV.
- **Behavioral Analytics**: Monitors typing patterns and mouse movements to detect bot-like behavior.
- **Impossible Travel Detection**: Flags login attempts from geographically distant locations within unrealistic timeframes using IP geolocation.
- **Admin Dashboard**: Comprehensive monitoring interface for security alerts, user management, and system health.
- **Modern UI/UX**: Responsive React frontend with glassmorphism design.

---

## 🗂️ Project Structure

```
QuantumShield/
├── api/                          # Flask Backend (Python)
│   ├── index.py                  # App factory & entry point
│   ├── database.py               # SQLite init + schema migrations
│   ├── config.py                 # Risk thresholds & env config
│   ├── routes/
│   │   ├── auth_routes.py        # User authentication endpoints
│   │   ├── admin_routes.py       # Admin panel endpoints
│   │   └── detect_routes.py      # AI detection endpoints
│   ├── services/
│   │   ├── auth_service.py       # JWT & password handling
│   │   ├── face_service.py       # Deepfake model interface
│   │   ├── risk_engine.py        # Security decision matrix
│   │   └── ...
│   └── static/                   # Uploaded media storage
├── src/                          # React Frontend (Vite)
│   ├── pages/
│   │   ├── LoginPage.jsx         # Biometric login interface
│   │   ├── RegisterPage.jsx      # Facial enrollment flow
│   │   ├── AdminDashboardPage.jsx# Security monitoring console
│   │   └── ...
│   ├── components/               # Reusable UI components
│   └── services/                 # API client wrapper
├── deepfake_detection_model.h5   # Core AI model weights (Larger file)
├── quantumshield.db              # SQLite Database
└── ...
```

---

## ⚙️ Tech Stack

| Layer       | Technology |
|-------------|------------|
| **Frontend**| React 18, Vite, Tailwind/CSS, Axios, react-webcam |
| **Backend** | Python 3.10+, Flask 3.1, Flask-CORS |
| **AI/ML**   | TensorFlow, Keras, XceptionNet, OpenCV, Scikit-learn |
| **Database**| SQLite 3 (WAL mode enabled) |
| **Security**| JWT (RS256/HS256), Bcrypt, GeoIP |

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/samirwatgule/deepfake-login-system.git
cd deepfake-login-system
```

### 2️⃣ Backend Setup

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Start the Flask server
python api/index.py
```
> The server will start at `http://localhost:5000`

### 3️⃣ Frontend Setup

Open a new terminal in the project root:

```bash
# Install Node dependencies
npm install

# Start the development server
npm run dev
```
> The application will be available at `http://localhost:5173`

---

## 🛡️ Default Admin Credentials

When you first run the application, an admin account is automatically created:

- **Email:** `admin@gamil.com`
- **Password:** `Admin@123`
- **Login URL:** `/admin-login`

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
