import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChevronLeft, Calendar, User } from 'lucide-react';

interface CriticsReview {
  id: number;
  title: string;
  reviewer: string;
  date: string;
  content: string;
  reviewSummary: string;
  url: string;
  createdAt: string;
}

interface ReviewPageData {
  content: CriticsReview[];
  totalElements: number;
  totalPages: number;
  size: number;
  number: number;
  first: boolean;
  last: boolean;
}

// reviewSummary 파싱 함수 
const parseReviewSummary = (summaryString: string) => {
    // 빈 문자열이나 null 체크
    if (!summaryString || summaryString.trim() === '') {
      return null; // null 반환으로 렌더링하지 않음
    }
  
    try {
      // JSON 형태인지 확인
      const trimmed = summaryString.trim();
      if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
        const parsed = JSON.parse(summaryString);
        return {
          summary: parsed.summary?.korean || '',
          artistInfo: parsed.categories?.artist_info?.korean || '',
          albumInfo: parsed.categories?.album_info?.korean || '',
          trackInfo: parsed.categories?.track_info || {},
          performanceNote: parsed.categories?.performance_note?.korean || '',
          culturalContext: parsed.categories?.cultural_context?.korean || '',
          instrumentation: parsed.categories?.instrumentation?.korean || '',
          compositionInfluence: parsed.categories?.composition_influence?.korean || '',
          reviewerOpinion: parsed.categories?.reviewer_opinion?.korean || ''
        };
      } else {
        // JSON이 아닌 경우 null 반환
        return null;
      }
    } catch (error) {
      // JSON 파싱 실패시 null 반환 (에러 로그 제거)
      return null;
    }
  };

const CriticsReviewPage: React.FC = () => {
  const [reviews, setReviews] = useState<CriticsReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  const fetchReviews = async (pageNum: number = 0) => {
    try {
      setLoading(true);
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';
      const response = await fetch(`${API_BASE_URL}/api/critics?page=${pageNum}&size=10`);
      const data: ReviewPageData = await response.json();
      
      if (pageNum === 0) {
        setReviews(data.content);
      } else {
        setReviews(prev => [...prev, ...data.content]);
      }
      
      setTotalPages(data.totalPages);
      setHasMore(!data.last);
    } catch (error) {
      console.error('리뷰를 불러오는데 실패했습니다:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReviews(0);
  }, []);

  const loadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchReviews(nextPage);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center gap-4">
            <Button 
              variant="ghost" 
              size="sm"
              onClick={() => window.history.back()}
              className="flex items-center gap-2"
            >
              <ChevronLeft className="w-4 h-4" />
              뒤로가기
            </Button>
            <h1 className="text-2xl font-bold text-gray-900">전문가 리뷰</h1>
          </div>
        </div>
      </div>

      {/* 메인 콘텐츠 */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {loading && reviews.length === 0 ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <div className="space-y-6">
            {reviews.map((review) => {
            const summaryData = parseReviewSummary(review.reviewSummary);
            if (!summaryData) {
                return (
                  <Card key={review.id} className="hover:shadow-lg transition-shadow">
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <CardTitle className="text-xl font-semibold text-gray-900 mb-2">
                            {review.title}
                          </CardTitle>
                          <div className="flex items-center gap-4 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                              <User className="w-4 h-4" />
                              {review.reviewer}
                            </div>
                            <div className="flex items-center gap-1">
                              <Calendar className="w-4 h-4" />
                              {formatDate(review.date)}
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {/* 원본 리뷰 내용만 표시 */}
                      <div className="mb-4">
                        <h4 className="font-medium text-gray-900 mb-2">📖 리뷰 내용</h4>
                        <p className="text-gray-700 leading-relaxed">{review.content}</p>
                      </div>
            
                      {review.url && (
                        <div className="pt-4 border-t">
                          <a 
                            href={review.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 font-medium"
                          >
                            원문 보기 →
                          </a>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              }
                return (
                    <Card key={review.id} className="hover:shadow-lg transition-shadow">
                    <CardHeader>
                        <div className="flex items-start justify-between">
                        <div className="flex-1">
                            <CardTitle className="text-xl font-semibold text-gray-900 mb-2">
                            {review.title}
                            </CardTitle>
                            <div className="flex items-center gap-4 text-sm text-gray-600">
                            <div className="flex items-center gap-1">
                                <User className="w-4 h-4" />
                                {review.reviewer}
                            </div>
                            <div className="flex items-center gap-1">
                                <Calendar className="w-4 h-4" />
                                {formatDate(review.date)}
                            </div>
                            </div>
                        </div>
                        </div>
                    </CardHeader>
                    <CardContent>
                        {/* 요약 섹션 */}
                        {summaryData && summaryData.summary && (
                        <div className="mb-6">
                            <h4 className="font-semibold text-gray-900 mb-3 text-lg">📝 요약</h4>
                            <p className="text-gray-700 bg-blue-50 p-4 rounded-lg leading-relaxed">
                            {summaryData.summary}
                            </p>
                        </div>
                        )}

                        {/* 아티스트 정보 */}
                        {summaryData && summaryData.artistInfo && (
                        <div className="mb-4">
                            <h4 className="font-medium text-gray-900 mb-2">🎵 아티스트 정보</h4>
                            <p className="text-gray-700 text-sm leading-relaxed">{summaryData.artistInfo}</p>
                        </div>
                        )}

                        {/* 앨범 정보 */}
                        {summaryData && summaryData.albumInfo && (
                        <div className="mb-4">
                            <h4 className="font-medium text-gray-900 mb-2">💿 앨범 정보</h4>
                            <p className="text-gray-700 text-sm leading-relaxed">{summaryData.albumInfo}</p>
                        </div>
                        )}

                        {/* 트랙 정보 */}
                        {summaryData && summaryData.trackInfo && 
                        typeof summaryData.trackInfo === 'object' && 
                        Object.keys(summaryData.trackInfo).length > 0 && (
                        <div className="mb-4">
                            <h4 className="font-medium text-gray-900 mb-2">🎼 트랙 정보</h4>
                            <div className="space-y-2">
                            {Object.entries(summaryData.trackInfo).map(([trackName, trackData]: [string, any]) => (
                                <div key={trackName} className="bg-gray-50 p-3 rounded-lg">
                                <h5 className="font-medium text-gray-800 mb-1">• {trackName}</h5>
                                <p className="text-gray-700 text-sm">
                                    {typeof trackData === 'object' ? trackData?.korean || '' : trackData}
                                </p>
                                </div>
                            ))}
                            </div>
                        </div>
                        )}

                        {/* 연주 노트 */}
                        {summaryData && summaryData.performanceNote && (
                        <div className="mb-4">
                            <h4 className="font-medium text-gray-900 mb-2">🎺 연주 노트</h4>
                            <p className="text-gray-700 text-sm leading-relaxed">{summaryData.performanceNote}</p>
                        </div>
                        )}

                        {/* 문화적 맥락 */}
                        {summaryData && summaryData.culturalContext && (
                        <div className="mb-4">
                            <h4 className="font-medium text-gray-900 mb-2">🌍 문화적 맥락</h4>
                            <p className="text-gray-700 text-sm leading-relaxed">{summaryData.culturalContext}</p>
                        </div>
                        )}

                        {/* 악기 구성 */}
                        {summaryData && summaryData.instrumentation && (
                        <div className="mb-4">
                            <h4 className="font-medium text-gray-900 mb-2">🎷 악기 구성</h4>
                            <p className="text-gray-700 text-sm leading-relaxed">{summaryData.instrumentation}</p>
                        </div>
                        )}

                        {/* 작곡 영향 */}
                        {summaryData && summaryData.compositionInfluence && (
                        <div className="mb-4">
                            <h4 className="font-medium text-gray-900 mb-2">🎵 작곡 영향</h4>
                            <p className="text-gray-700 text-sm leading-relaxed">{summaryData.compositionInfluence}</p>
                        </div>
                        )}

                        {/* 평론가 의견 */}
                        {summaryData && summaryData.reviewerOpinion && (
                        <div className="mb-4">
                            <h4 className="font-medium text-gray-900 mb-2">⭐ 평론가 의견</h4>
                            <p className="text-gray-700 text-sm leading-relaxed bg-yellow-50 p-3 rounded-lg">
                            {summaryData.reviewerOpinion}
                            </p>
                        </div>
                        )}

                        {review.url && (
                        <div className="pt-4 border-t">
                            <a 
                            href={review.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 font-medium"
                            >
                            원문 보기 →
                            </a>
                        </div>
                        )}
                    </CardContent>
                    </Card>
                );            
            })}

            {/* 무한 스크롤 로드 더 보기 버튼 */}
            {hasMore && (
              <div className="flex justify-center py-8">
                <Button 
                  onClick={loadMore}
                  disabled={loading}
                  className="px-8 py-2"
                >
                  {loading ? '로딩 중...' : '더 보기'}
                </Button>
              </div>
            )}

            {!hasMore && reviews.length > 0 && (
              <div className="text-center py-8 text-gray-500">
                모든 리뷰를 불러왔습니다.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CriticsReviewPage;