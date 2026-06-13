import { BrowserRouter, Route, Routes } from "react-router-dom";
import { CriticsReviewDetailPage } from "./pages/CriticsReviewDetailPage";
import { CriticsReviewPage } from "./pages/CriticsReviewPage";
import { MainPage } from "./pages/MainPage";
import { MyReviewsPage } from "./pages/MyReviewsPage";
import { ReviewBasedRecommendPage } from "./pages/ReviewBasedRecommendPage";
import { WriteReviewPage } from "./pages/WriteReviewPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/write" element={<WriteReviewPage />} />
        <Route path="/recommend" element={<MyReviewsPage />} />
        <Route path="/recommend/:id" element={<ReviewBasedRecommendPage />} />
        <Route path="/critics" element={<CriticsReviewPage />} />
        <Route path="/critics/:id" element={<CriticsReviewDetailPage />} />
      </Routes>
    </BrowserRouter>
  );
}
