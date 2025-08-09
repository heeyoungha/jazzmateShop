import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainPage from './pages/MainPage';
import CriticsReviewPage from './pages/CriticsReviewPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/critics" element={<CriticsReviewPage />} />
      </Routes>
    </Router>
  );
}

export default App;