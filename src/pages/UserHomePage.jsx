import { useState, useEffect } from 'react';

export default function UserHomePage({ onLogout }) {
    const name = localStorage.getItem('name') || localStorage.getItem('email')?.split('@')[0] || 'User';
    const [currentTime, setCurrentTime] = useState(new Date());
    const [activeService, setActiveService] = useState(null);

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    // Simulated market data
    const marketData = [
        { symbol: 'NIFTY 50', value: '22,456.80', change: '+1.24%', up: true },
        { symbol: 'SENSEX', value: '73,890.45', change: '+0.87%', up: true },
        { symbol: 'BANK NIFTY', value: '47,234.15', change: '-0.32%', up: false },
        { symbol: 'GOLD', value: '₹71,450', change: '+0.56%', up: true },
        { symbol: 'USD/INR', value: '83.42', change: '-0.15%', up: false },
        { symbol: 'BITCOIN', value: '$67,890', change: '+2.45%', up: true },
    ];

    const services = [
        { icon: '💳', title: 'Smart Payments', desc: 'Instant UPI, NEFT, RTGS & international transfers with zero downtime', color: '#6366f1' },
        { icon: '📈', title: 'Wealth Management', desc: 'AI-powered mutual funds, stocks, and SIP investments with smart recommendations', color: '#10b981' },
        { icon: '🛡️', title: 'Insurance Hub', desc: 'Life, health, vehicle & travel insurance with instant claim processing', color: '#f59e0b' },
        { icon: '🏦', title: 'Digital Loans', desc: 'Personal, home & business loans with instant approval in under 2 minutes', color: '#ef4444' },
        { icon: '💰', title: 'Fixed Deposits', desc: 'High-interest FDs & RDs with flexible tenures and auto-renewal options', color: '#8b5cf6' },
        { icon: '🌐', title: 'Forex & Crypto', desc: 'Trade forex pairs and cryptocurrencies with real-time market insights', color: '#06b6d4' },
    ];

    const features = [
        { icon: '🔐', title: 'Bank-Grade Security', desc: '256-bit encryption with AI fraud detection' },
        { icon: '⚡', title: 'Lightning Fast', desc: 'Transactions processed in under 2 seconds' },
        { icon: '📱', title: '24/7 Access', desc: 'Manage your finances anytime, anywhere' },
        { icon: '🤖', title: 'AI Powered', desc: 'Smart insights and personalized recommendations' },
    ];

    const transactions = [
        { type: 'credit', desc: 'Salary Credit', amount: '+₹45,000.00', date: 'Today', icon: '💼' },
        { type: 'debit', desc: 'Electricity Bill', amount: '-₹2,340.00', date: 'Yesterday', icon: '⚡' },
        { type: 'credit', desc: 'Investment Return', amount: '+₹8,750.00', date: 'Mar 17', icon: '📈' },
        { type: 'debit', desc: 'Online Shopping', amount: '-₹3,999.00', date: 'Mar 16', icon: '🛒' },
        { type: 'credit', desc: 'Freelance Payment', amount: '+₹15,000.00', date: 'Mar 15', icon: '💻' },
    ];

    const greeting = currentTime.getHours() < 12 ? 'Good Morning' : currentTime.getHours() < 17 ? 'Good Afternoon' : 'Good Evening';

    return (
        <div className="fin-home">
            {/* Market Ticker Bar */}
            <div className="fin-ticker-bar">
                <div className="fin-ticker-content">
                    {[...marketData, ...marketData].map((item, i) => (
                        <span key={i} className="fin-ticker-item">
                            <span className="fin-ticker-symbol">{item.symbol}</span>
                            <span className="fin-ticker-value">{item.value}</span>
                            <span className={`fin-ticker-change ${item.up ? 'up' : 'down'}`}>
                                {item.up ? '▲' : '▼'} {item.change}
                            </span>
                        </span>
                    ))}
                </div>
            </div>

            {/* Hero Section */}
            <section className="fin-hero">
                <div className="fin-hero-bg-orbs">
                    <div className="fin-orb fin-orb-1"></div>
                    <div className="fin-orb fin-orb-2"></div>
                    <div className="fin-orb fin-orb-3"></div>
                </div>
                <div className="fin-hero-content">
                    <div className="fin-hero-greeting">{greeting}, <span className="fin-hero-name">{name}</span> 👋</div>
                    <h1 className="fin-hero-title">
                        Your Financial<br />
                        <span className="fin-gradient-text">Command Center</span>
                    </h1>
                    <p className="fin-hero-subtitle">
                        Manage your money, investments, and insurance — all in one secure platform powered by AI
                    </p>
                    <div className="fin-hero-stats">
                        <div className="fin-hero-stat">
                            <div className="fin-hero-stat-value">₹2,45,890</div>
                            <div className="fin-hero-stat-label">Total Balance</div>
                        </div>
                        <div className="fin-hero-stat-divider"></div>
                        <div className="fin-hero-stat">
                            <div className="fin-hero-stat-value">₹1,28,500</div>
                            <div className="fin-hero-stat-label">Investments</div>
                        </div>
                        <div className="fin-hero-stat-divider"></div>
                        <div className="fin-hero-stat">
                            <div className="fin-hero-stat-value">8.2%</div>
                            <div className="fin-hero-stat-label">Returns (YTD)</div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Quick Actions */}
            <section className="fin-section">
                <div className="fin-quick-actions">
                    <button className="fin-quick-btn">
                        <span className="fin-quick-icon">📤</span>
                        <span>Send Money</span>
                    </button>
                    <button className="fin-quick-btn">
                        <span className="fin-quick-icon">📥</span>
                        <span>Receive</span>
                    </button>
                    <button className="fin-quick-btn">
                        <span className="fin-quick-icon">📊</span>
                        <span>Invest</span>
                    </button>
                    <button className="fin-quick-btn">
                        <span className="fin-quick-icon">💳</span>
                        <span>Pay Bills</span>
                    </button>
                    <button className="fin-quick-btn">
                        <span className="fin-quick-icon">🔄</span>
                        <span>Transfer</span>
                    </button>
                </div>
            </section>

            {/* Recent Transactions */}
            <section className="fin-section">
                <div className="fin-section-header">
                    <h2>Recent Transactions</h2>
                    <button className="fin-link-btn">View All →</button>
                </div>
                <div className="fin-transactions-card">
                    {transactions.map((tx, i) => (
                        <div key={i} className="fin-tx-row">
                            <div className="fin-tx-icon">{tx.icon}</div>
                            <div className="fin-tx-info">
                                <div className="fin-tx-desc">{tx.desc}</div>
                                <div className="fin-tx-date">{tx.date}</div>
                            </div>
                            <div className={`fin-tx-amount ${tx.type}`}>{tx.amount}</div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Services */}
            <section className="fin-section">
                <div className="fin-section-header">
                    <h2>Our Services</h2>
                    <p className="fin-section-desc">Everything you need to manage your financial life</p>
                </div>
                <div className="fin-services-grid">
                    {services.map((svc, i) => (
                        <div
                            key={i}
                            className={`fin-service-card ${activeService === i ? 'active' : ''}`}
                            onMouseEnter={() => setActiveService(i)}
                            onMouseLeave={() => setActiveService(null)}
                        >
                            <div className="fin-service-icon" style={{ background: `${svc.color}20`, color: svc.color }}>
                                {svc.icon}
                            </div>
                            <h3>{svc.title}</h3>
                            <p>{svc.desc}</p>
                            <div className="fin-service-arrow" style={{ color: svc.color }}>
                                Explore →
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Market Overview */}
            <section className="fin-section">
                <div className="fin-section-header">
                    <h2>Market Overview</h2>
                    <div className="fin-live-badge">
                        <span className="fin-live-dot"></span> LIVE
                    </div>
                </div>
                <div className="fin-market-grid">
                    {marketData.map((item, i) => (
                        <div key={i} className="fin-market-card">
                            <div className="fin-market-symbol">{item.symbol}</div>
                            <div className="fin-market-value">{item.value}</div>
                            <div className={`fin-market-change ${item.up ? 'up' : 'down'}`}>
                                {item.up ? '📈' : '📉'} {item.change}
                            </div>
                            <div className="fin-market-chart">
                                <svg viewBox="0 0 100 30" className={`fin-mini-chart ${item.up ? 'up' : 'down'}`}>
                                    <polyline
                                        fill="none"
                                        strokeWidth="2"
                                        strokeLinecap="round"
                                        points={item.up
                                            ? "0,25 15,20 30,22 45,15 60,18 75,10 100,5"
                                            : "0,5 15,10 30,8 45,18 60,15 75,22 100,25"
                                        }
                                    />
                                </svg>
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Features / Trust Section */}
            <section className="fin-section fin-trust-section">
                <div className="fin-section-header">
                    <h2>Why Choose Us</h2>
                    <p className="fin-section-desc">Trusted by over 10 million users across India</p>
                </div>
                <div className="fin-features-grid">
                    {features.map((feat, i) => (
                        <div key={i} className="fin-feature-card">
                            <div className="fin-feature-icon">{feat.icon}</div>
                            <h3>{feat.title}</h3>
                            <p>{feat.desc}</p>
                        </div>
                    ))}
                </div>
            </section>

            {/* Footer */}
            <footer className="fin-footer">
                <div className="fin-footer-content">
                    <div className="fin-footer-brand">
                        <div className="fin-footer-logo">⚛ QuantumShield Finance</div>
                        <p>Secure, smart, and simple financial services for everyone.</p>
                    </div>
                    <div className="fin-footer-links">
                        <div className="fin-footer-col">
                            <h4>Products</h4>
                            <a href="#">Payments</a>
                            <a href="#">Investments</a>
                            <a href="#">Insurance</a>
                            <a href="#">Loans</a>
                        </div>
                        <div className="fin-footer-col">
                            <h4>Company</h4>
                            <a href="#">About Us</a>
                            <a href="#">Careers</a>
                            <a href="#">Blog</a>
                            <a href="#">Contact</a>
                        </div>
                        <div className="fin-footer-col">
                            <h4>Legal</h4>
                            <a href="#">Privacy Policy</a>
                            <a href="#">Terms of Service</a>
                            <a href="#">Security</a>
                        </div>
                    </div>
                </div>
                <div className="fin-footer-bottom">
                    <span>© 2026 QuantumShield Finance. All rights reserved.</span>
                    <span>RBI Licensed • SEBI Registered • IRDAI Approved</span>
                </div>
            </footer>
        </div>
    );
}
