# services/qdrant_service.py
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Any, Set

class QdrantService:
    def __init__(self):
        self.client = None
        self.collection_name = "allthatjazz_album"
        self.vector_size = 1024  # intfloat/multilingual-e5-large 모델용
        
    async def initialize(self):
        """Qdrant 클라우드 연결"""
        try:
            # 클라우드 URL과 API 키 사용
            self.client = QdrantClient(
                url=os.getenv("QDRANT_URL"),
                api_key=os.getenv("QDRANT_API_KEY")
            )
            
            # 컬렉션 생성 (이미 있으면 무시)
            try:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                print("✅ Qdrant 클라우드 컬렉션 생성 완료")
            except Exception:
                print("ℹ️ Qdrant 컬렉션이 이미 존재합니다")
                
        except Exception as e:
            print(f"❌ Qdrant 클라우드 연결 실패: {e}")
            raise
    
    async def get_existing_ids(self) -> Set[str]:
        """이미 업로드된 ID 목록 조회 (point_id 기준)"""
        try:
            result = self.client.scroll(
                collection_name=self.collection_name,
                limit=10000,
                with_payload=False,  # payload 불필요
                with_vectors=False
            )
            
            existing_ids = set()
            for point in result[0]:
                # point.id를 문자열로 변환 (Supabase ID와 타입 일치)
                existing_ids.add(str(point.id))
            
            return existing_ids
        except Exception as e:
            print(f"⚠️ 기존 ID 조회 실패: {e}")
            return set()
    
    async def add_track(self, track_data: Dict[str, Any], embedding: List[float]):
        """트랙 데이터를 벡터 DB에 추가"""
        try:
            # ID를 정수로 변환 (Qdrant 요구사항)
            point_id = int(track_data["id"]) if track_data["id"] else 0
            
            # payload에서 sp_album_id 제거
            payload = track_data.copy()
            # payload['sp_album_id'] = str(track_data["id"])  # 이 줄 제거
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
        except Exception as e:
            print(f"❌ 벡터 저장 실패: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "status": "healthy",
                "collection": self.collection_name,
                "points_count": info.points_count
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": self.collection_name,
                "points_count": 0,
                "error": str(e)
            }

    async def recommend_tracks_by_content(
        self,
        artist: str = "",
        metadata: Dict[str, Any] = {},
        content: str = "",
        review_summary: str = "",
        lyrics: str = "",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        감상문 텍스트를 기반으로 곡을 추천합니다.
        
        Args:
            artist: 아티스트 이름 (선택사항, 필터링용)
            metadata: 메타데이터 필터 (선택사항)
            content: 감상문 텍스트 (필수)
            review_summary: 리뷰 요약 (선택사항)
            lyrics: 가사 (선택사항, 현재 미사용)
            limit: 추천할 곡 수 (기본값: 10)
            
        Returns:
            추천 결과 리스트 (각 항목은 {"id", "score", "payload"} 형태)
        """
        if not self.client:
            raise RuntimeError("Qdrant 클라이언트가 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        
        if not content:
            print("⚠️ 감상문 내용이 비어있습니다.")
            return []
        
        try:
            print(f"🔍 추천 검색 시작: 감상문 {len(content)}자, limit={limit}")
            
            # 임베딩 서비스 사용하여 감상문을 벡터로 변환
            from services.embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService()
            await embedding_service.initialize()
            
            # 감상문 텍스트를 임베딩으로 변환하기 위한 데이터 생성
            # EmbeddingService의 _create_text 메서드 형식에 맞게 구성
            review_data = {
                "content": content,
                "review_summary": review_summary if review_summary else content[:200],  # 요약이 없으면 내용 일부 사용
            }
            
            print(f"📝 임베딩 생성 중...")
            # 임베딩 생성
            query_embedding = await embedding_service.get_embedding(review_data)
            
            if not query_embedding:
                print("❌ 임베딩 생성 실패")
                return []
            
            if len(query_embedding) != self.vector_size:
                print(f"❌ 임베딩 크기 불일치: 기대={self.vector_size}, 실제={len(query_embedding)}")
                return []
            
            print(f"✅ 임베딩 생성 완료: {len(query_embedding)}차원")
            
            # 필터 구성 (선택사항)
            query_filter = None
            if artist:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="album_artist",
                            match=MatchValue(value=artist)
                        )
                    ]
                )
                print(f"🔍 아티스트 필터 적용: {artist}")
            
            # Qdrant에서 유사한 벡터 검색
            print(f"🔎 Qdrant 벡터 검색 중...")
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
            
            print(f"✅ 추천 검색 완료: {len(recommendations)}개 곡 발견")
            if recommendations:
                print(f"   최고 유사도: {recommendations[0].get('score', 0):.4f}")
            
            return recommendations
            
        except Exception as e:
            print(f"❌ 추천 검색 실패: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def disconnect(self):
        """연결 해제"""
        self.client = None