import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, Music, Star, ArrowLeft, Heart } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface UserReview {
  id: number;
  trackName: string;
  artistName: string;
  reviewContent: string;
  rating: number;
  mood: string;
  genre: string;
  createdAt: string;
}

const MyReviewsPage: React.FC = () => {
  const navigate = useNavigate();
  const [reviews, setReviews] = useState<UserReview[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchUserReviews();
  }, []);

  const fetchUserReviews = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('/api/user-reviews');
      
      if (response.ok) {
        const data = await response.json();
        setReviews(data);
      } else {
        setError('감상문 목록을 불러오는데 실패했습니다.');
      }
    } catch (err) {
      setError('서버 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };


  const handleReviewClick = (reviewId: number) => {
    navigate(`/recommend/${reviewId}`);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR');
  };

  const getMoodColor = (mood: string) => {
    const moodColors: { [key: string]: string } = {
      'melancholic': 'bg-blue-100 text-blue-800',
      'energetic': 'bg-red-100 text-red-800',
      'peaceful': 'bg-green-100 text-green-800',
      'romantic': 'bg-pink-100 text-pink-800',
      'nostalgic': 'bg-purple-100 text-purple-800',
      'dramatic': 'bg-orange-100 text-orange-800',
    };
    return moodColors[mood] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-6">
        <Button 
          variant="outline" 
          onClick={() => navigate('/')}
          className="mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          홈으로 돌아가기
        </Button>
        
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          🎵 AI 맞춤 추천
        </h1>
        <p className="text-lg text-gray-600">
          기존 감상문을 클릭하여 곡을 추천받으세요
        </p>
      </div>

      {/* 기존 감상문 목록 */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          내가 작성한 감상문
        </h2>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">감상문 목록을 불러오는 중...</span>
        </div>
      ) : error ? (
        <Card>
          <CardContent className="text-center py-8">
            <p className="text-red-600">{error}</p>
          </CardContent>
        </Card>
      ) : reviews.length === 0 ? (
        <Card>
              <CardContent className="text-center py-8">
                <Music className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 mb-4">아직 작성된 감상문이 없습니다.</p>
                <p className="text-sm text-gray-400">먼저 감상문을 작성해주세요!</p>
              </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {reviews.map((review) => (
            <Card 
              key={review.id}
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => handleReviewClick(review.id)}
            >
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg">{review.trackName}</CardTitle>
                    <CardDescription className="text-base">{review.artistName}</CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    {review.rating && (
                      <div className="flex items-center gap-1">
                        <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                        <span className="text-sm font-medium">{review.rating}</span>
                      </div>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-gray-700 mb-4 line-clamp-3">
                  {review.reviewContent}
                </p>
                <div className="flex items-center justify-between">
                  <div className="flex gap-2">
                    {review.mood && (
                      <Badge className={getMoodColor(review.mood)}>
                        {review.mood}
                      </Badge>
                    )}
                    {review.genre && (
                      <Badge variant="outline">
                        {review.genre}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Heart className="h-4 w-4" />
                    <span>{formatDate(review.createdAt)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyReviewsPage;
