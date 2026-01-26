import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './pages/HomePage';
import QuestionsPage from './pages/QuestionsPage';
import ResultsPage from './pages/ResultsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/cycles/:cycleId/questions" element={<QuestionsPage />} />
        <Route path="/cycles/:cycleId/results" element={<ResultsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
