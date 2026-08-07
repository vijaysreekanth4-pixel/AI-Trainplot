import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API = 'http://localhost:8001/api';

const DOMAINS = [
  'Software Engineering',
  'Data Science',
  'Product Management',
  'UI/UX Design',
  'DevOps Engineering',
  'Machine Learning',
  'Business Analysis',
  'Cloud Architecture',
  'Cybersecurity',
  'Mobile Development',
];

export default function InterviewSetup() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('iai_current') || '{"firstName":"Candidate"}');

  const [domain, setDomain] = useState('Software Engineering');
  const [difficulty, setDifficulty] = useState('Medium');
  const [apiKey, setApiKey] = useState(localStorage.getItem('openai_api_key') || '');
  const [resume, setResume] = useState(null);
  const [resumeSessionId, setResumeSessionId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');

  const handleResumeUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.match(/\.(pdf|txt)$/i)) {
      setError('Only PDF or TXT files are supported.');
      return;
    }

    setResume(file);
    setError('');
    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    const headers = { 'Content-Type': 'multipart/form-data' };
    if (apiKey) headers['X-OpenAI-Key'] = apiKey;

    try {
      const res = await axios.post(`${API}/upload_resume`, formData, { headers });
      setResumeSessionId(res.data.resume_session_id);
    } catch (err) {
      console.error('Upload error:', err);
      setError('Could not upload resume. Is the backend server running on port 8001?');
      setResume(null);
    } finally {
      setUploading(false);
    }
  };

  const handleStart = async () => {
    if (!resume) {
      setError('Please upload your resume first to get personalized questions.');
      return;
    }
    setError('');
    setStarting(true);

    try {
      const payload = {
        name: `${user.firstName} ${user.lastName || ''}`.trim(),
        experience: '3 years',
        domain,
        difficulty,
        focus_area: 'Technical + Behavioral',
        resume_session_id: resumeSessionId,
        openai_api_key: apiKey,
      };
      if (apiKey) localStorage.setItem('openai_api_key', apiKey);
      const res = await axios.post(`${API}/setup_interview`, payload);
      const { session_id, first_question, total_questions } = res.data;

      navigate('/interview', {
        state: { sessionId: session_id, domain, firstQuestion: first_question, totalQuestions: total_questions },
      });
    } catch (err) {
      console.error('Setup error:', err);
      setError('Could not start interview. Is the backend server running on port 8001?');
      setStarting(false);
    }
  };

  return (
    <div className="setup-page">
      <div className="setup-card">
        <h2>Interview Setup</h2>
        <p>Configure your session. Upload your resume for personalized AI questions.</p>

        <div className="grid-2">
          <div className="form-group">
            <label>Job Domain</label>
            <select value={domain} onChange={e => setDomain(e.target.value)}>
              <option>Software Engineering</option>
              <option>Data Science</option>
              <option>Product Management</option>
              <option>UI/UX Design</option>
              <option>DevOps / Cloud</option>
              <option>Cybersecurity</option>
              <option>Marketing</option>
              <option>HR & Recruiting</option>
              <option>Finance</option>
            </select>
          </div>
          <div className="form-group">
            <label>Difficulty Level</label>
            <select value={difficulty} onChange={e => setDifficulty(e.target.value)}>
              <option>Fresher</option>
              <option>Junior</option>
              <option>Medium</option>
              <option>Senior</option>
              <option>Lead</option>
            </select>
          </div>
          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label>OpenAI API Key (Required for true LLM)</label>
            <input 
              type="password" 
              placeholder="sk-..." 
              value={apiKey} 
              onChange={e => setApiKey(e.target.value)} 
              style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)', color: 'white' }}
            />
          </div>
        </div>

        <div className="form-group" style={{ display: 'flex', alignItems: 'center', color: '#94A3B8', fontSize: '0.9rem', background: 'rgba(255,255,255,0.03)', padding: '0.8rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
          🤖 ARIA will automatically ask 10+ questions based on your resume depth.
        </div>

        {/* Resume Upload */}
        <label className={`upload-area ${resume ? 'uploaded' : ''}`} style={{ display: 'block', cursor: 'pointer' }}>
          <input type="file" accept=".pdf,.txt" style={{ display: 'none' }} onChange={handleResumeUpload} />
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
              {uploading ? '⏳' : resume ? '✅' : '📄'}
            </div>
            <p>
              {uploading
                ? 'Uploading and indexing resume...'
                : resume
                ? <><strong>{resume.name}</strong> — Resume indexed!</>
                : <><strong>Click to upload Resume</strong><br />Supports PDF or TXT</>}
            </p>
            {resumeSessionId && <p style={{ color: '#10B981', fontSize: '0.8rem', marginTop: '0.3rem' }}>✓ Indexed into FAISS vector store</p>}
          </div>
        </label>

        {error && <div className="error-msg" style={{ display: 'block', marginBottom: '1rem' }}>{error}</div>}

        <button
          className="btn-primary"
          onClick={handleStart}
          disabled={starting || uploading}
        >
          {starting ? '⏳ Starting Interview...' : '▶ Start AI Interview'}
        </button>

        <button
          className="btn-secondary"
          style={{ width: '100%', marginTop: '0.75rem', textAlign: 'center' }}
          onClick={() => navigate('/')}
        >
          ← Back
        </button>
      </div>
    </div>
  );
}
