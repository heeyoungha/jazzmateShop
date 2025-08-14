import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, Music, Star, ArrowLeft, Heart, Play } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';

interface Recommendation {
  pointId: string;
  score: number;
  payload: {
    albumArtist: string;
    albumTitle: string;
    genre: string;
    mood: string;
    vocalStyle: string;
    instrumentation: string;
    energy: number;
    bpm: number;
  };
  reason: string;
}

interface UserReview {
  id: number;
  trackName: string;
  artistName: string;
  reviewContent: string;
  rating: number;
  mood: string;
  genre: string;
  energyLevel: number;
  bpm: number;
  vocalStyle: string;
  instrumentation: string;
}

const ReviewBasedRecommendPage: React.FC = () => {
  const navigate = useNavigate();
  const { reviewId } = useParams<{ reviewId: string }>();
  const [review, setReview] = useState<UserReview | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (reviewId) {
      fetchReviewAndRecommendations();
    }
  }, [reviewId]);

  const generateNewRecommendations = async (reviewContent: string, reviewId: string) => {
    try {
      console.log('추천 결과가 없습니다. 잠시 후 다시 시도해주세요.');
      setError('추천 결과가 아직 생성되지 않았습니다. 잠시 후 다시 시도해주세요.');
    } catch (err) {
      console.error('추천 생성 오류:', err);
      setError('추천 생성 중 오류가 발생했습니다.');
    }
  };

  const fetchReviewAndRecommendations = async () => {
    try {
      setIsLoading(true);
      
      // 감상문과 추천 결과를 한 번에 가져오기
      const response = await fetch(`http://localhost:8080/api/user-reviews/${reviewId}`);
      if (!response.ok) {
        throw new Error('감상문을 찾을 수 없습니다.');
      }
      
      const data = await response.json();
      setReview(data);
      
      // 추천 결과가 있으면 표시
      if (data.hasRecommendations && data.recommendations.length > 0) {
        const formattedRecommendations = await Promise.all(
          data.recommendations.map(async (rec: any) => {
            // Track 정보 조회
            const trackResponse = await fetch(`http://localhost:8080/api/tracks/${rec.trackId}`);
            const trackData = trackResponse.ok ? await trackResponse.json() : null;
            
            return {
              pointId: rec.trackId,
              score: rec.recommendationScore,
              payload: {
                albumArtist: trackData?.artistName || 'Unknown Artist',
                albumTitle: trackData?.trackTitle || 'Unknown Album',
                genre: trackData?.genre || 'jazz',
                mood: trackData?.mood || 'melancholic',
                vocalStyle: trackData?.vocalStyle || 'instrumental',
                instrumentation: trackData?.instrumentation || 'N/A',
                energy: trackData?.energy || 0.5,
                bpm: trackData?.bpm || 120
              },
              reason: rec.recommendationReason
            };
          })
        );
        setRecommendations(formattedRecommendations);
      } else {
        // 추천 결과가 없으면 로딩 상태 유지
        console.log('추천 결과가 아직 생성되지 않았습니다.');
        setRecommendations([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatScore = (score: number) => {
    return (score * 100).toFixed(1);
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

  const getGenreColor = (genre: string) => {
    const genreColors: { [key: string]: string } = {
      'jazz': 'bg-yellow-100 text-yellow-800',
      'blues': 'bg-indigo-100 text-indigo-800',
      'soul': 'bg-purple-100 text-purple-800',
      'funk': 'bg-green-100 text-green-800',
      'bebop': 'bg-red-100 text-red-800',
      'fusion': 'bg-blue-100 text-blue-800',
    };
    return genreColors[genre] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-6">
        <Button 
          variant="outline" 
          onClick={() => navigate('/recommend')}
          className="mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          추천 목록으로 돌아가기
        </Button>
        
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          🎵 AI 맞춤 추천 결과
        </h1>
        <p className="text-lg text-gray-600">
          감상문을 분석하여 추천된 곡들입니다
        </p>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">추천 결과를 불러오는 중...</span>
        </div>
      ) : error ? (
        <Card>
          <CardContent className="text-center py-8">
            <p className="text-red-600">{error}</p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* 감상문 정보 */}
          {review && (
            <Card className="mb-8">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Music className="h-5 w-5" />
                  기준 감상문
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <h3 className="text-xl font-semibold">{review.trackName}</h3>
                  <p className="text-gray-600">{review.artistName}</p>
                </div>
                <p className="text-gray-700 mb-4">{review.reviewContent}</p>
                <div className="flex gap-2">
                  {review.mood && (
                    <Badge className={getMoodColor(review.mood)}>
                      {review.mood}
                    </Badge>
                  )}
                  {review.genre && (
                    <Badge className={getGenreColor(review.genre)}>
                      {review.genre}
                    </Badge>
                  )}
                  {review.rating && (
                    <Badge variant="outline">
                      <Star className="h-3 w-3 mr-1" />
                      {review.rating}
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 추천 결과 */}
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-900">
              추천 곡 목록 ({recommendations.length}개)
            </h2>
            
            {recommendations.length === 0 ? (
              <Card>
                <CardContent className="text-center py-8">
                  <Music className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500 mb-2">추천 결과가 아직 생성되지 않았습니다.</p>
                  <p className="text-sm text-gray-400">감상문 작성 후 잠시 기다려주세요.</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {recommendations.map((rec, index) => (
                  <Card key={rec.pointId} className="hover:shadow-lg transition-shadow">
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <CardTitle className="text-lg mb-1">
                            {rec.payload.albumTitle}
                          </CardTitle>
                          <CardDescription className="text-base">
                            {rec.payload.albumArtist}
                          </CardDescription>
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-gray-500">추천 점수</div>
                          <div className="text-lg font-bold text-blue-600">
                            {formatScore(rec.score)}%
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2 mb-4">
                        <Badge className={getGenreColor(rec.payload.genre)}>
                          {rec.payload.genre}
                        </Badge>
                        <Badge className={getMoodColor(rec.payload.mood)}>
                          {rec.payload.mood}
                        </Badge>
                        {rec.payload.vocalStyle && rec.payload.vocalStyle !== 'N/A' && (
                          <Badge variant="outline">
                            {rec.payload.vocalStyle}
                          </Badge>
                        )}
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-500">에너지:</span>
                          <span className="ml-1 font-medium">
                            {(rec.payload.energy * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500">BPM:</span>
                          <span className="ml-1 font-medium">{rec.payload.bpm}</span>
                        </div>
                        <div className="col-span-2">
                          <span className="text-gray-500">악기 구성:</span>
                          <span className="ml-1 font-medium">
                            {rec.payload.instrumentation || 'N/A'}
                          </span>
                        </div>
                      </div>
                      
                          {/* 추천 사유 */}
                          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                            <div className="text-sm font-medium text-blue-800 mb-2">
                              💡 추천 사유
                            </div>
                            <p className="text-sm text-blue-700 leading-relaxed">
                              {rec.reason}
                            </p>
                          </div>
                          
                          {/* 재생 버튼 주석처리 */}
                          {/* <div className="mt-4 flex gap-2">
                            <Button size="sm" className="flex-1">
                              <Play className="mr-2 h-4 w-4" />
                              재생
                            </Button>
                            <Button size="sm" variant="outline">
                              <Heart className="h-4 w-4" />
                            </Button>
                          </div> */}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default ReviewBasedRecommendPage;
