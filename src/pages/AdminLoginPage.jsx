import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminLogin } from '../services/api';

export default function AdminLoginPage({ onLogin }) {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (!email || !password) {
            setError('Admin credentials are required.');
            return;
        }

        setLoading(true);
        try {
            const res = await adminLogin({ email, password });
            const { token, email: adminEmail, role } = res.data;
            onLogin(token, adminEmail, role);
            navigate('/admin/dashboard');
        } catch (err) {
            setError(err.response?.data?.error || 'Admin authentication failed.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-page admin-auth-page">
            <div className="auth-card admin-card">
                <div className="admin-badge">⚡ CLASSIFIED</div>
                <div className="auth-header">
                    <h1 className="admin-title">Admin Access</h1>
                    <p>QuantumShield Control Panel — Authorized Personnel Only</p>
                </div>

                {error && <div className="error-alert">{error}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Admin Email</label>
                        <input
                            type="email"
                            className="form-input"
                            placeholder="admin@gmail.com"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            autoComplete="off"
                        />
                    </div>

                    <div className="form-group">
                        <label>Admin Password</label>
                        <div style={{ position: 'relative' }}>
                            <input
                                type={showPassword ? 'text' : 'password'}
                                className="form-input"
                                placeholder="Enter admin password"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                autoComplete="off"
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                style={{
                                    position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    color: 'var(--text-muted)', fontSize: '1rem'
                                }}
                            >
                                {showPassword ? '🙈' : '👁️'}
                            </button>
                        </div>
                    </div>

                    <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
                        {loading ? <><span className="spinner-sm" /> Authenticating...</> : '🔓 Access Control Panel'}
                    </button>
                </form>

                <div className="admin-footer">
                    <span>🔒 This portal is not linked from the main application</span>
                </div>
            </div>
        </div>
    );
}
