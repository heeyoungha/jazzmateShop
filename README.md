# 🎷 JazzMate

재즈 음악 감상문 작성 및 AI 기반 맞춤형 음악 추천 플랫폼

## 📖 프로젝트 소개

JazzmateShop은 재즈 입문자들을 위한 종합 플랫폼입니다. 사용자가 좋아하는 재즈 곡에 대한 감상문을 작성하고, AI 기술을 활용하여 개인의 취향과 감상 패턴을 분석해 맞춤형 음악을 추천합니다. 벡터 임베딩과 대규모 언어 모델을 결합하여 의미 기반 음악 추천 시스템을 구현했습니다.

## ✨ 주요 기능

### 1. 감상문 작성 및 관리
- 상세한 재즈 곡 감상문 작성 (트랙명, 아티스트, 감상 내용 등)
- 장르, 무드, 에너지 레벨, BPM, 보컬 스타일 등 메타데이터 기록
- 작성한 감상문 목록 조회 및 관리
- 공개/비공개 설정 기능

### 2. AI 기반 맞춤형 추천
- **벡터 임베딩 기반 유사도 검색**: 감상문 텍스트를 임베딩으로 변환하여 유사한 곡 검색
- **LLM 기반 추천 사유 생성**: GPT-3.5를 활용하여 각 추천 곡에 대한 상세한 추천 이유 제공
- **실시간 추천**: 감상문 작성 직후 비동기로 추천 생성
- **추천 정확도 향상**: 평론가 리뷰 데이터를 활용한 고품질 벡터 DB 구축

### 3. 평론가 리뷰 조회
- 전문 평론가들의 최신 앨범 리뷰 확인
- 클래식 재해석부터 새로운 발견까지 다양한 시각 제공

### 4. 데이터 품질 모니터링
- 데이터베이스 내 데이터 품질 현황 시각화
- 히트맵 및 시계열 그래프를 통한 데이터 품질 트렌드 분석

## 🛠 기술 스택

### Frontend
- **React 18** - 사용자 인터페이스 구축
- **TypeScript** - 타입 안정성 보장
- **Vite** - 빠른 개발 서버 및 빌드 도구
- **Tailwind CSS** - 유틸리티 기반 스타일링
- **shadcn/ui** - 고품질 UI 컴포넌트 라이브러리
- **React Router** - 클라이언트 사이드 라우팅
- **ApexCharts** - 데이터 시각화

### Backend
- **Spring Boot 3.5.7** - RESTful API 서버
- **Java 17** - 백엔드 언어
- **JPA/Hibernate** - ORM 프레임워크
- **PostgreSQL (Supabase)** - 관계형 데이터베이스

### AI Service
- **Python 3** - AI 서비스 구현
- **FastAPI** - 고성능 비동기 API 프레임워크
- **Qdrant** - 벡터 데이터베이스
- **Hugging Face** - 임베딩 모델 (`multilingual-e5-large`)
- **OpenAI GPT-3.5-turbo** - 추천 사유 생성

### DevOps & Infrastructure
- **Docker** - 컨테이너화
- **Docker Compose** - 멀티 컨테이너 애플리케이션 관리
- **Nginx** - 리버스 프록시 및 로드 밸런싱

## 🏗 시스템 아키텍처

```
┌─────────────┐
│   Frontend  │  React + TypeScript + Vite
│   (Nginx)   │
└──────┬──────┘
       │
       ├──────────────┬──────────────────┐
       │              │                  │
       ▼              ▼                  ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│   Backend   │  │  AI Service  │  │  AI Service  │
│  (REST API) │  │  (FastAPI)    │  │  (FastAPI)   │
│Spring Boot  │  │  (직접 호출)   │  │ (백엔드 경유)   │
└──────┬──────┘  └──────┬───────┘  └──────┬───────┘
       │               │                  │
       │               │                  │
       ▼               │                  │
┌──────────┐          │                  │
│Supabase  │          │                  │
│PostgreSQL│          │                  │
└──────────┘          │                  │
                       │                  │
        ┌──────────────┼──────────────────┘
        │              │                  │
        ▼              ▼                  ▼
   ┌──────────┐  ┌──────────┐      ┌──────────┐
   │Hugging   │  │  Qdrant  │      │ OpenAI   │
   │Face API  │  │Vector DB │      │ GPT API  │
   │(외부 API) │  │(외부 클라우드)│      │(외부 API)│
   └──────────┘  └──────────┘      └──────────┘
```

### 데이터 흐름

#### 1. 감상문 작성 및 자동 추천 생성 플로우
1. **감상문 작성**: 사용자가 감상문을 작성하면 프론트엔드에서 백엔드로 전송
2. **감상문 저장**: Spring Boot 백엔드가 Supabase PostgreSQL에 감상문 저장 (동기 처리)
3. **추천 요청**: 백엔드가 비동기로 AI 서비스(FastAPI)에 추천 요청 전송
4. **임베딩 생성**: AI 서비스가 Hugging Face API를 통해 감상문 텍스트를 벡터로 변환
5. **벡터 검색**: AI 서비스가 Qdrant 클라우드 API를 통해 유사도가 높은 곡 검색
6. **추천 사유 생성**: AI 서비스가 OpenAI GPT API를 통해 각 추천 곡에 대한 추천 사유 생성
7. **결과 저장**: AI 서비스가 백엔드 API를 호출하여 추천 결과를 Supabase PostgreSQL에 저장

**참고**: 이 플로우에서 추천 생성이 실패하거나 누락된 경우, 사용자는 다음 플로우를 통해 수동으로 추천을 다시 생성할 수 있습니다.

#### 2. 데이터 품질 조회 플로우 (프론트엔드 → FastAPI 직접 호출)
1. **데이터 품질 요청**: 프론트엔드에서 FastAPI(`/ai-api/admin/data-quality`)로 직접 요청
2. **데이터 분석**: AI 서비스가 Supabase PostgreSQL에서 데이터를 조회하고 품질을 분석
3. **결과 반환**: 데이터 품질 현황(완성도, 시계열 트렌드 등)을 JSON 형태로 반환

**참고**: Qdrant는 클라우드 서비스로, AI 서비스 내부에서 QdrantClient를 통해 직접 API로 연결됩니다. 별도의 로컬 서비스나 컨테이너가 아닙니다.

## 🔑 주요 기능 상세

### 1. 감상문 기반 추천 시스템

사용자가 작성한 감상문의 의미를 벡터 임베딩으로 변환하고, Qdrant 벡터 데이터베이스에서 유사도가 높은 곡을 검색합니다. 각 추천 곡에 대해서는 GPT-3.5를 활용하여 개인화된 추천 사유를 생성합니다.

**핵심 알고리즘:**
- 텍스트 임베딩: `multilingual-e5-large` 모델 사용
- 유사도 측정: Cosine Similarity
- 추천 사유 생성: GPT-3.5-turbo를 활용한 자연어 생성

<details>
<summary>📝 주요 코드 보기</summary>

**감상문 기반 추천 실행 (recommend_by_review.py)**

```python
async def recommend_by_review(review_text: str, review_id: int = None, limit: int = 10):
    """감상문 텍스트를 기반으로 곡을 추천"""
    try:
        # Qdrant 서비스 초기화
        qdrant_service = QdrantService()
        await qdrant_service.initialize()
        
        # 감상문 기반 추천 실행
        recommendations = await qdrant_service.recommend_tracks_by_content(
            artist="",
            metadata={},
            content=review_text,
            review_summary="",
            lyrics="",
            limit=limit
        )
        
        # 추천사유 생성
        reason_service = RecommendationReasonService()
        recommendations_with_reasons = []
        
        for rec in recommendations:
            try:
                # LLM을 사용한 추천사유 생성
                payload = rec.get("payload", {})
                
                reason = reason_service.generate_recommendation_reason_with_llm(
                    user_review=review_text,
                    recommended_track=payload
                )
                
                # 추천사유를 포함한 새로운 추천 결과 생성
                rec_with_reason = rec.copy()
                rec_with_reason["reason"] = reason
                recommendations_with_reasons.append(rec_with_reason)
                
            except Exception as e:
                print(f"⚠️ 추천사유 생성 실패: {e}")
                # 추천사유 생성 실패 시 기본 메시지 사용
                rec_with_reason = rec.copy()
                rec_with_reason["reason"] = f"감상문과 유사한 스타일의 곡입니다. (유사도: {rec.get('score', 0.0)*100:.1f}%)"
                recommendations_with_reasons.append(rec_with_reason)
        
        # review_id가 제공되면 DB에 저장
        if review_id:
            save_recommendations_to_db(review_id, recommendations_with_reasons, review_text)
        
        # 결과를 JSON 형태로 반환
        result = {
            "success": True,
            "recommendations": recommendations_with_reasons,
            "count": len(recommendations_with_reasons)
        }
        
        await qdrant_service.disconnect()
```

**임베딩 생성 (embedding_service.py)**

```python
    async def get_embedding(self, track_data: Dict[str, Any]) -> Optional[List[float]]:
        """단일 임베딩 생성"""
        if not self.client:
            error_msg = "HF_TOKEN이 설정되지 않았습니다."
            print(f"❌ {error_msg}")
            self._save_failed_data(track_data, error_msg)
            return None
            
        try:
            import requests
            
            text = self._create_text(track_data)
            
            # E5 모델은 특별한 프롬프트 형식 필요
            if not text.startswith("query: ") and not text.startswith("passage: "):
                text = f"query: {text}"
            
            # 직접 API 호출 시도
            api_key = os.getenv('HF_TOKEN')
            headers = {"Authorization": f"Bearer {api_key}"}
            
            # Inference API 엔드포인트
            api_url = "https://api-inference.huggingface.co/models/intfloat/multilingual-e5-large"
            
            response = requests.post(
                api_url,
                headers=headers,
                json={"inputs": text},
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 결과가 리스트인 경우
            if isinstance(result, list):
                # E5 모델은 보통 첫 번째 요소가 임베딩 벡터
                if len(result) > 0 and isinstance(result[0], list):
                    return result[0]
                return result
            
            return result
        
            
        except Exception as e:
            error_msg = f"임베딩 생성 실패: {str(e)}"
            print(f"❌ {error_msg}")
            # 임베딩 없이는 저장하지 않음
            return None
```

**벡터 검색 (qdrant_service.py)**

```python
        # Qdrant에서 유사한 벡터 검색
        search_results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        # 결과 포맷팅
        recommendations = []
        for result in search_results:
            recommendations.append({
                "id": result.id,
                "score": result.score,
                "payload": result.payload
            })
        
        if recommendations:
            print(f"   최고 유사도: {recommendations[0].get('score', 0):.4f}")
        
        return recommendations
        
    except Exception as e:
        print(f"❌ 추천 검색 실패: {e}")
        import traceback
        traceback.print_exc()
        return []
```

</details>

### 2. 비동기 처리

감상문 저장과 추천 생성을 분리하여 사용자 응답 시간을 최소화했습니다. 추천 생성은 비동기로 처리되며, 실패하더라도 감상문 저장은 성공으로 처리됩니다.

<details>
<summary>📝 주요 코드 보기</summary>

**감상문 저장 및 비동기 추천 요청 (UserReviewService.java)**

```java
    public UserReviewResponse createUserReview(UserReviewRequest request) {
        try {
            
            UserReview userReview = UserReview.builder()
                .albumId(request.getAlbumId())
                .userId(request.getUserId())
                .trackName(request.getTrackName())
                .artistName(request.getArtistName())
                .reviewContent(request.getReviewContent())
                .rating(request.getRating())
                .mood(request.getMood())
                .genre(request.getGenre())
                .energyLevel(request.getEnergyLevel())
                .bpm(request.getBpm())
                .vocalStyle(request.getVocalStyle())
                .instrumentation(request.getInstrumentation())
                .tags(request.getTags())
                .isPublic(request.getIsPublic())
                .isFeatured(false)
                .likeCount(0)
                .commentCount(0)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();
            
            UserReview savedReview = userReviewRepository.save(userReview);
            
            return convertToResponse(savedReview);
            
        } catch (Exception e) {
            log.error("감상문 생성 오류: ", e);
            throw new RuntimeException("감상문 생성 중 오류가 발생했습니다: " + e.getMessage());
        }
    }
```

**비동기 추천 생성 (UserReviewService.java)**

```java
    public void generateRecommendationsForReview(Integer reviewId, String reviewText) {
        try {
            // HTTP 클라이언트 생성
            HttpClient client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(30))
                .build();
            
            // 요청 데이터 생성
            ObjectMapper objectMapper = new ObjectMapper();
            Map<String, Object> requestData = new HashMap<>();
            requestData.put("review_text", reviewText);
            requestData.put("review_id", reviewId);
            requestData.put("limit", 3);
            
            String requestBody = objectMapper.writeValueAsString(requestData);
            
            // HTTP 요청 생성
            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(aiServiceUrl + "/recommend/by-review"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .timeout(Duration.ofSeconds(60))
                .build();
            
            // 요청 전송
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            
            if (response.statusCode() == 200) {
                log.info("추천 생성 완료: review_id={}", reviewId);
                log.info("FastAPI 응답: {}", response.body());
            } else {
                log.error("추천 생성 실패: review_id={}, statusCode={}, response={}", 
                    reviewId, response.statusCode(), response.body());
            }
            
        } catch (Exception e) {
            log.error("추천 생성 오류: review_id={}, error={}", reviewId, e.getMessage());
        }
```

</details>

### 3. 데이터 품질 관리

데이터베이스 내 데이터 품질을 모니터링하고 시각화하여 데이터의 신뢰성을 유지합니다.

<details>
<summary>📝 주요 코드 보기</summary>

**데이터 품질 조회 API (api_server.py)**

```python
@app.get("/admin/data-quality")
async def get_data_quality():
    """데이터 품질 히스토리 및 현재 상태 조회"""
    try:
        csv_file = '/app/data_quality_history.csv'
        
        # CSV 파일이 없으면 빈 응답
        if not os.path.exists(csv_file):
            return {
                "success": False,
                "message": "데이터 품질 히스토리 파일이 없습니다.",
                "data": None
            }
        
        # CSV 파일 읽기
        df = pd.read_csv(csv_file)
        
        # datetime으로 변환
        df['datetime'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('datetime')
        
        # 최신 분석 결과 (마지막 행)
        latest_row = df.iloc[-1]
        
        # 전체 시계열 데이터 추출
        timeseries_data = {
            "dates": df['datetime'].dt.strftime('%Y-%m-%d %H:%M').tolist(),
            "overall_quality": df['overall_quality'].tolist(),
            "total_records": df['total_records'].tolist(),
            "total_fields": df['total_fields'].tolist() if 'total_fields' in df.columns else []
        }
        
        # 필드별 완성도 데이터 추출
        completeness_fields = [col for col in df.columns if col.endswith('_completeness')]
        field_completeness = {}
        
        for col in completeness_fields:
            field_name = col.replace('_completeness', '')
            # 메타데이터 필드 제외
            if field_name not in ['date', 'timestamp']:
                field_completeness[field_name] = {
                    "history": df[col].tolist(),
                    "latest": float(latest_row[col]),
                    "missing_pct": float(latest_row.get(f'{field_name}_missing_pct', 0))
                }
        
        # 최신 분석 결과 요약
        latest_summary = {
            "date": latest_row['date'],
            "timestamp": latest_row['timestamp'],
            "overall_quality": float(latest_row['overall_quality']),
            "total_records": int(latest_row['total_records']),
            "total_fields": int(latest_row.get('total_fields', 0)),
            "field_completeness": {field: data["latest"] for field, data in field_completeness.items()}
        }
        
        return {
            "success": True,
            "data": {
                "latest": latest_summary,
                "timeseries": timeseries_data,
                "field_completeness": field_completeness
            }
        }
        
    except Exception as e:
        print(f"❌ 데이터 품질 조회 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "data": None
        }
```

</details>

## 📊 주요 API 엔드포인트

### Backend (Spring Boot)
- `POST /api/user-reviews` - 감상문 작성
- `GET /api/user-reviews` - 감상문 목록 조회
- `GET /api/user-reviews/{id}` - 특정 감상문 조회
- `POST /api/tracks` - 트랙 정보 저장/조회
- `POST /api/recommend-tracks` - 추천 트랙 저장
- `GET /api/albums/search` - 앨범 검색

### AI Service (FastAPI)
- `POST /recommend/by-review` - 감상문 기반 추천 생성 (프론트엔드 직접 호출 또는 백엔드 경유)
- `GET /admin/data-quality` - 데이터 품질 현황 조회 (프론트엔드 직접 호출)
- `POST /build-vector-db` - 벡터 DB 구축

**참고**: 일부 AI 서비스 엔드포인트는 프론트엔드에서 Nginx 프록시(`/ai-api`)를 통해 직접 호출하며, 나머지는 Spring Boot 백엔드를 경유합니다.

## 🎯 향후 개선 계획

### 1. 추천 정확도 향상
- **곡 메타데이터 보강**: 현재 데이터셋의 곡 메타데이터(장르, 무드, BPM, 보컬 스타일 등)를 더욱 상세하고 정확하게 수집 및 보강
- **다양한 메타데이터 소스 통합**: 음악 플랫폼 API, 음악 데이터베이스 등 다양한 소스에서 메타데이터 수집
- **메타데이터 기반 하이브리드 추천**: 벡터 유사도와 메타데이터 필터링을 결합한 하이브리드 추천 시스템 구현

### 2. 데이터 품질 향상
- **데이터 검증 로직 강화**: 입력 데이터의 품질을 검증하는 자동화된 프로세스 구축
- **데이터 클리닝 파이프라인**: 중복 데이터 제거, 누락된 필드 보완 등의 데이터 클리닝 자동화
- **실시간 데이터 품질 모니터링**: 데이터 품질 지표를 실시간으로 추적하고 알림 시스템 구축
- **데이터 증강**: 외부 소스와의 매칭을 통한 데이터 보강

### 3. 시스템 성능 최적화
- 추천 시스템 응답 시간 개선
- 벡터 검색 성능 최적화
- 캐싱 전략 도입

### 4. 사용자 경험 개선
- 개인화된 대시보드
- 추천 결과에 대한 사용자 피드백 수집 및 학습
- 감상문 작성 시 자동 완성 기능


## 🚀 설치 및 실행

### 사전 요구사항
- Docker & Docker Compose

### 환경 변수 설정

#### 개발 환경
`backend/.env` 파일을 생성하고 다음 내용을 설정합니다:

```env
# 프론트엔드 설정
VITE_API_URL=http://localhost:8080

# 자바 백엔드 설정
AI_SERVICE_URL=http://ai-api:8000

# AI 서비스 설정
ALLOWED_ORIGINS=http://localhost:3001,http://localhost:3000

# 데이터베이스 설정 (Supabase)
SPRING_DATASOURCE_URL=jdbc:postgresql://your-supabase-host:5432/your-database
SPRING_DATASOURCE_USERNAME=your-username
SPRING_DATASOURCE_PASSWORD=your-password

# Hugging Face API
HF_TOKEN=your-hugging-face-token

# Qdrant 설정
QDRANT_URL=https://your-qdrant-host:6333
QDRANT_API_KEY=your-qdrant-api-key

# OpenAI API
OPENAI_API_KEY=your-openai-api-key
```

#### 운영 환경
`env.production.example` 파일을 참고하여 운영 환경 설정 파일을 생성합니다.

### Docker Compose를 이용한 실행

#### 개발 환경
```bash
# 전체 서비스 실행
docker-compose up -d

# 특정 서비스만 실행
docker-compose up -d java-backend
docker-compose up -d ai-api
docker-compose up -d frontend
```

#### 운영 환경
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 로컬 개발 환경 실행

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

#### Backend (Spring Boot)
```bash
cd backend
./gradlew bootRun
```

#### AI Service
```bash
cd backend/ai-service
pip install -r requirements.txt
python api_server.py
```
