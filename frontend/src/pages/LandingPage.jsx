import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const EyeOpen = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
  </svg>
);
const EyeOff = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
    <line x1="1" y1="1" x2="23" y2="23"/>
  </svg>
);

export default function LandingPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState('signin');
  const [form, setForm] = useState({ firstName: '', lastName: '', phone: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPasswordSignin, setShowPasswordSignin] = useState(false);
  const [showPasswordSignup, setShowPasswordSignup] = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  // ── SIGN IN ──
  const handleSignIn = (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    const { email, password } = form;
    if (!email || !password) { setError('Please fill in all fields.'); return; }

    const users = JSON.parse(localStorage.getItem('iai_users') || '{}');
    const user = users[email.toLowerCase()];
    if (!user) { setError('No account found. Please sign up first.'); return; }
    if (atob(user.password) !== password) { setError('Incorrect password. Please try again.'); return; }

    setSuccess('✅ Signed in! Redirecting...');
    setTimeout(() => {
      localStorage.setItem('iai_current', JSON.stringify(user));
      navigate('/setup');
    }, 600);
  };

  // ── SIGN UP ──
  const handleSignUp = (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    const { firstName, lastName, phone, email, password } = form;

    if (!firstName || !lastName) { setError('Please enter your first and last name.'); return; }
    if (!/^\d{10}$/.test(phone.replace(/\D/g, ''))) { setError('Please enter a valid 10-digit phone number.'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError('Please enter a valid email address.'); return; }
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return; }

    const users = JSON.parse(localStorage.getItem('iai_users') || '{}');
    if (users[email.toLowerCase()]) { setError('This email is already registered. Please sign in.'); return; }

    const user = {
      firstName, lastName, phone,
      email: email.toLowerCase(),
      password: btoa(password),
      createdAt: new Date().toISOString()
    };
    users[email.toLowerCase()] = user;
    localStorage.setItem('iai_users', JSON.stringify(users));

    setSuccess('✅ Account created! Signing you in...');
    setLoading(true);
    setTimeout(() => {
      localStorage.setItem('iai_current', JSON.stringify(user));
      navigate('/setup');
    }, 800);
  };

  return (
    <div className="page">
      <nav className="nav">
        <a href="/" className="nav-brand">
          <svg width="24" height="24" fill="none" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
            <path d="M8 12h8M12 8v8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          AI Trainplot
        </a>
      </nav>

      <main className="landing-main">
        {/* Left */}
        <div className="landing-left">
          <h1 className="landing-title">
            Master Your <span className="highlight">AI-Powered</span><br />Job Interview
          </h1>
          <p className="landing-desc">
            Upload your resume, get personalized questions from <strong>Kerin</strong> — your AI interviewer — and receive expert feedback powered by LangGraph RAG + OpenAI.
          </p>
          <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            {['🧠 LangGraph AI', '📄 Resume RAG', '🎙️ Voice Interview', '📊 Live Scoring'].map(f => (
              <span key={f} style={{
                background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)',
                borderRadius: '20px', padding: '0.35rem 0.9rem', fontSize: '0.82rem', color: '#a5b4fc'
              }}>{f}</span>
            ))}
          </div>
        </div>

        {/* Auth Card */}
        <div className="auth-card">
          <h2 style={{ marginBottom: '0.4rem' }}>
            {tab === 'signin' ? '👋 Welcome Back!' : '🚀 Create Account'}
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.87rem', marginBottom: '1.2rem' }}>
            {tab === 'signin'
              ? 'Sign in to start your AI interview practice.'
              : 'Fill in your details to get started for free.'}
          </p>

          {/* Tabs */}
          <div className="tab-row">
            <button className={`tab-btn ${tab === 'signin' ? 'active' : ''}`}
              onClick={() => { setTab('signin'); setError(''); setSuccess(''); }}>
              Sign In
            </button>
            <button className={`tab-btn ${tab === 'signup' ? 'active' : ''}`}
              onClick={() => { setTab('signup'); setError(''); setSuccess(''); }}>
              Sign Up
            </button>
          </div>

          {/* ── SIGN IN FORM ── */}
          {tab === 'signin' && (
            <form onSubmit={handleSignIn}>
              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  placeholder="you@company.com"
                  value={form.email}
                  onChange={e => set('email', e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPasswordSignin ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={form.password}
                    onChange={e => set('password', e.target.value)}
                    required
                    style={{ paddingRight: '2.8rem', width: '100%', boxSizing: 'border-box' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPasswordSignin(v => !v)}
                    style={{
                      position: 'absolute', right: '0.75rem', top: '50%',
                      transform: 'translateY(-50%)', background: 'none',
                      border: 'none', cursor: 'pointer', color: '#64748b', padding: 0
                    }}
                  >
                    {showPasswordSignin ? <EyeOff /> : <EyeOpen />}
                  </button>
                </div>
              </div>

              {error && <div className="error-msg">⚠️ {error}</div>}
              {success && <div className="success-msg">{success}</div>}

              <div style={{ textAlign: 'right', marginTop: '0.5rem', marginBottom: '1rem' }}>
                <a href="#" onClick={(e) => { e.preventDefault(); setTab('forgot'); setError(''); setSuccess(''); }} style={{ color: '#3B82F6', fontSize: '0.85rem', textDecoration: 'none' }}>Forgot Password?</a>
              </div>

              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Signing in...' : 'Sign In →'}
              </button>
            </form>
          )}

          {/* ── FORGOT PASSWORD FORM ── */}
          {tab === 'forgot' && (
            <form onSubmit={(e) => {
              e.preventDefault();
              setError(''); setSuccess('');
              const { email, password } = form;
              if (!email || !password) { setError('Please fill in all fields.'); return; }
              if (password.length < 6) { setError('Password must be at least 6 characters.'); return; }
              
              const users = JSON.parse(localStorage.getItem('iai_users') || '{}');
              if (!users[email.toLowerCase()]) { setError('No account found with this email.'); return; }
              
              users[email.toLowerCase()].password = btoa(password);
              localStorage.setItem('iai_users', JSON.stringify(users));
              setSuccess('✅ Password reset successfully! You can now sign in.');
              setTimeout(() => { setTab('signin'); form.password = ''; }, 1500);
            }}>
              <div className="form-group">
                <label>Registered Email Address</label>
                <input
                  type="email"
                  placeholder="you@company.com"
                  value={form.email}
                  onChange={e => set('email', e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>New Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPasswordSignin ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={form.password}
                    onChange={e => set('password', e.target.value)}
                    required
                    style={{ paddingRight: '2.8rem', width: '100%', boxSizing: 'border-box' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPasswordSignin(v => !v)}
                    style={{
                      position: 'absolute', right: '0.75rem', top: '50%',
                      transform: 'translateY(-50%)', background: 'none',
                      border: 'none', cursor: 'pointer', color: '#64748b', padding: 0
                    }}
                  >
                    {showPasswordSignin ? <EyeOff /> : <EyeOpen />}
                  </button>
                </div>
              </div>

              {error && <div className="error-msg">⚠️ {error}</div>}
              {success && <div className="success-msg">{success}</div>}

              <button type="submit" className="btn-primary" disabled={loading} style={{ marginTop: '0.5rem' }}>
                Reset Password
              </button>
              
              <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                <a href="#" onClick={(e) => { e.preventDefault(); setTab('signin'); setError(''); setSuccess(''); }} style={{ color: '#94a3b8', fontSize: '0.85rem', textDecoration: 'none' }}>
                  ← Back to Sign In
                </a>
              </div>
            </form>
          )}

          {/* ── SIGN UP FORM ── */}
          {tab === 'signup' && (
            <form onSubmit={handleSignUp}>
              <div className="grid-2">
                <div className="form-group">
                  <label>First Name</label>
                  <input type="text" placeholder="Ravi" value={form.firstName}
                    onChange={e => set('firstName', e.target.value)} required />
                </div>
                <div className="form-group">
                  <label>Last Name</label>
                  <input type="text" placeholder="Kumar" value={form.lastName}
                    onChange={e => set('lastName', e.target.value)} required />
                </div>
              </div>
              <div className="form-group">
                <label>Phone Number</label>
                <input type="tel" placeholder="+91 9876543210" value={form.phone}
                  onChange={e => set('phone', e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input type="email" placeholder="ravi@example.com" value={form.email}
                  onChange={e => set('email', e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Password (min 6 characters)</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPasswordSignup ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={form.password}
                    onChange={e => set('password', e.target.value)}
                    required
                    style={{ paddingRight: '2.8rem', width: '100%', boxSizing: 'border-box' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPasswordSignup(v => !v)}
                    style={{
                      position: 'absolute', right: '0.75rem', top: '50%',
                      transform: 'translateY(-50%)', background: 'none',
                      border: 'none', cursor: 'pointer', color: '#64748b', padding: 0
                    }}
                  >
                    {showPasswordSignup ? <EyeOff /> : <EyeOpen />}
                  </button>
                </div>
              </div>

              {error && <div className="error-msg">⚠️ {error}</div>}
              {success && <div className="success-msg">{success}</div>}

              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Creating Account...' : 'Create Account →'}
              </button>
            </form>
          )}

        </div>
      </main>
    </div>
  );
}
