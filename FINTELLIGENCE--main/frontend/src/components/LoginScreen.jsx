import { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import Brand from './Brand';
import '../App.css';

export default function LoginScreen({ setToken }) {
  const [email, setEmail] = useState('admin@fintelligence.io');
  const [password, setPassword] = useState('Admin@2026');
  const [role, setRole] = useState('investigating_officer');
  const [error, setError] = useState('');

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, role }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.msg || data.error || 'Sign in failed');
      localStorage.setItem('fintelligence_token', data.access_token);
      setToken(data.access_token);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="login-shell">
      <section className="login-art">
        <div className="art-text">
          <span>CASE FILE / 2026 / AML</span>
          <h1>Trace every rupee. Investigate every signal.</h1>
        </div>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <Brand compact />
          <p className="eyebrow">SECURE LOGIN</p>
          <h2>Sign in to your investigation workspace.</h2>
          <p className="muted">Use analyst credentials below, or create users from the backend seed/admin flow.</p>
          <form onSubmit={submit}>
            <label>
              <span>Email</span>
              <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" />
            </label>
            <label>
              <span>Password</span>
              <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" />
            </label>
            <div className="login-roles">
              <span>Select Role (Optional)</span>
              <div className="radio-group">
                <label>
                  <input type="radio" value="investigating_officer" checked={role === 'investigating_officer'} onChange={(e) => setRole(e.target.value)} />
                  Investigation Officer
                </label>
                <label>
                  <input type="radio" value="supervisor" checked={role === 'supervisor'} onChange={(e) => setRole(e.target.value)} />
                  Senior Investigation Officer
                </label>
              </div>
            </div>
            {error && <div className="form-error">{error}</div>}
            <button className="primary-button" type="submit">
              Sign in <ArrowRight size={15} />
            </button>
          </form>
          <div className="demo-line">
            <span>Demo credentials</span>
            <strong>admin@fintelligence.io / Admin@2026</strong>
          </div>
        </div>
      </section>
    </div>
  );
}
