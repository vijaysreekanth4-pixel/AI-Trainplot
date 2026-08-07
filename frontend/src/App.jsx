import { BrowserRouter, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import InterviewSetup from './pages/InterviewSetup';
import InterviewRoom from './pages/InterviewRoom';
import FeedbackDashboard from './pages/FeedbackDashboard';

function App() {
  return (
    <BrowserRouter>
      <>
        <div className="stars-container">
          <div className="stars"></div>
          <div className="stars2"></div>
          <div className="stars3"></div>
        </div>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/setup" element={<InterviewSetup />} />
          <Route path="/interview" element={<InterviewRoom />} />
          <Route path="/feedback" element={<FeedbackDashboard />} />
        </Routes>
      </>
    </BrowserRouter>
  );
}

export default App;
