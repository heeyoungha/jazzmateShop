import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainPage from './pages/MainPage';
import CriticsReviewPage from './pages/CriticsReviewPage';
import ReviewRecommendPage from './pages/ReviewRecommendPage';
import WriteReviewPage from './pages/WriteReviewPage';
import MyReviewsPage from './pages/MyReviewsPage';
import ReviewBasedRecommendPage from './pages/ReviewBasedRecommendPage';
import AdminPage from './pages/AdminPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/critics" element={<CriticsReviewPage />} />
        <Route path="/recommend" element={<MyReviewsPage />} />
        <Route path="/recommend/:reviewId" element={<ReviewBasedRecommendPage />} />
        <Route path="/write-review" element={<WriteReviewPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </Router>
  );
}

export default App;