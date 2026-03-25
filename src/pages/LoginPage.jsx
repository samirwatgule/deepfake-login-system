import { useState, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Webcam from 'react-webcam';
import { loginUser } from '../services/api';

export default function LoginPage({ onLogin }) {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [riskResult, setRiskResult] = useState(null);
    const [showOtp, setShowOtp] = useState(false);
    const [otp, setOtp] = useState('');

    // Webcam
    const webcamRef = useRef(null);
    const [faceImage, setFaceImage] = useState('');
    const [webcamReady, setWebcamReady] = useState(false);
    const [quality, setQuality] = useState({ score: 0, label: 'Scanning...', status: 'poor' });

    // Typing speed measurement
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
                const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
                const wpm = Math.round(60000 / (avgInterval * 5));
                setTypingSpeed(wpm);
            }
            return updated;
        });
    };

    const capturePhoto = useCallback(() => {
        if (webcamRef.current) {
            const shot = webcamRef.current.getScreenshot();
            setFaceImage(shot || '');
            
            // Quality feedback sim
            if (shot) {
                setQuality({ score: 92, label: 'High Precision', status: 'good' });
            }
        }
    }, []);

    const getDeviceInfo = () => ({
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        screenResolution: `${screen.width}x${screen.height}`,
        language: navigator.language,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    });

    const getCoords = () => {
        return new Promise((resolve) => {
            if (!navigator.geolocation) {
                resolve(null);
                return;
            }
            navigator.geolocation.getCurrentPosition(
                (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
                () => resolve(null),
                { timeout: 5000 }
            );
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setRiskResult(null);

        if (!email || !password) {
            setError('Email and password are required.');
            return;
        }

        // Auto-capture if no image yet
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
            const res = await loginUser({
                email,
                password,
                faceImage: currentFaceImage || '',
                deviceInfo: getDeviceInfo(),
                typingSpeed,
                coords
            });

            const { token, email: userEmail, role, risk } = res.data;

            setRiskResult(risk);

            if (risk.decision === 'FLAG') {
                setShowOtp(true);
                localStorage.setItem('pendingToken', token);
            } else if (risk.decision === 'ALLOW') {
                onLogin(token, userEmail, role || 'user');
                if (role === 'admin') {
                    navigate('/admin/dashboard');
                } else {
                    navigate('/home');
                }
            }
            // BLOCK = don't login, just show result (deepfake detected)
        } catch (err) {
            setError(err.response?.data?.error || 'Login failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleOtpVerify = () => {
        if (otp.length === 6) {
            setShowOtp(false);
            if (riskResult) {
                const token = localStorage.getItem('pendingToken') || '';
                onLogin(token || 'otp-verified-token', email, 'user');
                localStorage.removeItem('pendingToken');
                navigate('/home');
            }
        }
    };

    const decisionLabels = {
        ALLOW: { title: 'Access Granted', subtitle: 'Identity verified — you are who you say you are.', icon: '✓' },
        FLAG: { title: 'Additional Verification Required', subtitle: 'Moderate risk detected — OTP verification needed.', icon: '⚠' },
        BLOCK: { title: 'Access Blocked', subtitle: '', icon: '✕' },
    };

    // Build block subtitle based on face verdict
    const getBlockSubtitle = () => {
        if (!riskResult) return 'High risk detected — login denied.';
        if (riskResult.face_verdict === 'FAKE') {
            return `🚫 DEEPFAKE DETECTED — AI model identified a fake/manipulated face (${(riskResult.face_confidence * 100).toFixed(1)}% confidence). Access denied.`;
        }
        return 'High risk detected — login attempt denied for security.';
    };

    return (
        <div className="auth-page">
            <div style={{ width: '100%', maxWidth: 480 }}>
                <div className="auth-card">
                    <div className="auth-header">
                        <h1>Sign In</h1>
                        <p>AI-powered identity verification with real-time deepfake detection</p>
                    </div>

                    {error && <div className="error-alert">{error}</div>}

                    <form onSubmit={handleSubmit}>
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
                                placeholder="Enter your password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                onKeyDown={handleKeyDown}
                            />
                            {typingSpeed > 0 && (
                                <div className="typing-speed-display">Typing speed: ~{typingSpeed} WPM</div>
                            )}
                        </div>

                        <div className="webcam-section">
                            <label>🔒 Live Face Verification <span className="label-hint">(AI deepfake detection active)</span></label>
                            {faceImage ? (
                                <>
                                    <div className="webcam-wrap">
                                        <img src={faceImage} alt="Captured" className="webcam-captured" />
                                    </div>

                                    <div className={`quality-label ${quality.status}`}>
                                        <span>Scan Quality: {quality.label}</span>
                                        <span>{quality.score}%</span>
                                    </div>
                                    <div className="quality-meter">
                                        <div 
                                            className={`quality-meter-fill ${quality.status}`} 
                                            style={{ width: `${quality.score}%` }} 
                                        />
                                    </div>

                                    <div className="webcam-controls">
                                        <button type="button" className="btn btn-outline" onClick={() => { setFaceImage(''); setQuality({ score: 0, label: 'Scanning...', status: 'poor' }); }}>
                                            Retake
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div className="webcam-wrap">
                                        <Webcam
                                            ref={webcamRef}
                                            audio={false}
                                            screenshotFormat="image/jpeg"
                                            width="100%"
                                            videoConstraints={{ facingMode: 'user', width: 480, height: 240 }}
                                            onUserMedia={() => setWebcamReady(true)}
                                            onUserMediaError={() => setWebcamReady(false)}
                                        />
                                        <div className="webcam-ai-badge">🤖 AI Scanning Active</div>
                                    </div>
                                    <div className="webcam-controls">
                                        <button type="button" className="btn btn-outline" onClick={capturePhoto} disabled={!webcamReady}>
                                            📸 Scan Identity
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>

                        <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
                            {loading ? <><span className="spinner-sm" /> AI Verifying Identity...</> : '🔐 Sign In'}
                        </button>
                    </form>

                    <div className="form-footer">
                        Don't have an account? <Link to="/register">Register</Link>
                    </div>
                </div>

                {/* Risk Result */}
                {riskResult && (
                    <div className="risk-result">
                        <div className={`risk-header ${riskResult.decision.toLowerCase()}`}>
                            <div className={`risk-icon ${riskResult.decision.toLowerCase()}`}>
                                {decisionLabels[riskResult.decision]?.icon}
                            </div>
                            <div>
                                <div className={`risk-title ${riskResult.decision.toLowerCase()}`}>
                                    {decisionLabels[riskResult.decision]?.title}
                                </div>
                                <div className="risk-subtitle">
                                    {riskResult.decision === 'BLOCK' ? getBlockSubtitle() : decisionLabels[riskResult.decision]?.subtitle}
                                </div>
                            </div>
                        </div>

                        <div className="risk-body">
                            {[
                                { label: 'Device Risk', value: riskResult.device_risk, max: 20 },
                                { label: 'Location Risk', value: riskResult.location_risk, max: 25 },
                                { label: 'Behavior Risk', value: riskResult.behavior_risk, max: 30 },
                                { label: 'Face AI Risk', value: riskResult.face_risk, max: 30 },
                            ].map(({ label, value, max }) => (
                                <div key={label}>
                                    <div className="risk-score-row">
                                        <span className="risk-score-label">{label}</span>
                                        <span className="risk-score-value">{value}/{max}</span>
                                    </div>
                                    <div className="risk-bar-track">
                                        <div
                                            className={`risk-bar-fill ${value / max > 0.6 ? 'high' : value / max > 0.3 ? 'medium' : 'low'}`}
                                            style={{ width: `${(value / max) * 100}%` }}
                                        />
                                    </div>
                                </div>
                            ))}

                            {/* Face AI Verdict */}
                            {riskResult.face_verdict && (
                                <div className={`face-verdict-banner ${riskResult.face_verdict.toLowerCase()}`}>
                                    <span className="face-verdict-icon">
                                        {riskResult.face_verdict === 'REAL' ? '✅' : riskResult.face_verdict === 'FAKE' ? '🚫' : '⚠️'}
                                    </span>
                                    <span>
                                        Face AI Verdict: <strong>{riskResult.face_verdict}</strong>
                                        {riskResult.face_confidence > 0 && ` (${(riskResult.face_confidence * 100).toFixed(1)}% confidence)`}
                                    </span>
                                </div>
                            )}
                        </div>

                        <div className="risk-total">
                            <span>Total Risk Score</span>
                            <span className="risk-total-value">{riskResult.total_risk}/100</span>
                        </div>

                        {riskResult.details && riskResult.details.length > 0 && (
                            <div className="risk-details">
                                <h4>Analysis Details</h4>
                                {riskResult.details.map((d, i) => (
                                    <div key={i} className="risk-detail-item">• {d}</div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* OTP Modal */}
                {showOtp && (
                    <div className="otp-modal-overlay" onClick={() => setShowOtp(false)}>
                        <div className="otp-modal" onClick={e => e.stopPropagation()}>
                            <h3>🔐 OTP Verification</h3>
                            <p>A verification code has been sent to your email. Enter it below to proceed.</p>
                            <input
                                className="otp-input"
                                type="text"
                                maxLength={6}
                                placeholder="000000"
                                value={otp}
                                onChange={e => setOtp(e.target.value.replace(/\D/g, ''))}
                            />
                            <button
                                className="btn btn-primary"
                                onClick={handleOtpVerify}
                                disabled={otp.length !== 6}
                            >
                                Verify Code
                            </button>
                            <div className="otp-hint">For demo: enter any 6-digit code (e.g., 123456)</div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
