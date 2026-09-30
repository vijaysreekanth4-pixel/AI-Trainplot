import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';

const INTERVIEWERS = [
  { name: 'Kerin',   role: 'Technical Lead',       img: '/assets/interviewer_f_1.jpg' },
  { name: 'Kerin',   role: 'System Architect',     img: '/assets/interviewer_f_2.jpg' },
  { name: 'Kerin',   role: 'Interview Director',   img: '/assets/interviewer_f_3.jpg' },
  { name: 'Kerin',   role: 'Analysis Engine',      img: '/assets/interviewer_f_4.jpg' },
  { name: 'Kerin',   role: 'Core AI',              img: '/assets/interviewer_f_5.jpg' },
  { name: 'Kerin',   role: 'Evaluation Matrix',    img: '/assets/interviewer_f_6.jpg' },
  { name: 'Kerin',   role: 'Neural Network',       img: '/assets/interviewer_f_7.jpg' },
  { name: 'Kerin',   role: 'Data Synthesizer',     img: '/assets/interviewer_f_8.jpg' },
  { name: 'Kerin',   role: 'Logic Processor',      img: '/assets/interviewer_m_1.jpg' },
  { name: 'Kerin',   role: 'System Protocol',      img: '/assets/interviewer_m_2.jpg' },
  { name: 'Kerin',   role: 'Technical Analyst',    img: '/assets/interviewer_m_3.jpg' },
  { name: 'Kerin',   role: 'Cognitive Module',     img: '/assets/interviewer_m_4.jpg' },
  { name: 'Kerin',   role: 'Interview Engine',     img: '/assets/interviewer_m_5.jpg' },
  { name: 'Kerin',   role: 'Behavioral AI',        img: '/assets/interviewer_m_6.jpg' },
  { name: 'Kerin',   role: 'Decision Matrix',      img: '/assets/interviewer_m_7.jpg' },
  { name: 'Kerin',   role: 'Knowledge Graph',      img: '/assets/interviewer_m_8.jpg' },
];

const getGrade = (s) => {
  if (s >= 85) return { letter: 'A', label: 'Excellent', color: '#10B981' };
  if (s >= 70) return { letter: 'B', label: 'Good',      color: '#3B82F6' };
  if (s >= 55) return { letter: 'C', label: 'Average',   color: '#F59E0B' };
  return                { letter: 'D', label: 'Needs Work',color: '#EF4444' };
};

export default function InterviewRoom() {
  const location = useLocation();
  const navigate = useNavigate();

  const sessionId     = location.state?.sessionId;
  const domain        = location.state?.domain || 'General';
  const firstQuestion = location.state?.firstQuestion || "Hello! I'm your AI Interviewer. Tell me about yourself.";

  const [interviewer]   = useState(() => INTERVIEWERS[Math.floor(Math.random() * INTERVIEWERS.length)]);
  const [isMicOn,       setIsMicOn]       = useState(false);
  const [isVideoOn,     setIsVideoOn]     = useState(true);
  const [isThinking,    setIsThinking]    = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState(firstQuestion);
  const [messages,      setMessages]      = useState([]);
  const [questionNum,   setQuestionNum]   = useState(1);
  const [isComplete,    setIsComplete]    = useState(false);
  const [ariaWaiting,   setAriaWaiting]   = useState(true);
  const [isAITalking,   setIsAITalking]   = useState(false);
  const [lastScore,     setLastScore]     = useState(null);
  const [lastCommScore, setLastCommScore] = useState(null);

  const recognitionRef  = useRef(null);
  const synthRef        = useRef(window.speechSynthesis);
  const messagesEndRef  = useRef(null);
  const videoRef        = useRef(null);
  const streamRef       = useRef(null);
  const accumulatedRef  = useRef('');   // accumulates all speech chunks
  const silenceTimerRef = useRef(null); // silence detection timer
  const [liveTranscript, setLiveTranscript] = useState(''); // shows live words

  // ── Redirect if no session ──
  useEffect(() => {
    if (!sessionId) {
      alert('No active session. Please start from Setup.');
      navigate('/setup');
    }
  }, [sessionId, navigate]);

  // ── Auto-scroll transcript ──
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Setup Live Webcam ──
  useEffect(() => {
    async function setupCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (err) {
        console.error('Error accessing webcam:', err);
      }
    }
    setupCamera();
    return () => { streamRef.current?.getTracks().forEach(t => t.stop()); };
  }, []);


  // ── Setup SpeechRecognition (continuous with silence detection) ──
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;       // keep listening
    recognition.interimResults = true;   // show words as user speaks
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      let interimText = '';
      let finalText = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          finalText += result[0].transcript + ' ';
        } else {
          interimText += result[0].transcript;
        }
      }

      // Accumulate final words
      if (finalText) {
        accumulatedRef.current += finalText;
      }

      // Show live preview
      setLiveTranscript(accumulatedRef.current + interimText);

      // Reset silence timer — wait 1.5s after last word before submitting
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = setTimeout(() => {
        const fullAnswer = accumulatedRef.current.trim();
        if (fullAnswer.length > 2) {
          recognition.stop();
          setIsMicOn(false);
          setLiveTranscript('');
          accumulatedRef.current = '';
          handleAnswer(fullAnswer);
        }
      }, 1500); // 1.5 second silence = done speaking
    };

    recognition.onerror = (event) => {
      if (event.error !== 'no-speech') {
        console.error('Speech recognition error', event.error);
      }
      setIsMicOn(false);
    };

    recognition.onend = () => {
      // Auto-restart if mic is still supposed to be on (keeps continuous)
      if (isMicOn) {
        try { recognition.start(); } catch(e) {}
      } else {
        setIsMicOn(false);
      }
    };

    recognitionRef.current = recognition;
  }, [sessionId]);

  // ── Text-to-Speech (AI Voice) ──
  const speak = (text) => {
    if (!text) return;
    synthRef.current.cancel();

    // IMPORTANT: Stop mic when AI is speaking to prevent false triggers
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch(e) {}
    }
    setIsMicOn(false);
    accumulatedRef.current = '';
    setLiveTranscript('');

    const utterance = new SpeechSynthesisUtterance(text);
    
    const voices = synthRef.current.getVoices();
    const preferred = voices.find(v => v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Zira') || v.name.includes('Natural'));
    if (preferred) utterance.voice = preferred;
    
    utterance.rate = 0.95;
    utterance.pitch = 1.05;

    utterance.onstart = () => setIsAITalking(true);
    utterance.onend = () => {
      setIsAITalking(false);
      setAriaWaiting(true);
      // Do NOT auto-start mic — user must press mic button manually
    };
    utterance.onerror = () => {
      setIsAITalking(false);
      setAriaWaiting(true);
    };

    synthRef.current.speak(utterance);
  };

  // Speak first question on load
  useEffect(() => {
    if (!firstQuestion) return;
    const timer = setTimeout(() => {
      speak(firstQuestion);
    }, 1500);
    return () => clearTimeout(timer);
  }, [firstQuestion]);

  // ── Toggle Microphone ──
  const toggleMic = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported. Try Chrome or Edge.');
      return;
    }
    if (isMicOn) {
      // Manual stop — if they pressed stop button, submit whatever was accumulated
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      recognitionRef.current.stop();
      setIsMicOn(false);
      const finalAnswer = accumulatedRef.current.trim();
      if (finalAnswer.length > 2) {
        accumulatedRef.current = '';
        setLiveTranscript('');
        handleAnswer(finalAnswer);
      }
    } else {
      // Start fresh
      accumulatedRef.current = '';
      setLiveTranscript('');
      synthRef.current.cancel();
      setIsAITalking(false);
      try { recognitionRef.current.start(); setIsMicOn(true); }
      catch (e) { console.error('Mic start error:', e); }
    }
  };

  // ── Submit answer to backend ──
  const handleAnswer = async (text) => {
    setMessages(prev => [...prev, { role: 'candidate', text }]);
    setIsThinking(true);
    setAriaWaiting(false);
    try {
      const res = await axios.post(`${API}/submit_answer`, { session_id: sessionId, answer: text });
      const { score, comm_score, feedback, correct_answer, next_question, is_complete, question_number } = res.data;
      setQuestionNum(question_number + 1);
      setLastScore(score);
      setLastCommScore(comm_score ?? score);

      // Add AI feedback message
      setMessages(prev => [...prev, { role: 'aria', text: feedback, score }]);

      // Live score feedback removed from chat as per user request

      if (is_complete || !next_question) {
        setCurrentQuestion('Interview complete! Great job. Redirecting to your results...');
        speak(feedback + ' The interview is now complete. Great job! Let me take you to your results.');
        setIsComplete(true);
        setIsThinking(false);
        setTimeout(() => navigate('/feedback', { state: { sessionId } }), 5000);
      } else {
        // Clear old question and maintain a 1.5s gap with thinking dots
        setCurrentQuestion('');
        
        setTimeout(() => {
          setCurrentQuestion(next_question);
          speak(feedback + '. ' + next_question);
          setIsThinking(false);
        }, 1500);
      }
    } catch (err) {
      console.error('Submit error:', err);
      setMessages(prev => [...prev, { role: 'error', text: 'Connection error. Is the backend running on port 8001?' }]);
      setIsThinking(false);
    }
  };

  // ── End session ──
  const handleEnd = () => {
    synthRef.current.cancel();
    recognitionRef.current?.stop();
    streamRef.current?.getTracks().forEach(t => t.stop());
    navigate('/feedback', { state: { sessionId } });
  };

  return (
    <div className="room-page">
      {/* Header */}
      <header className="room-header">
        <div className="live-badge">
          <span className="live-dot"></span>
          Live Interview — {domain}
        </div>
        <div className="q-progress">
          Question {questionNum} {isComplete ? '✅ Complete' : ''}
        </div>
        <div style={{ fontSize: '0.8rem', color: '#64748B' }}>
          Session: {sessionId?.substring(0, 8)}...
        </div>
      </header>

      {/* Body */}
      <div className="room-body">

        {/* ─── AI Interviewer Panel ─── */}
        <div className={`ai-panel ${isAITalking ? 'talking' : ''}`}>

          {/* Face with canvas mouth */}
          <div className="ai-face-wrapper">
            <img
              src={interviewer.img}
              alt={interviewer.name}
              className="ai-image"
              onError={e => { e.target.src = '/assets/avatar_2.jpg'; }}
            />

            {/* Glow ring when speaking */}
            {isAITalking && <div className="talking-ring"></div>}

            {/* Sound visualizer bars at bottom */}
            {isAITalking && (
              <div className="audio-visualizer">
                <div className="bar"></div>
                <div className="bar"></div>
                <div className="bar"></div>
                <div className="bar"></div>
                <div className="bar"></div>
              </div>
            )}

            {/* Current question overlay */}
            <div className="ai-overlay">
              <div className="ai-name">🎙 AI Interview Session</div>
              {isThinking ? (
                <div className="thinking-dots">
                  <div className="thinking-dot"></div>
                  <div className="thinking-dot"></div>
                  <div className="thinking-dot"></div>
                </div>
              ) : (
                <p className="ai-question">{currentQuestion}</p>
              )}
            </div>
          </div>

          {/* Interviewer info */}
          <div className="interviewer-badge">
            <div className="interviewer-name">{interviewer.name}</div>
            <div className="interviewer-role">{interviewer.role}</div>
            {isAITalking && <div className="speaking-pill">🗣 Speaking...</div>}
            {ariaWaiting && !isAITalking && !isThinking && (
              <div className="waiting-pill">⏳ Waiting for your answer...</div>
            )}
          </div>

          {/* Live grade badge removed as per user request */}
        </div>

        {/* ─── Candidate Panel ─── */}
        <div className="candidate-panel">
          <div className="cam-box">
            <video
              ref={videoRef}
              autoPlay playsInline muted
              onLoadedMetadata={() => videoRef.current?.play().catch(e => console.error("Video play error:", e))}
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: isVideoOn ? 'block' : 'none' }}
            />
            {!isVideoOn && <div className="cam-off">📷</div>}
            <div className="cam-label">You</div>
          </div>

          <div className="transcript-box">
            <div className="transcript-title">Live Transcript</div>
            {messages.length === 0 && (
              <div style={{ color: '#475569', fontSize: '0.82rem', textAlign: 'center', marginTop: '1rem' }}>
                Press 🎙 Mic to speak your answer
              </div>
            )}
            {messages.map((msg, i) => {
              if (msg.role === 'correct') {
                return (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: '0.6rem',
                    background: 'linear-gradient(135deg, rgba(16,185,129,0.2), rgba(16,185,129,0.05))',
                    border: '2px solid rgba(16,185,129,0.6)',
                    borderRadius: '12px',
                    padding: '0.6rem 1.1rem',
                    margin: '0.5rem 0',
                    fontSize: '0.9rem', fontWeight: 800, color: '#10B981',
                    animation: 'fadeInUp 0.3s ease',
                    boxShadow: '0 0 12px rgba(16,185,129,0.25)',
                  }}>
                    <span style={{ fontSize: '1.2rem' }}>✅</span>
                    {msg.text}
                  </div>
                );
              }
              if (msg.role === 'wrong') {
                return (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', gap: '0.6rem',
                    background: 'linear-gradient(135deg, rgba(239,68,68,0.18), rgba(239,68,68,0.05))',
                    border: '2px solid rgba(239,68,68,0.55)',
                    borderRadius: '12px',
                    padding: '0.6rem 1.1rem',
                    margin: '0.5rem 0',
                    fontSize: '0.9rem', fontWeight: 800, color: '#EF4444',
                    animation: 'fadeInUp 0.3s ease',
                    boxShadow: '0 0 12px rgba(239,68,68,0.2)',
                  }}>
                    <span style={{ fontSize: '1.2rem' }}>❌</span>
                    {msg.text}
                  </div>
                );
              }
              return (
                <div key={i} className={`msg ${msg.role === 'candidate' ? 'msg-candidate' : 'msg-aria'}`}>
                  <div className="msg-label">
                    {msg.role === 'candidate' ? '👤 You' : msg.role === 'error' ? '⚠️ Error' : `🤖 ${interviewer.name}`}
                  </div>
                  {msg.text}
                  {msg.score !== undefined && msg.score >= 0 && (
                    <div className="msg-score" style={{ color: getGrade(msg.score).color }}>
                      {getGrade(msg.score).letter} — {msg.score}/100
                    </div>
                  )}
                </div>
              );
            })}
            {/* Live speech preview - shows words as user speaks */}
            {isMicOn && (
              <div style={{
                background: 'rgba(99,102,241,0.08)',
                border: '1px dashed rgba(99,102,241,0.5)',
                borderRadius: '10px',
                padding: '0.65rem 1rem',
                margin: '0.5rem 0',
              }}>
                <div style={{ fontSize: '0.7rem', color: '#818CF8', fontWeight: 700, marginBottom: '0.3rem' }}>
                  🔴 Listening... (auto-submits after 1.5s silence)
                </div>
                <div style={{ color: '#c7d2fe', fontSize: '0.87rem', lineHeight: 1.5, minHeight: '1.2rem' }}>
                  {liveTranscript || <em style={{ color: '#4B5563' }}>Speak now...</em>}
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      {/* Controls */}
      <footer className="room-controls">
        <div style={{ textAlign: 'center' }}>
          <button
            className={`ctrl-btn ${isMicOn ? 'mic-on' : 'mic-off'}`}
            onClick={toggleMic}
            disabled={isThinking || isComplete}
            title={isMicOn ? 'Stop Listening' : 'Click to Speak'}
          >
            {isMicOn ? '🎙' : '🎤'}
          </button>
          <div className="ctrl-hint">{isMicOn ? 'Listening...' : 'Click to Speak'}</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <button className="ctrl-btn vid" onClick={() => setIsVideoOn(v => !v)} title="Toggle Camera">
            {isVideoOn ? '📷' : '📵'}
          </button>
          <div className="ctrl-hint">{isVideoOn ? 'Camera On' : 'Camera Off'}</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <button className="ctrl-btn end" onClick={handleEnd} title="End Interview">📵</button>
          <div className="ctrl-hint">End Session</div>
        </div>
      </footer>
    </div>
  );
}
