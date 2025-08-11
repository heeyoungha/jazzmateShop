# services/qdrant_service.py
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
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

    async def disconnect(self):
        """연결 해제"""
        self.client = None