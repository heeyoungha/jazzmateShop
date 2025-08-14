#!/usr/bin/env python3
"""
감상문 기반 곡 추천 스크립트
"""

import argparse
import asyncio
import json
import os
import sys
import requests
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
from services.qdrant_service import QdrantService

# 환경 변수 로드
env_path = project_root.parent / '.env'
load_dotenv(env_path)

def save_recommendations_to_db(review_id: int, recommendations: list):
    """추천 결과를 Java 백엔드 DB에 저장합니다."""
    try:
        print(f"💾 추천 결과를 DB에 저장 중... (review_id: {review_id})")
        
        # 간단한 세션 사용 (연결 재사용)
        session = requests.Session()
        
        # Java 백엔드 API 호출하여 추천 결과 저장
        for i, rec in enumerate(recommendations):
            # Track 정보 저장
            track_data = {
                "trackTitle": rec.get("payload", {}).get("album_title", "Unknown"),
                "artistName": rec.get("payload", {}).get("album_artist", "Unknown"),
                "genre": rec.get("payload", {}).get("genre"),
                "mood": rec.get("payload", {}).get("mood"),
                "energy": rec.get("payload", {}).get("energy"),
                "bpm": rec.get("payload", {}).get("bpm"),
                "vocalStyle": rec.get("payload", {}).get("vocal_style"),
                "instrumentation": rec.get("payload", {}).get("instrumentation")
            }
            
            # Track 생성 또는 조회
            try:
                track_response = session.post(
                    "http://jazzmateshop-java-backend-1:8080/api/tracks",
                    json=track_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            except requests.exceptions.RequestException as e:
                print(f"❌ Track 저장 실패: {e}")
                continue
            
            if track_response.status_code == 200:
                track_id = track_response.json().get("id")
                print(f"✅ Track 저장 완료: {track_data['artistName']} - {track_data['trackTitle']} (ID: {track_id})")
                
                # RecommendTrack 저장
                recommend_data = {
                    "userReviewId": review_id,
                    "trackId": track_id,
                    "recommendationScore": rec.get("score", 0.0),
                    "recommendationReason": f"감상문 기반 추천 (유사도: {rec.get('score', 0.0):.3f})"
                }

                try:
                    recommend_response = session.post(
                        "http://jazzmateshop-java-backend-1:8080/api/recommend-tracks",
                        json=recommend_data,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if recommend_response.status_code == 200:
                        print(f"✅ 추천 저장 완료: {track_data['artistName']} - {track_data['trackTitle']}")
                    else:
                        print(f"❌ 추천 저장 실패: {recommend_response.status_code} - {recommend_response.text}")
                except requests.exceptions.RequestException as e:
                    print(f"❌ 추천 저장 실패: {e}")
            else:
                print(f"❌ Track 저장 실패: {track_response.status_code} - {track_response.text}")
        
        print("💾 모든 추천 결과 저장 완료!")
        
    except Exception as e:
        print(f"❌ DB 저장 실패: {e}")

async def recommend_by_review(review_text: str, review_id: int = None, limit: int = 10):
    """감상문 텍스트를 기반으로 곡을 추천합니다."""
    try:
        print(f"🎵 감상문 기반 추천 시작: {len(review_text)}자")
        
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
        
        print(f"✅ 추천 완료: {len(recommendations)}개 곡")
        
        # review_id가 제공되면 DB에 저장
        if review_id:
            save_recommendations_to_db(review_id, recommendations)
        
        # 결과를 JSON 형태로 반환
        result = {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations)
        }
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        await qdrant_service.disconnect()
        
    except Exception as e:
        print(f"❌ 추천 실패: {e}")
        error_result = {
            "success": False,
            "error": str(e),
            "recommendations": []
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser(description='감상문 기반 곡 추천')
    parser.add_argument('--review-text', required=True, help='감상문 텍스트')
    parser.add_argument('--review-id', type=int, help='감상문 ID (DB 저장용)')
    parser.add_argument('--limit', type=int, default=10, help='추천할 곡 수 (기본값: 10)')
    
    args = parser.parse_args()
    
    # 비동기 함수 실행
    asyncio.run(recommend_by_review(args.review_text, args.review_id, args.limit))

if __name__ == "__main__":
    main()