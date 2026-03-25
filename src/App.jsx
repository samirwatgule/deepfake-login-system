import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import UserHomePage from './pages/UserHomePage';
import DetectPage from './pages/DetectPage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import './App.css';

function App() {
    const [token, setToken]   = useState(localStorage.getItem('token') || '');
    const [email, setEmail]   = useState(localStorage.getItem('email') || '');
    const [role,  setRole]    = useState(localStorage.getItem('role')  || '');

    const handleLogin = (newToken, newEmail, newRole = 'user', newName = '') => {
        setToken(newToken);
        setEmail(newEmail);
        setRole(newRole);
        localStorage.setItem('token', newToken);
        localStorage.setItem('email', newEmail);
        localStorage.setItem('role',  newRole);
        if (newName) localStorage.setItem('name', newName);
    };

    const handleLogout = () => {
        setToken('');
        setEmail('');
        setRole('');
        ['token', 'email', 'role', 'name', 'pendingToken'].forEach(k => localStorage.removeItem(k));
    };

    const isAuth  = !!token;
    const isAdmin = role === 'admin';

    return (
        <Router>
            <Navbar isAuth={isAuth} email={email} role={role} onLogout={handleLogout} />
            <Routes>
                {/* Auth */}
                <Route path="/login"
                    element={isAuth ? <Navigate to={isAdmin ? '/admin/dashboard' : '/home'} /> : <LoginPage onLogin={handleLogin} />}
                />
                <Route path="/register"
                    element={isAuth ? <Navigate to="/home" /> : <RegisterPage onLogin={handleLogin} />}
                />

                {/* User Pages */}
                <Route path="/home"
                    element={isAuth && !isAdmin ? <UserHomePage onLogout={handleLogout} /> : <Navigate to={isAuth ? '/admin/dashboard' : '/login'} />}
                />

                {/* Detect — admin only */}
                <Route path="/detect"
                    element={isAuth && isAdmin ? <DetectPage token={token} /> : <Navigate to={isAuth ? '/home' : '/login'} />}
                />

                {/* Admin */}
                <Route path="/quantum-admin"
                    element={isAdmin ? <Navigate to="/admin/dashboard" /> : <AdminLoginPage onLogin={handleLogin} />}
                />
                <Route path="/admin/dashboard"
                    element={isAuth && isAdmin ? <AdminDashboardPage token={token} /> : <Navigate to="/quantum-admin" />}
                />

                {/* Default */}
                <Route path="*" element={
                    <Navigate to={isAuth ? (isAdmin ? '/admin/dashboard' : '/home') : '/login'} />
                } />
            </Routes>
        </Router>
    );
}

export default App;
