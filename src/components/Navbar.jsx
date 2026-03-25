import { Link, useLocation } from 'react-router-dom';

export default function Navbar({ isAuth, email, role, onLogout }) {
    const location = useLocation();
    const isAdmin = role === 'admin';
    const name = localStorage.getItem('name') || email?.split('@')[0] || '';
    const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2) || '?';

    const navLinks = isAdmin
        ? [
            { to: '/admin/dashboard', label: '⚡ Command Center' },
            { to: '/detect', label: '🔍 Detect' },
          ]
        : [
            { to: '/home', label: '🏠 Home' },
          ];

    return (
        <nav className="navbar">
            <div className="navbar-inner">
                {/* Brand */}
                <Link to={isAuth ? (isAdmin ? '/admin/dashboard' : '/home') : '/login'} className="navbar-brand">
                    <div className="brand-icon">⚛</div>
                    <div>
                        <span className="brand-name">QuantumShield</span>
                        <span className="brand-tag">{isAdmin ? 'Admin Panel' : 'Finance'}</span>
                    </div>
                </Link>

                {/* Nav Links */}
                {isAuth && (
                    <div className="nav-links">
                        {navLinks.map(link => (
                            <Link
                                key={link.to}
                                to={link.to}
                                className={`nav-link ${location.pathname === link.to ? 'active' : ''}`}
                            >
                                {link.label}
                            </Link>
                        ))}
                    </div>
                )}

                {/* Right Side */}
                <div className="nav-right">
                    {isAuth ? (
                        <>
                            <div className="nav-user">
                                <div className="nav-avatar">{initials}</div>
                                <div className="nav-user-info">
                                    <div className="nav-user-name">{name || email}</div>
                                    <div className={`nav-role-badge ${isAdmin ? 'admin' : 'user'}`}>
                                        {isAdmin ? '👑 Admin' : '🔵 User'}
                                    </div>
                                </div>
                            </div>
                            <button className="btn btn-ghost nav-logout" onClick={onLogout}>
                                Sign Out
                            </button>
                        </>
                    ) : (
                        <div className="nav-auth-links">
                            <Link to="/login" className={`nav-link ${location.pathname === '/login' ? 'active' : ''}`}>
                                Sign In
                            </Link>
                            <Link to="/register" className="btn btn-primary btn-sm">
                                Register
                            </Link>
                        </div>
                    )}
                </div>
            </div>
        </nav>
    );
}
