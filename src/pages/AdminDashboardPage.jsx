import { useState, useEffect } from 'react';
import { getStats, getLoginLogs, getUsers, toggleBlockUser, getUserById, deleteUser } from '../services/api';

export default function AdminDashboardPage({ token }) {
    const [stats, setStats] = useState(null);
    const [logs, setLogs] = useState([]);
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview');
    const [statusFilter, setStatusFilter] = useState('');
    const [selectedUser, setSelectedUser] = useState(null);
    const [userLogs, setUserLogs] = useState(null);
    const [userLogsLoading, setUserLogsLoading] = useState(false);

    useEffect(() => { fetchData(); }, []);

    const fetchData = async () => {
        setLoading(true);
        try {
            const [statsRes, logsRes, usersRes] = await Promise.all([
                getStats(),
                getLoginLogs({ limit: 50 }),
                getUsers(),
            ]);
            setStats(statsRes.data);
            setLogs(logsRes.data.logs || []);
            setUsers(usersRes.data.users || []);
        } catch (err) {
            console.error('Failed to fetch admin data:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleBlockUser = async (userId) => {
        try {
            await toggleBlockUser(userId);
            fetchData();
        } catch (err) {
            console.error('Failed to toggle block:', err);
        }
    };

    const handleDeleteUser = async (user) => {
        if (!window.confirm(`Are you sure you want to permanently delete user ${user.email}?\nThis will remove them and all their login logs from the database. This action cannot be undone.`)) return;
        try {
            await deleteUser(user.id);
            fetchData();
        } catch (err) {
            console.error('Failed to delete user:', err);
            alert(err.response?.data?.error || 'Failed to delete user');
        }
    };

    const handleViewUserLogs = async (user) => {
        setSelectedUser(user);
        setUserLogs(null);
        setUserLogsLoading(true);
        try {
            const res = await getUserById(user.id);
            setUserLogs(res.data.logs || []);
        } catch (err) {
            setUserLogs([]);
        } finally {
            setUserLogsLoading(false);
        }
    };

    const filteredLogs = statusFilter
        ? logs.filter(l => l.decision === statusFilter)
        : logs;

    if (loading) {
        return (
            <div className="loading-center">
                <div className="loading-spinner" />
            </div>
        );
    }

    const s = stats || {};

    return (
        <div className="admin-dashboard">
            <div className="admin-dash-header">
                <div>
                    <h1>⚡ QuantumShield Command Center</h1>
                    <p>Real-time AI security monitoring, deepfake analytics, and user management</p>
                </div>
                <button className="btn btn-outline" onClick={fetchData}>🔄 Refresh</button>
            </div>

            {/* ── Tab Navigation ── */}
            <div className="admin-tabs">
                {['overview', 'logs', 'users'].map(tab => (
                    <button
                        key={tab}
                        className={`admin-tab ${activeTab === tab ? 'active' : ''}`}
                        onClick={() => setActiveTab(tab)}
                    >
                        {tab === 'overview' && '📊 '}
                        {tab === 'logs' && '📋 '}
                        {tab === 'users' && '👥 '}
                        {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                ))}
            </div>

            {/* ── Overview Tab ── */}
            {activeTab === 'overview' && (
                <>
                    <div className="stats-grid stats-grid-6">
                        <div className="stat-card"><div className="stat-label">Total Logins</div><div className="stat-value">{s.total_logins || 0}</div></div>
                        <div className="stat-card"><div className="stat-label">Allowed</div><div className="stat-value success">{s.allowed || 0}</div></div>
                        <div className="stat-card"><div className="stat-label">Flagged</div><div className="stat-value warning">{s.flagged || 0}</div></div>
                        <div className="stat-card"><div className="stat-label">Blocked</div><div className="stat-value danger">{s.blocked || 0}</div></div>
                        <div className="stat-card"><div className="stat-label">Deepfakes Caught</div><div className="stat-value danger">{s.deepfakes_blocked || 0}</div></div>
                        <div className="stat-card"><div className="stat-label">Total Users</div><div className="stat-value">{s.total_users || 0}</div></div>
                        <div className="stat-card"><div className="stat-label">Blocked Users</div><div className="stat-value danger">{s.blocked_users || 0}</div></div>
                        <div className="stat-card"><div className="stat-label">Impossible Travel</div><div className="stat-value warning">{s.suspicious_logins || 0}</div></div>
                    </div>

                    <div className="dashboard-grid">
                        {/* Risk Breakdown */}
                        <div className="dashboard-card">
                            <div className="card-header">Average Risk Breakdown</div>
                            <div className="card-body">
                                {(s.total_logins || 0) > 0 ? (
                                    <>
                                        {[
                                            { label: 'Device', value: s.avg_device_risk || 0, max: 20, cls: 'device' },
                                            { label: 'Location', value: s.avg_location_risk || 0, max: 25, cls: 'location' },
                                            { label: 'Behavior', value: s.avg_behavior_risk || 0, max: 30, cls: 'behavior' },
                                            { label: 'Face/AI', value: s.avg_face_risk || 0, max: 30, cls: 'face' },
                                        ].map(({ label, value, max, cls }) => (
                                            <div className="risk-chart-bar" key={label}>
                                                <div className="risk-chart-label">{label}</div>
                                                <div className="risk-chart-track">
                                                    <div className={`risk-chart-fill ${cls}`} style={{ width: `${(value / max) * 100}%` }} />
                                                </div>
                                                <div className="risk-chart-value">{value}</div>
                                            </div>
                                        ))}
                                    </>
                                ) : (
                                    <div className="empty-state"><div className="empty-state-icon">📊</div><p>No data yet</p></div>
                                )}
                            </div>
                        </div>

                        {/* Decision Distribution */}
                        <div className="dashboard-card">
                            <div className="card-header">Decision Distribution</div>
                            <div className="card-body">
                                {(s.total_logins || 0) > 0 ? (
                                    <div className="decision-chart">
                                        <div className="donut-wrap">
                                            <svg width="140" height="140" viewBox="0 0 140 140">
                                                {renderDonut(s.allowed || 0, s.flagged || 0, s.blocked || 0)}
                                            </svg>
                                            <div className="donut-center">
                                                <div className="donut-center-value">{s.total_logins || 0}</div>
                                                <div className="donut-center-label">Total</div>
                                            </div>
                                        </div>
                                        <div className="decision-legend">
                                            <div className="legend-item"><span className="legend-dot allow" /><span>Allowed</span><span className="legend-count">{s.allowed || 0}</span></div>
                                            <div className="legend-item"><span className="legend-dot flag" /><span>Flagged</span><span className="legend-count">{s.flagged || 0}</span></div>
                                            <div className="legend-item"><span className="legend-dot block" /><span>Blocked</span><span className="legend-count">{s.blocked || 0}</span></div>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="empty-state"><div className="empty-state-icon">🔄</div><p>No data yet</p></div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Recent Suspicious */}
                    {s.recent_suspicious && s.recent_suspicious.length > 0 && (
                        <div className="dashboard-card full-width" style={{ marginBottom: 20 }}>
                            <div className="card-header">⚠️ Recent Suspicious Attempts</div>
                            <div className="card-body" style={{ padding: 0 }}>
                                <table className="logs-table">
                                    <thead>
                                        <tr>
                                            <th>Email</th><th>Location</th><th>Risk</th>
                                            <th>Decision</th><th>Face AI</th><th>Travel</th><th>Time</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {s.recent_suspicious.map((log, i) => (
                                            <tr key={i} className={log.is_suspicious ? 'row-suspicious' : ''}>
                                                <td style={{ fontWeight: 500 }}>{log.email}</td>
                                                <td>{log.city}, {log.country}</td>
                                                <td style={{ fontWeight: 700 }}>{log.total_risk}</td>
                                                <td><span className={`decision-badge ${log.decision.toLowerCase()}`}>{log.decision}</span></td>
                                                <td><span className={`face-verdict ${(log.face_verdict || '').toLowerCase()}`}>{log.face_verdict || '—'}</span></td>
                                                <td>{log.is_suspicious ? <span className="suspicious-travel-badge">⚠️ Travel</span> : '—'}</td>
                                                <td>{formatTime(log.timestamp)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* ── Logs Tab ── */}
            {activeTab === 'logs' && (
                <div className="dashboard-card full-width">
                    <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>All Login Logs</span>
                        <div className="filter-group">
                            {['', 'ALLOW', 'FLAG', 'BLOCK'].map(f => (
                                <button
                                    key={f}
                                    className={`filter-btn ${statusFilter === f ? 'active' : ''}`}
                                    onClick={() => setStatusFilter(f)}
                                >
                                    {f || 'All'}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="card-body" style={{ padding: 0 }}>
                        {filteredLogs.length > 0 ? (
                            <table className="logs-table">
                                <thead>
                                    <tr>
                                        <th>Email</th><th>IP</th><th>Location</th>
                                        <th>Device</th><th>Behavior</th><th>Face</th>
                                        <th>Total</th><th>Decision</th><th>Face AI</th>
                                        <th>Travel</th><th>Time</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredLogs.map((log, i) => (
                                        <tr key={i} className={log.is_suspicious ? 'row-suspicious' : ''}>
                                            <td style={{ fontWeight: 500 }}>{log.email}</td>
                                            <td style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{log.ip_address}</td>
                                            <td>{log.city}, {log.country}</td>
                                            <td>{log.device_risk}</td>
                                            <td>{log.behavior_risk}</td>
                                            <td>{log.face_risk}</td>
                                            <td style={{ fontWeight: 700 }}>{log.total_risk}</td>
                                            <td><span className={`decision-badge ${log.decision.toLowerCase()}`}>{log.decision}</span></td>
                                            <td><span className={`face-verdict ${(log.face_verdict || '').toLowerCase()}`}>{log.face_verdict || '—'}</span></td>
                                            <td>{log.is_suspicious ? <span className="suspicious-travel-badge">⚠️</span> : '—'}</td>
                                            <td>{formatTime(log.timestamp)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <div className="empty-state"><div className="empty-state-icon">📋</div><p>No logs found</p></div>
                        )}
                    </div>
                </div>
            )}

            {/* ── Users Tab ── */}
            {activeTab === 'users' && (
                <div className="dashboard-card full-width">
                    <div className="card-header">👥 Registered Users ({users.length})</div>
                    <div className="card-body" style={{ padding: 0 }}>
                        {users.length > 0 ? (
                            <table className="logs-table">
                                <thead>
                                    <tr>
                                        <th>Actions</th><th>ID</th><th>Name</th><th>Email</th><th>Role</th>
                                        <th>Location</th><th>Logins</th><th>Face</th>
                                        <th>Status</th><th>Registered</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {users.map(user => (
                                        <tr key={user.id}>
                                            <td>
                                                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', minWidth: '240px' }}>
                                                    <button
                                                        className="btn-sm btn-outline"
                                                        onClick={() => handleViewUserLogs(user)}
                                                    >
                                                        📋 History
                                                    </button>
                                                    {user.role !== 'admin' && (
                                                        <>
                                                            <button
                                                                className={`btn-sm ${user.is_blocked ? 'btn-unblock' : 'btn-block'}`}
                                                                onClick={() => handleBlockUser(user.id)}
                                                            >
                                                                {user.is_blocked ? 'Unblock' : 'Block'}
                                                            </button>
                                                            <button
                                                                className="btn-sm"
                                                                onClick={() => handleDeleteUser(user)}
                                                                style={{ backgroundColor: '#dc2626', color: '#ffffff', border: '1px solid #b91c1c', fontWeight: 'bold' }}
                                                            >
                                                                🗑️ Delete
                                                            </button>
                                                        </>
                                                    )}
                                                </div>
                                            </td>
                                            <td style={{ fontWeight: 800 }}>{user.id}</td>
                                            <td style={{ fontWeight: 500 }}>{user.name || '—'}</td>
                                            <td>{user.email}</td>
                                            <td><span className={`role-badge ${user.role}`}>{user.role}</span></td>
                                            <td>{user.home_city}, {user.home_country}</td>
                                            <td>{user.login_count}</td>
                                            <td>{user.is_face_verified ? '✅' : '❌'}</td>
                                            <td>
                                                <span className={`status-badge ${user.is_blocked ? 'blocked' : 'active'}`}>
                                                    {user.is_blocked ? '🚫 Blocked' : '✅ Active'}
                                                </span>
                                            </td>
                                            <td>{formatTime(user.created_at)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <div className="empty-state"><div className="empty-state-icon">👥</div><p>No users yet</p></div>
                        )}
                    </div>
                </div>
            )}

            {/* ── Per-user Login History Modal ── */}
            {selectedUser && (
                <div className="otp-modal-overlay" onClick={() => setSelectedUser(null)}>
                    <div className="otp-modal" style={{ maxWidth: 700, width: '90%', maxHeight: '85vh', overflow: 'auto' }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                            <h3>📋 Login History — {selectedUser.name || selectedUser.email}</h3>
                            <button style={{ background: 'none', border: 'none', color: '#fff', fontSize: '1.5rem', cursor: 'pointer' }} onClick={() => setSelectedUser(null)}>✕</button>
                        </div>
                        <p style={{ color: '#94a3b8', fontSize: '0.88rem', marginBottom: 16 }}>
                            Showing last 30 authentication events for <strong>{selectedUser.email}</strong>
                        </p>
                        {userLogsLoading ? (
                            <div style={{ textAlign: 'center', padding: 40 }}><div className="loading-spinner" /></div>
                        ) : userLogs && userLogs.length > 0 ? (
                            <table className="logs-table">
                                <thead>
                                    <tr>
                                        <th>Location</th><th>Risk</th><th>Decision</th><th>Face</th><th>Travel</th><th>Time</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {userLogs.map((log, i) => (
                                        <tr key={i} className={log.is_suspicious ? 'row-suspicious' : ''}>
                                            <td>{log.city}, {log.country}</td>
                                            <td style={{ fontWeight: 700 }}>{log.total_risk}</td>
                                            <td><span className={`decision-badge ${log.decision.toLowerCase()}`}>{log.decision}</span></td>
                                            <td><span className={`face-verdict ${(log.face_verdict || '').toLowerCase()}`}>{log.face_verdict || '—'}</span></td>
                                            <td>{log.is_suspicious ? <span className="suspicious-travel-badge">⚠️ Travel</span> : '—'}</td>
                                            <td>{formatTime(log.timestamp)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <div className="empty-state"><div className="empty-state-icon">📋</div><p>No login history</p></div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

function renderDonut(allow, flag, block) {
    const total = allow + flag + block;
    if (total === 0) return null;
    const r = 56, cx = 70, cy = 70;
    const circumference = 2 * Math.PI * r;
    const segments = [
        { value: allow, color: '#10b981' },
        { value: flag, color: '#f59e0b' },
        { value: block, color: '#ef4444' },
    ];
    let offset = 0;
    return segments.map((seg, i) => {
        const pct = seg.value / total;
        const dash = pct * circumference;
        const gap = circumference - dash;
        const rotation = (offset / total) * 360 - 90;
        offset += seg.value;
        return <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke={seg.color} strokeWidth="22" strokeDasharray={`${dash} ${gap}`} transform={`rotate(${rotation} ${cx} ${cy})`} />;
    });
}

function formatTime(ts) {
    if (!ts) return '—';
    const d = new Date(ts);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) +
        ' ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}
