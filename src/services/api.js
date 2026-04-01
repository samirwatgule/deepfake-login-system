// ─── Real API Service — QuantumShield ───
// All calls hit the Flask backend at /api/*
// Vite proxy forwards /api → http://localhost:5000

import axios from 'axios';

const api = axios.create({
    baseURL: '',
    headers: { 'Content-Type': 'application/json' },
    timeout: 30000, // 30s for ML model inference
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Handle 401 responses (expired token) — only clear session for protected endpoints
api.interceptors.response.use(
    (res) => res,
    (err) => {
        if (err.response?.status === 401) {
            const url = err.config?.url || '';
            // Don't clear session on login/register failures — only on protected API calls
            const isAuthEndpoint = url.includes('/api/login') || url.includes('/api/register') || url.includes('/api/admin/login');
            if (!isAuthEndpoint) {
                localStorage.removeItem('token');
                localStorage.removeItem('email');
                localStorage.removeItem('role');
                localStorage.removeItem('name');
            }
        }
        return Promise.reject(err);
    }
);

// ─── Auth API ───────────────────────────────────────────────────────────────

export const registerUser = (data) => api.post('/api/register', data);

export const loginUser = (data) => api.post('/api/login', data);

export const adminLogin = (data) => api.post('/api/admin/login', data);

// ─── User API ───────────────────────────────────────────────────────────────

export const getUserProfile = () => api.get('/api/user/profile');

export const getUserLogs = (params) => api.get('/api/user/logs', { params });

// ─── Admin API ──────────────────────────────────────────────────────────────

export const getStats = () => api.get('/api/admin/stats');

export const getLoginLogs = (params) => api.get('/api/admin/logs', { params });

export const getUsers = () => api.get('/api/admin/users');

export const toggleBlockUser = (userId) => api.post(`/api/admin/users/${userId}/block`);

export const getUserById = (userId) => api.get(`/api/admin/users/${userId}/logs`);

export const deleteUser = (userId) => api.delete(`/api/admin/users/${userId}`);

// ─── Deepfake Detection API ─────────────────────────────────────────────────

export const detectImage = (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/detect/image', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
};

export const detectWebcam = (base64Image) =>
    api.post('/api/detect/webcam', { image: base64Image });

// ─── Health ─────────────────────────────────────────────────────────────────

export const healthCheck = () => api.get('/api/health');

// ─── Utility ────────────────────────────────────────────────────────────────

export const collectDeviceInfo = () => ({
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    language: navigator.language,
    screenResolution: `${window.screen.width}x${window.screen.height}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    colorDepth: window.screen.colorDepth,
    hardwareConcurrency: navigator.hardwareConcurrency || 0,
    touchSupport: 'ontouchstart' in window,
});

export default {
    registerUser, loginUser, adminLogin,
    getUserProfile, getUserLogs,
    getStats, getLoginLogs, getUsers, toggleBlockUser, getUserById, deleteUser,
    detectImage, detectWebcam, healthCheck, collectDeviceInfo,
};
