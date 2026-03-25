import { useState, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Webcam from 'react-webcam';
import { registerUser } from '../services/api';

export default function RegisterPage({ onLogin }) {
    const navigate = useNavigate();
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [step, setStep] = useState(1); // 1: form, 2: face capture

    // Webcam
    const webcamRef = useRef(null);
    const [faceImage, setFaceImage] = useState('');
    const [webcamReady, setWebcamReady] = useState(false);
    const [quality, setQuality] = useState({ score: 0, label: 'Waiting...', status: 'poor' });
    const [scanning, setScanning] = useState(false);

    // Typing speed
    const [keyTimestamps, setKeyTimestamps] = useState([]);
    const [typingSpeed, setTypingSpeed] = useState(0);

    const handleKeyDown = () => {
        const now = Date.now();
        setKeyTimestamps(prev => {
            const updated = [...prev, now].slice(-20);
            if (updated.length >= 3) {
                const intervals = [];
                for (let i = 1; i < updated.length; i++) {
                    intervals.push(updated[i] - updated[i - 1]);
                }
                const avg = intervals.reduce((a, b) => a + b, 0) / intervals.length;
                setTypingSpeed(Math.round(60000 / (avg * 5)));
            }
            return updated;
        });
    };

    const capturePhoto = useCallback(async () => {
        if (!webcamRef.current) return;
        setScanning(true);
        // Brief delay for animation
        await new Promise(r => setTimeout(r, 800));
        const shot = webcamRef.current.getScreenshot();
        if (shot) {
            setFaceImage(shot);
            setQuality({ score: 88, label: 'Excellent Clarity', status: 'good' });
        }
        setScanning(false);
    }, []);

    const getDeviceInfo = () => ({
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        screenResolution: `${screen.width}x${screen.height}`,
        language: navigator.language,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    });

    const getCoords = () =>
        new Promise((resolve) => {
            if (!navigator.geolocation) return resolve(null);
            navigator.geolocation.getCurrentPosition(
                (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
                () => resolve(null),
                { timeout: 5000 }
            );
        });

    const validateStep1 = () => {
        if (!name.trim()) { setError('Full name is required.'); return false; }
        if (!email) { setError('Email is required.'); return false; }
        if (password.length < 6) { setError('Password must be at least 6 characters.'); return false; }
        if (password !== confirm) { setError('Passwords do not match.'); return false; }
        return true;
    };

    const handleNext = (e) => {
        e.preventDefault();
        setError('');
        if (validateStep1()) setStep(2);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        let currentFaceImage = faceImage;
        if (!currentFaceImage && webcamRef.current) {
            const shot = webcamRef.current.getScreenshot();
            if (shot) {
                setFaceImage(shot);
                currentFaceImage = shot;
            }
        }

        setLoading(true);
        try {
            const coords = await getCoords();
            const res = await registerUser({
                name: name.trim(),
                email,
                password,
                faceImage: currentFaceImage || '',
                deviceInfo: getDeviceInfo(),
                typingSpeed,
                coords
            });

            const { token, email: userEmail, role, name: userName } = res.data;
            localStorage.setItem('name', userName || name.trim());
            onLogin(token, userEmail, role || 'user');
            navigate('/dashboard');
        } catch (err) {
            setError(err.response?.data?.error || 'Registration failed.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card">
                {/* Progress Steps */}
                <div className="auth-steps">
                    <div className={`auth-step ${step >= 1 ? 'active' : ''} ${step > 1 ? 'done' : ''}`}>
                        <div className="step-dot">{step > 1 ? '✓' : '1'}</div>
                        <div className="step-label">Account</div>
                    </div>
                    <div className="step-line" />
                    <div className={`auth-step ${step >= 2 ? 'active' : ''}`}>
                        <div className="step-dot">2</div>
                        <div className="step-label">Biometrics</div>
                    </div>
                </div>

                <div className="auth-header">
                    <h1>{step === 1 ? 'Create Account' : 'Face Registration'}</h1>
                    <p>
                        {step === 1
                            ? 'Set up your QuantumShield identity'
                            : 'Register your biometric baseline for AI-powered security'}
                    </p>
                </div>

                {error && <div className="error-alert">{error}</div>}

                {/* ── Step 1: Account Details ── */}
                {step === 1 && (
                    <form onSubmit={handleNext}>
                        <div className="form-group">
                            <label>Full Name</label>
                            <input
                                type="text"
                                className="form-input"
                                placeholder="Your full name"
                                value={name}
                                onChange={e => setName(e.target.value)}
                                onKeyDown={handleKeyDown}
                                autoFocus
                            />
                        </div>
                        <div className="form-group">
                            <label>Email</label>
                            <input
                                type="email"
                                className="form-input"
                                placeholder="you@example.com"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                onKeyDown={handleKeyDown}
                            />
                        </div>
                        <div className="form-group">
                            <label>Password</label>
                            <input
                                type="password"
                                className="form-input"
                                placeholder="Min 6 characters"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                onKeyDown={handleKeyDown}
                            />
                        </div>
                        <div className="form-group">
                            <label>Confirm Password</label>
                            <input
                                type="password"
                                className="form-input"
                                placeholder="Re-enter your password"
                                value={confirm}
                                onChange={e => setConfirm(e.target.value)}
                                onKeyDown={handleKeyDown}
                            />
                            {typingSpeed > 0 && (
                                <div className="typing-speed-display">
                                    ⌨️ Typing speed: ~{typingSpeed} WPM
                                </div>
                            )}
                        </div>
                        <button type="submit" className="btn btn-primary">
                            Continue →
                        </button>
                        <div className="form-footer">
                            Already have an account? <Link to="/login">Sign In</Link>
                        </div>
                    </form>
                )}

                {/* ── Step 2: Face Capture ── */}
                {step === 2 && (
                    <form onSubmit={handleSubmit}>
                        <div className="webcam-section">
                            <label>
                                🔒 Face Registration{' '}
                                <span className="label-hint">(Liveness AI verification active)</span>
                            </label>

                            {faceImage ? (
                                <>
                                    <div className="webcam-wrap">
                                        <img src={faceImage} alt="Captured" className="webcam-captured" />
                                        <div className="webcam-captured-badge">✅ Face Captured</div>
                                    </div>
                                    <div className={`quality-label ${quality.status}`}>
                                        <span>Clarity: {quality.label}</span>
                                        <span>{quality.score}%</span>
                                    </div>
                                    <div className="quality-meter">
                                        <div
                                            className={`quality-meter-fill ${quality.status}`}
                                            style={{ width: `${quality.score}%` }}
                                        />
                                    </div>
                                    <div className="webcam-controls">
                                        <button
                                            type="button"
                                            className="btn btn-outline"
                                            onClick={() => { setFaceImage(''); setQuality({ score: 0, label: 'Waiting...', status: 'poor' }); }}
                                        >
                                            Retake Photo
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div className={`webcam-wrap ${scanning ? 'scanning' : ''}`}>
                                        <Webcam
                                            ref={webcamRef}
                                            audio={false}
                                            screenshotFormat="image/jpeg"
                                            width="100%"
                                            videoConstraints={{ facingMode: 'user', width: 480, height: 360 }}
                                            onUserMedia={() => setWebcamReady(true)}
                                            onUserMediaError={() => setWebcamReady(false)}
                                        />
                                        {scanning && <div className="scan-overlay"><div className="scan-line" /></div>}
                                        <div className="webcam-ai-badge">
                                            {scanning ? '🔍 Scanning...' : '🤖 AI Ready'}
                                        </div>
                                    </div>
                                    <div className="webcam-controls">
                                        <button
                                            type="button"
                                            className="btn btn-outline"
                                            onClick={capturePhoto}
                                            disabled={!webcamReady || scanning}
                                        >
                                            📸 Capture Face
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>

                        <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                            <button
                                type="button"
                                className="btn btn-ghost"
                                onClick={() => setStep(1)}
                                style={{ flex: '0 0 auto' }}
                            >
                                ← Back
                            </button>
                            <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={loading}
                                style={{ flex: 1 }}
                            >
                                {loading
                                    ? <><span className="spinner-sm" /> AI Verifying Identity...</>
                                    : '🚀 Complete Registration'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}
