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
from services.recommendation_reason_service import RecommendationReasonService

# 환경 변수 로드
env_path = project_root.parent / '.env'
load_dotenv(env_path)

def save_recommendations_to_db(review_id: int, recommendations: list, user_review_text: str):
    """추천 결과를 Java 백엔드 DB에 저장합니다."""
    try:
        print(f"💾 추천 결과를 DB에 저장 중... (review_id: {review_id}, 추천 개수: {len(recommendations)})")
        
        if not recommendations:
            print("⚠️ 저장할 추천 결과가 없습니다.")
            return
        
        # 간단한 세션 사용 (연결 재사용)
        session = requests.Session()
        
        # Java 백엔드 URL 설정
        backend_url = "http://java-backend:8080"
        print(f"🔗 백엔드 연결 대상: {backend_url}")
        
        saved_count = 0
        failed_count = 0
        
        # Java 백엔드 API 호출하여 추천 결과 저장
        for i, rec in enumerate(recommendations):
            # Track 정보
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
            track_url = f"{backend_url}/api/tracks"
            try:
                print(f"📤 Track 저장 요청: {track_data['artistName']} - {track_data['trackTitle']}")
                track_response = session.post(
                    track_url,
                    json=track_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                print(f"📥 Track 응답 상태: {track_response.status_code}")
            except requests.exceptions.ConnectionError as e:
                print(f"❌ Track 저장 실패 (연결 오류): {track_url} - {e}")
                failed_count += 1
                continue
            except requests.exceptions.Timeout as e:
                print(f"❌ Track 저장 실패 (타임아웃): {track_url} - {e}")
                failed_count += 1
                continue
            except requests.exceptions.RequestException as e:
                print(f"❌ Track 저장 실패: {track_url} - {e}")
                failed_count += 1
                continue
            
            if track_response.status_code == 200:
                track_id = track_response.json().get("id")
                print(f"✅ Track 저장 완료: {track_data['artistName']} - {track_data['trackTitle']} (ID: {track_id})")
                
                # 이미 생성된 추천 사유 사용 (중복 생성 제거)
                recommendation_reason = rec.get("reason", "감상문과 유사한 스타일의 곡입니다.")
                
                # RecommendTrack 저장
                recommend_data = {
                    "userReviewId": review_id,
                    "trackId": track_id,
                    "recommendationScore": rec.get("score", 0.0),
                    "recommendationReason": recommendation_reason
                }

                try:
                    recommend_response = session.post(
                        "http://java-backend:8080/api/recommend-tracks",
                        json=recommend_data,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if recommend_response.status_code == 200:
                        print(f"✅ 추천 저장 완료: {track_data['artistName']} - {track_data['trackTitle']}")
                        saved_count += 1
                    else:
                        print(f"❌ 추천 저장 실패: {recommend_response.status_code} - {recommend_response.text}")
                        failed_count += 1
                except requests.exceptions.ConnectionError as e:
                    print(f"❌ 추천 저장 실패 (연결 오류): {e}")
                    failed_count += 1
                except requests.exceptions.Timeout as e:
                    print(f"❌ 추천 저장 실패 (타임아웃): {e}")
                    failed_count += 1
                except requests.exceptions.RequestException as e:
                    print(f"❌ 추천 저장 실패: {e}")
                    failed_count += 1
            else:
                print(f"❌ Track 저장 실패: {track_response.status_code} - {track_response.text}")
                failed_count += 1
        
        print(f"💾 추천 결과 저장 완료: 성공 {saved_count}개, 실패 {failed_count}개")
        
    except Exception as e:
        print(f"❌ DB 저장 실패: {e}")
        import traceback
        traceback.print_exc()

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
        
        # 추천사유 생성
        reason_service = RecommendationReasonService()
        recommendations_with_reasons = []
        
        for rec in recommendations:
            try:
                # LLM을 사용한 추천사유 생성
                payload = rec.get("payload", {})
                print(f"🔍 추천 데이터 확인: {payload.get('track_artist', 'Unknown')} - {payload.get('track_title', 'Unknown')}")
                
                reason = reason_service.generate_recommendation_reason_with_llm(
                    user_review=review_text,
                    recommended_track=payload
                )
                
                # 추천사유를 포함한 새로운 추천 결과 생성
                rec_with_reason = rec.copy()
                rec_with_reason["reason"] = reason
                recommendations_with_reasons.append(rec_with_reason)
                
                print(f"💡 추천사유 생성: {reason[:50]}...")
                
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