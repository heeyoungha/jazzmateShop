import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Loader2, Music, Star, Heart, Save, ArrowLeft } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useNavigate } from 'react-router-dom';

interface Album {
  id: number;
  album_artist: string;
  album_title: string;
  album_year: number;
}

const WriteReviewPage: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // 폼 데이터
  const [formData, setFormData] = useState({
    albumId: '',
    trackName: '',
    reviewContent: '',
    rating: '',
    mood: '',
    genre: '',
    energyLevel: '',
    bpm: '',
    vocalStyle: '',
    instrumentation: '',
    tags: '',
    isPublic: true
  });

  // 앨범 검색 관련 상태 (주석처리)
  // const [searchQuery, setSearchQuery] = useState('');
  // const [searchResults, setSearchResults] = useState<Album[]>([]);
  // const [isSearching, setIsSearching] = useState(false);
  // const [selectedAlbum, setSelectedAlbum] = useState<Album | null>(null);

  // 직접 입력 필드
  const [trackInfo, setTrackInfo] = useState({
    trackName: '',
    artistName: ''
  });

  // 앨범 검색 함수 (주석처리)
  // const searchAlbums = async () => {
  //   if (!searchQuery.trim()) return;
  //   
  //   setIsSearching(true);
  //   try {
  //     const response = await fetch(`/api/albums/search?q=${encodeURIComponent(searchQuery)}`);
  //     if (response.ok) {
  //       const albums = await response.json();
  //       setSearchResults(albums);
  //     }
  //   } catch (err) {
  //     console.error('앨범 검색 오류:', err);
  //   } finally {
  //     setIsSearching(false);
  //   }
  // };

  // 감상문 제출 함수
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!trackInfo.trackName.trim() || !trackInfo.artistName.trim() || !formData.reviewContent.trim()) {
      setError('트랙명, 아티스트명, 감상문을 모두 입력해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch('/api/user-reviews', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          album_id: null, // 직접 입력 모드에서는 album_id 없음
          track_name: trackInfo.trackName,
          artist_name: trackInfo.artistName,
          review_content: formData.reviewContent,
          rating: formData.rating ? parseFloat(formData.rating) : null,
          mood: formData.mood || null,
          genre: formData.genre || null,
          energy_level: formData.energyLevel ? parseFloat(formData.energyLevel) : null,
          bpm: formData.bpm ? parseInt(formData.bpm) : null,
          vocal_style: formData.vocalStyle || null,
          instrumentation: formData.instrumentation || null,
          tags: formData.tags ? formData.tags.split(',').map(tag => tag.trim()) : [],
          is_public: formData.isPublic
        }),
      });

      if (response.ok) {
        setSuccess('감상문이 성공적으로 저장되었습니다!');
        // 폼 초기화
        setFormData({
          albumId: '',
          trackName: '',
          reviewContent: '',
          rating: '',
          mood: '',
          genre: '',
          energyLevel: '',
          bpm: '',
          vocalStyle: '',
          instrumentation: '',
          tags: '',
          isPublic: true
        });
        setTrackInfo({
          trackName: '',
          artistName: ''
        });
      } else {
        const errorData = await response.json();
        setError(errorData.message || '감상문 저장에 실패했습니다.');
      }
    } catch (err) {
      setError('서버 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
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
          🎵 나만의 감상문 작성
        </h1>
        <p className="text-lg text-gray-600">
          좋아하는 재즈 곡에 대한 감상을 기록하고 공유해보세요
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 트랙 정보 입력 섹션 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Music className="h-5 w-5" />
              트랙 정보 입력
            </CardTitle>
            <CardDescription>
              감상하고 싶은 곡의 정보를 직접 입력해주세요
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="trackName">트랙명 *</Label>
                <Input
                  id="trackName"
                  placeholder="예: Blue in Green"
                  value={trackInfo.trackName}
                  onChange={(e) => setTrackInfo(prev => ({ ...prev, trackName: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label htmlFor="artistName">아티스트명 *</Label>
                <Input
                  id="artistName"
                  placeholder="예: Miles Davis"
                  value={trackInfo.artistName}
                  onChange={(e) => setTrackInfo(prev => ({ ...prev, artistName: e.target.value }))}
                  required
                />
              </div>
            </div>

            {/* 입력된 정보 표시 */}
            {trackInfo.trackName && trackInfo.artistName && (
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center gap-2">
                  <Heart className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="font-semibold text-green-800">{trackInfo.trackName}</p>
                    <p className="text-sm text-green-600">{trackInfo.artistName}</p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 감상문 작성 섹션 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Star className="h-5 w-5" />
              감상문 작성
            </CardTitle>
            <CardDescription>
              음악에 대한 느낌과 생각을 자유롭게 작성해주세요
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="reviewContent">감상문 *</Label>
              <Textarea
                id="reviewContent"
                placeholder="이 곡을 들으며 느낀 감정, 생각, 추억 등을 자유롭게 작성해주세요..."
                value={formData.reviewContent}
                onChange={(e) => handleInputChange('reviewContent', e.target.value)}
                className="min-h-[200px]"
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="rating">평점 (0-5점)</Label>
                <Select value={formData.rating} onValueChange={(value) => handleInputChange('rating', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="평점을 선택하세요" />
                  </SelectTrigger>
                  <SelectContent>
                    {[5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1, 0.5, 0].map(score => (
                      <SelectItem key={score} value={score.toString()}>
                        {score}점
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="mood">무드</Label>
                <Select value={formData.mood} onValueChange={(value) => handleInputChange('mood', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="무드를 선택하세요" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="happy">Happy</SelectItem>
                    <SelectItem value="sad">Sad</SelectItem>
                    <SelectItem value="energetic">Energetic</SelectItem>
                    <SelectItem value="calm">Calm</SelectItem>
                    <SelectItem value="melancholic">Melancholic</SelectItem>
                    <SelectItem value="romantic">Romantic</SelectItem>
                    <SelectItem value="nostalgic">Nostalgic</SelectItem>
                    <SelectItem value="dramatic">Dramatic</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="genre">장르</Label>
                <Select value={formData.genre} onValueChange={(value) => handleInputChange('genre', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="장르를 선택하세요" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="jazz">Jazz</SelectItem>
                    <SelectItem value="blues">Blues</SelectItem>
                    <SelectItem value="soul">Soul</SelectItem>
                    <SelectItem value="funk">Funk</SelectItem>
                    <SelectItem value="bebop">Bebop</SelectItem>
                    <SelectItem value="fusion">Fusion</SelectItem>
                    <SelectItem value="swing">Swing</SelectItem>
                    <SelectItem value="cool">Cool Jazz</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="vocalStyle">발성 스타일</Label>
                <Select value={formData.vocalStyle} onValueChange={(value) => handleInputChange('vocalStyle', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="발성 스타일을 선택하세요" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="instrumental">Instrumental</SelectItem>
                    <SelectItem value="scat">Scat</SelectItem>
                    <SelectItem value="crooning">Crooning</SelectItem>
                    <SelectItem value="belting">Belting</SelectItem>
                    <SelectItem value="whisper">Whisper</SelectItem>
                    <SelectItem value="vocal">Vocal</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="energyLevel">에너지 레벨 (0-1)</Label>
                <Select value={formData.energyLevel} onValueChange={(value) => handleInputChange('energyLevel', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="에너지 레벨을 선택하세요" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0.0">0.0 (매우 차분)</SelectItem>
                    <SelectItem value="0.2">0.2 (차분)</SelectItem>
                    <SelectItem value="0.4">0.4 (보통)</SelectItem>
                    <SelectItem value="0.6">0.6 (활기참)</SelectItem>
                    <SelectItem value="0.8">0.8 (역동적)</SelectItem>
                    <SelectItem value="1.0">1.0 (매우 역동적)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="bpm">BPM</Label>
                <Input
                  id="bpm"
                  type="number"
                  placeholder="예: 120"
                  value={formData.bpm}
                  onChange={(e) => handleInputChange('bpm', e.target.value)}
                />
              </div>
            </div>

            <div>
              <Label htmlFor="instrumentation">악기 구성</Label>
              <Input
                id="instrumentation"
                placeholder="예: piano, saxophone, drums, bass"
                value={formData.instrumentation}
                onChange={(e) => handleInputChange('instrumentation', e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="tags">태그 (쉼표로 구분)</Label>
              <Input
                id="tags"
                placeholder="예: 재즈, 피아노, 감성적, 클래식"
                value={formData.tags}
                onChange={(e) => handleInputChange('tags', e.target.value)}
              />
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="isPublic"
                checked={formData.isPublic}
                onChange={(e) => handleInputChange('isPublic', e.target.checked.toString())}
                className="rounded"
              />
              <Label htmlFor="isPublic">다른 사용자들과 공유하기</Label>
            </div>
          </CardContent>
        </Card>

        {/* 에러 및 성공 메시지 */}
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {success && (
          <Alert className="border-green-200 bg-green-50">
            <AlertDescription className="text-green-800">{success}</AlertDescription>
          </Alert>
        )}

        {/* 제출 버튼 */}
        <div className="flex justify-end">
          <Button 
            type="submit" 
            disabled={isLoading || !trackInfo.trackName.trim() || !trackInfo.artistName.trim() || !formData.reviewContent.trim()}
            size="lg"
            className="px-8"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                저장 중...
              </>
            ) : (
              <>
                <Save className="mr-2 h-5 w-5" />
                감상문 저장하기
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default WriteReviewPage;
