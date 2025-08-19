import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Loader2, Music, Star, User } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { getApiUrl } from '@/lib/api';

interface Recommendation {
  point_id: string;
  score: number;
  payload: {
    album_artist: string;
    album_title: string;
    genre: string;
    mood: string;
    vocal_style: string;
    instrumentation: string;
    energy: number;
    bpm: number;
  };
}

const ReviewRecommendPage: React.FC = () => {
  const [reviewText, setReviewText] = useState('');
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmitReview = async () => {
    if (!reviewText.trim()) {
      setError('감상문을 작성해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setRecommendations([]);

    try {
      const apiUrl = getApiUrl();
      const response = await fetch(`${apiUrl}/recommend/by-review`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          review_text: reviewText.trim(),
          limit: 10
        }),
      });

      if (!response.ok) {
        throw new Error('추천 요청에 실패했습니다.');
      }

      const data = await response.json();
      setRecommendations(data.recommendations || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : '추천 시스템 오류가 발생했습니다.');
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
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          🎵 JazzMate 추천 시스템
        </h1>
        <p className="text-lg text-gray-600">
          감상문을 작성하면 당신의 취향에 맞는 재즈 곡을 추천해드립니다
        </p>
      </div>

      {/* 감상문 작성 섹션 */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            감상문 작성
          </CardTitle>
          <CardDescription>
            들었던 음악에 대한 감상이나 원하는 음악의 느낌을 자유롭게 작성해주세요.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="예: 오늘은 조용한 재즈가 듣고 싶어요. 피아노와 색소폰이 어우러진 멜랑콜릭한 느낌의 곡을 찾고 있습니다..."
            value={reviewText}
            onChange={(e) => setReviewText(e.target.value)}
            className="min-h-[120px] mb-4"
          />
          <Button 
            onClick={handleSubmitReview}
            disabled={isLoading || !reviewText.trim()}
            className="w-full"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                추천 중...
              </>
            ) : (
              <>
                <Music className="mr-2 h-4 w-4" />
                곡 추천받기
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* 에러 메시지 */}
      {error && (
        <Alert className="mb-6" variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* 추천 결과 섹션 */}
      {recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Star className="h-5 w-5" />
              추천 곡 목록
            </CardTitle>
            <CardDescription>
              당신의 감상문을 바탕으로 추천된 {recommendations.length}개의 곡입니다.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {recommendations.map((rec, index) => (
                <div key={rec.point_id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 mb-1">
                        {rec.payload.album_title}
                      </h3>
                      <p className="text-gray-600 mb-2">
                        {rec.payload.album_artist}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-gray-500">추천 점수</div>
                      <div className="text-lg font-bold text-blue-600">
                        {formatScore(rec.score)}%
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 mb-3">
                    <Badge className={getGenreColor(rec.payload.genre)}>
                      {rec.payload.genre}
                    </Badge>
                    <Badge className={getMoodColor(rec.payload.mood)}>
                      {rec.payload.mood}
                    </Badge>
                    {rec.payload.vocal_style && rec.payload.vocal_style !== 'N/A' && (
                      <Badge variant="outline">
                        {rec.payload.vocal_style}
                      </Badge>
                    )}
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
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
                    <div className="md:col-span-2">
                      <span className="text-gray-500">악기 구성:</span>
                      <span className="ml-1 font-medium">
                        {rec.payload.instrumentation || 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 추천 결과가 없을 때 */}
      {!isLoading && recommendations.length === 0 && reviewText && (
        <Card>
          <CardContent className="text-center py-8">
            <Music className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500">
              아직 추천 결과가 없습니다. 감상문을 작성하고 추천받기를 눌러보세요.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ReviewRecommendPage;


