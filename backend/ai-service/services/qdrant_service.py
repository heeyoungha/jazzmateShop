# services/qdrant_service.py
import os
from supabase import create_client, Client
from typing import List, Dict, Any, Optional

class QdrantService:
    def __init__(self, embedding_service=None):
        self.client: Optional[Client] = None
        self.embedding_service = embedding_service

    async def initialize(self):
        """Supabase 연결"""
        try:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if not url or not key:
                raise ValueError("SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY 환경변수가 필요합니다")
            self.client = create_client(url, key)
            print("✅ Supabase(pgvector) 연결 완료")
        except Exception as e:
            print(f"❌ Supabase 연결 실패: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """헬스 체크"""
        try:
            response = self.client.table("embedding_vectors").select("id", count="exact").limit(1).execute()
            return {
                "status": "healthy",
                "collection": "embedding_vectors",
                "points_count": response.count
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": "embedding_vectors",
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
        """감상문 텍스트를 기반으로 곡을 추천합니다."""
        if not self.client:
            raise RuntimeError("Supabase 클라이언트가 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")

        if not content:
            print("⚠️ 감상문 내용이 비어있습니다.")
            return []

        try:
            print(f"🔍 추천 검색 시작: 감상문 {len(content)}자, limit={limit}")

            if self.embedding_service is None:
                from services.embedding_service import EmbeddingService
                self.embedding_service = EmbeddingService()
                await self.embedding_service.initialize()

            review_data = {
                "content": content,
                "review_summary": review_summary if review_summary else content[:200],
            }

            print(f"📝 임베딩 생성 중...")
            query_embedding = await self.embedding_service.get_embedding(review_data)

            if not query_embedding:
                print("❌ 임베딩 생성 실패")
                return []

            print(f"✅ 임베딩 생성 완료: {len(query_embedding)}차원")

            # Supabase RPC로 pgvector 유사도 검색
            print(f"🔎 pgvector 벡터 검색 중...")
            response = self.client.rpc(
                "match_embeddings",
                {"query_embedding": query_embedding, "match_count": limit}
            ).execute()

            recommendations = []
            for row in response.data:
                recommendations.append({
                    "id": row["id"],
                    "score": row["score"],
                    "payload": {
                        "album_title": row.get("album_title", ""),
                        "album_artist": row.get("artist", ""),
                        "title": row.get("title", ""),
                        "reviewer": row.get("reviewer", ""),
                        "rating": row.get("rating"),
                    }
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
