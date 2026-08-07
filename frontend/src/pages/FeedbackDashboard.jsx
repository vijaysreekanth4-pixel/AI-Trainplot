import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip as ChartTooltip,
  Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, ChartTooltip, Legend);

// Helper: build per-segment color arrays for Green(up)/Red(down) chart
function buildSegmentColors(dataArr) {
  return dataArr.map((val, i) => {
    if (i === 0) return 'rgba(16,185,129,0.9)'; // first point defaults green
    return val >= dataArr[i - 1] ? 'rgba(16,185,129,0.9)' : 'rgba(239,68,68,0.9)';
  });
}

function TradingChart({ chartData }) {
  const labels = chartData.map(d => d.name);
  const techScores = chartData.map(d => d.tech);
  const fluencyScores = chartData.map(d => d.fluency);

  const techColors = buildSegmentColors(techScores);
  const fluencyColors = buildSegmentColors(fluencyScores);

  const data = {
    labels,
    datasets: [
      {
        label: 'Tech Score',
        data: techScores,
        borderWidth: 3,
        pointRadius: 6,
        pointHoverRadius: 9,
        pointBackgroundColor: techColors,
        pointBorderColor: '#0f172a',
        pointBorderWidth: 2,
        // Segment-level color: each segment between two points is colored based on direction
        segment: {
          borderColor: ctx => {
            const next = techScores[ctx.p1DataIndex];
            const prev = techScores[ctx.p0DataIndex];
            return next >= prev ? 'rgba(16,185,129,1)' : 'rgba(239,68,68,1)';
          },
        },
        tension: 0.4,
        fill: false,
      },
      {
        label: 'Fluency Score',
        data: fluencyScores,
        borderWidth: 2,
        borderDash: [6, 3],
        pointRadius: 5,
        pointHoverRadius: 8,
        pointBackgroundColor: fluencyColors,
        pointBorderColor: '#0f172a',
        pointBorderWidth: 2,
        segment: {
          borderColor: ctx => {
            const next = fluencyScores[ctx.p1DataIndex];
            const prev = fluencyScores[ctx.p0DataIndex];
            return next >= prev ? 'rgba(16,185,129,0.7)' : 'rgba(239,68,68,0.7)';
          },
        },
        tension: 0.4,
        fill: false,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 800 },
    scales: {
      x: {
        grid: { color: 'rgba(255,255,255,0.05)' },
        ticks: { color: '#94a3b8', font: { size: 12 } },
        border: { display: false },
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: 'rgba(255,255,255,0.05)' },
        ticks: { color: '#94a3b8', font: { size: 12 } },
        border: { display: false },
      },
    },
    plugins: {
      legend: {
        labels: {
          color: '#cbd5e1',
          usePointStyle: true,
          pointStyle: 'circle',
          padding: 20,
          generateLabels: (chart) => [
            { text: '▲ Tech Score (Up = Green / Down = Red)', fillStyle: 'rgba(16,185,129,0.9)', strokeStyle: 'rgba(16,185,129,0.9)', lineWidth: 2, pointStyle: 'circle' },
            { text: '-- Fluency Score', fillStyle: 'rgba(16,185,129,0.6)', strokeStyle: 'rgba(16,185,129,0.6)', lineWidth: 2, pointStyle: 'circle', lineDash: [6, 3] },
          ],
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15,23,42,0.95)',
        titleColor: '#f8fafc',
        bodyColor: '#cbd5e1',
        borderColor: '#334155',
        borderWidth: 1,
        padding: 12,
        callbacks: {
          label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y}/100`,
        },
      },
    },
  };

  return <Line data={data} options={options} />;
}

const API = 'http://localhost:8001/api';

export default function FeedbackDashboard() {
  const location = useLocation();
  const navigate = useNavigate();
  const sessionId = location.state?.sessionId;

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!sessionId) {
      setLoading(false);
      setError('No session data found.');
      return;
    }
    axios.get(`${API}/session_result/${sessionId}`)
      .then(res => {
        setResult(res.data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError('Could not load results. Please check your connection.');
        setLoading(false);
      });
  }, [sessionId]);

  const getGrade = (score) => {
    if (score >= 85) return { grade: 'A', label: 'Excellent', color: '#10B981' };
    if (score >= 70) return { grade: 'B', label: 'Good', color: '#3B82F6' };
    if (score >= 55) return { grade: 'C', label: 'Average', color: '#F59E0B' };
    return { grade: 'D', label: 'Needs Work', color: '#EF4444' };
  };

  const getStrengths = (feedbacks) => {
    const good = feedbacks.filter(f => f.score >= 70);
    if (good.length === 0) return ['Keep practicing — consistency is key!'];
    return good.slice(0, 3).map(f => f.feedback);
  };

  const getImprovements = (feedbacks) => {
    const low = feedbacks.filter(f => f.score < 70);
    if (low.length === 0) return ['Great overall performance! Try harder domains next.'];
    return low.slice(0, 3).map(f => f.feedback);
  };

  if (loading) {
    return (
      <div className="feedback-page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⏳</div>
          <p style={{ color: '#94A3B8' }}>Loading your results...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="feedback-page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>
          <p style={{ color: '#EF4444', marginBottom: '1rem' }}>{error}</p>
          <button className="btn-primary" style={{ width: 'auto', padding: '0.7rem 2rem' }} onClick={() => navigate('/')}>
            Go Home
          </button>
        </div>
      </div>
    );
  }

  const score = result?.average_score || 0;
  const commScore = result?.avg_comm_score || score;
  const feedbacks = result?.feedbacks || [];
  const techGrade = getGrade(score);
  const commGrade = getGrade(commScore);

  const chartData = feedbacks.map((fb, i) => ({
    name: `Q${i + 1}`,
    tech: fb.score,
    fluency: fb.comm_score ?? fb.score,
  }));

  return (
    <div className="feedback-page">
      <div className="feedback-inner">
        <h1>🎉 Interview Results</h1>

        {/* Score Cards */}
        <div className="dual-score-cards" style={{ display: 'flex', gap: '2rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
          <div className="score-card" style={{ flex: '1 1 300px', margin: 0 }}>
            <div className="score-ring" style={{ borderColor: techGrade.color }}>
              <span className="score-num" style={{ color: techGrade.color }}>{score}</span>
              <span className="score-denom">/100</span>
            </div>
            <div className="score-text">
              <h2>Tech Grade: {techGrade.letter} — {techGrade.label}</h2>
              <p style={{ fontSize: '0.9rem' }}>Technical accuracy and depth of answers in <strong>{result?.domain}</strong>.</p>
            </div>
          </div>
          
          <div className="score-card" style={{ flex: '1 1 300px', margin: 0 }}>
            <div className="score-ring" style={{ borderColor: commGrade.color }}>
              <span className="score-num" style={{ color: commGrade.color }}>{commScore}</span>
              <span className="score-denom">/100</span>
            </div>
            <div className="score-text">
              <h2>Fluency Grade: {commGrade.letter} — {commGrade.label}</h2>
              <p style={{ fontSize: '0.9rem' }}>Language fluency, grammar, pronunciation, and articulation.</p>
            </div>
          </div>
        </div>

        {/* Strengths & Improvements */}
        <div className="detail-grid">
          <div className="detail-card">
            <h3 style={{ color: '#10B981' }}>✅ Strengths</h3>
            <ul>
              {getStrengths(feedbacks).map((s, i) => (
                <li key={i}><span style={{ color: '#10B981' }}>•</span> {s}</li>
              ))}
            </ul>
          </div>
          <div className="detail-card">
            <h3 style={{ color: '#F59E0B' }}>⚡ Areas to Improve</h3>
            <ul>
              {getImprovements(feedbacks).map((s, i) => (
                <li key={i}><span style={{ color: '#F59E0B' }}>•</span> {s}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Performance Graph — Trading Style */}
        {feedbacks.length > 0 && (
          <div className="graph-section" style={{ background: 'rgba(15,23,42,0.7)', padding: '1.5rem 2rem', borderRadius: '16px', marginBottom: '2rem', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <h3 style={{ margin: 0 }}>📈 Performance Chart</h3>
              <div style={{ display: 'flex', gap: '1rem', fontSize: '0.78rem', color: '#64748b' }}>
                <span style={{ color: '#10B981' }}>▲ Rising</span>
                <span style={{ color: '#EF4444' }}>▼ Falling</span>
              </div>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#475569', margin: '0 0 1.2rem 0' }}>Green = score improved · Red = score dropped — hover any point for details</p>
            <div style={{ width: '100%', height: '340px' }}>
              <TradingChart chartData={chartData} />
            </div>
          </div>
        )}

        {/* Q&A Breakdown - ChatGPT Style */}
        {feedbacks.length > 0 && (
          <div className="qa-section" style={{ background: '#1e293b', borderRadius: '12px', padding: '1rem', marginTop: '2rem' }}>
            <h3 style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem', marginBottom: '1.5rem', textAlign: 'center' }}>💬 Interview Chat History</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {feedbacks.map((fb, i) => {
                const isCorrect = fb.score >= 85;
                const isFluencyGood = (fb.comm_score ?? fb.score) >= 85;
                const displayTechScore = isCorrect ? fb.score : 0;
                const displayFluencyScore = isFluencyGood ? (fb.comm_score ?? fb.score) : 0;

                return (
                  <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {/* Kerin Question Bubble */}
                    <div style={{ display: 'flex', gap: '1rem', maxWidth: '85%' }}>
                      <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: '#3B82F6', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem', flexShrink: 0 }}>🤖</div>
                      <div style={{ background: 'rgba(255,255,255,0.05)', padding: '1rem', borderRadius: '0 12px 12px 12px', color: '#f8fafc', fontSize: '0.95rem', lineHeight: 1.5 }}>
                        <div style={{ fontWeight: 700, color: '#94a3b8', fontSize: '0.75rem', marginBottom: '0.3rem' }}>Kerin (AI) - Q{i + 1}</div>
                        {fb.question}
                      </div>
                    </div>

                    {/* Candidate Answer Bubble */}
                    <div style={{ display: 'flex', gap: '1rem', maxWidth: '85%', alignSelf: 'flex-end', flexDirection: 'row-reverse' }}>
                      <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: '#10B981', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem', flexShrink: 0 }}>👤</div>
                      <div style={{ background: '#2563eb', padding: '1rem', borderRadius: '12px 0 12px 12px', color: '#ffffff', fontSize: '0.95rem', lineHeight: 1.5 }}>
                        <div style={{ fontWeight: 700, color: '#bfdbfe', fontSize: '0.75rem', marginBottom: '0.3rem', textAlign: 'right' }}>You</div>
                        {fb.answer}
                      </div>
                    </div>

                    {/* Kerin Feedback Bubble */}
                    <div style={{ display: 'flex', gap: '1rem', maxWidth: '90%' }}>
                      <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: '#3B82F6', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.2rem', flexShrink: 0 }}>🤖</div>
                      <div style={{ background: 'rgba(255,255,255,0.05)', padding: '1rem', borderRadius: '0 12px 12px 12px', color: '#f8fafc', fontSize: '0.95rem', lineHeight: 1.5, borderLeft: `3px solid ${isCorrect ? '#10B981' : '#EF4444'}` }}>
                        <div style={{ fontWeight: 700, color: '#94a3b8', fontSize: '0.75rem', marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between' }}>
                          <span>Kerin (Feedback)</span>
                          <span style={{ color: isCorrect ? '#10B981' : '#EF4444' }}>{isCorrect ? '✅ Accepted' : '❌ Needs Improvement'}</span>
                        </div>
                        
                        <div style={{ marginBottom: '1rem' }}>{fb.feedback}</div>
                        
                        {/* Scores */}
                        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                          <span style={{ background: 'rgba(255,255,255,0.1)', padding: '0.2rem 0.6rem', borderRadius: '4px', fontSize: '0.8rem' }}>🧠 Tech: {displayTechScore}/100</span>
                          <span style={{ background: 'rgba(255,255,255,0.1)', padding: '0.2rem 0.6rem', borderRadius: '4px', fontSize: '0.8rem' }}>🗣️ Fluency: {displayFluencyScore}/100</span>
                        </div>

                        {/* Language Feedback if any */}
                        {fb.language_feedback && (
                          <div style={{ fontSize: '0.85rem', color: isFluencyGood ? '#93c5fd' : '#fca5a5', marginBottom: '1rem', paddingLeft: '0.5rem', borderLeft: `2px solid ${isFluencyGood ? '#3B82F6' : '#EF4444'}` }}>
                            {fb.language_feedback}
                          </div>
                        )}

                        {/* Correct Answer */}
                        <div style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', padding: '0.75rem', borderRadius: '8px' }}>
                          <div style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 700, marginBottom: '0.3rem' }}>IDEAL ANSWER</div>
                          <div style={{ color: '#d1fae5', fontSize: '0.85rem' }}>{fb.correct_answer || 'A detailed answer covering core concepts, examples, and trade-offs is expected.'}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}


        {/* Actions */}
        <div className="action-row">
          <button className="btn-primary" style={{ width: 'auto', padding: '0.75rem 2rem' }} onClick={() => navigate('/setup')}>
            🔄 Try Another Interview
          </button>
          <button className="btn-secondary" onClick={() => navigate('/')}>
            🏠 Back to Home
          </button>
          <button
            className="btn-secondary"
            onClick={() => {
              const report = feedbacks.map((f, i) =>
                `Q${i+1}: ${f.question}\nAnswer: ${f.answer}\nFeedback: ${f.feedback}\nScore: ${f.score}/100\n`
              ).join('\n---\n');
              const blob = new Blob([`Interview Results\nDomain: ${result.domain}\nAverage Score: ${score}/100\n\n${report}`], { type: 'text/plain' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url; a.download = 'interview_report.txt'; a.click();
            }}
          >
            📥 Download Report
          </button>
        </div>
      </div>
    </div>
  );
}
