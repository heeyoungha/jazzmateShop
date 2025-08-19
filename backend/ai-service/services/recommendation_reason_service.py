#!/usr/bin/env python3
"""
추천 사유 생성 서비스
"""

import re
import requests
import json
import os
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

class RecommendationReasonService:
    def __init__(self):
        self.similarity_threshold = 0.3  # 유사도 임계값
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
    
    def generate_recommendation_reason_with_llm(self, user_review: str, recommended_track: Dict[str, Any]) -> str:
        """
        LLM을 사용하여 추천 사유 생성
        
        Args:
            user_review: 사용자 감상문
            recommended_track: 추천된 트랙 정보
            
        Returns:
            생성된 추천 사유
        """
        try:
            # 추천 트랙 정보 추출 
            track_title = recommended_track.get("track_title", recommended_track.get("album_title", "Unknown Title"))
            artist_name = recommended_track.get("track_artist", recommended_track.get("album_artist", "Unknown Artist"))
            album_title = recommended_track.get("album_title", "Unknown Album")
            content = recommended_track.get("content", "")
            review_summary = recommended_track.get("review_summary", "")
            
            # 프롬프트 작성
            prompt = self._create_recommendation_prompt(
                user_review, track_title, artist_name, album_title, content, review_summary
            )
            
            # LLM API 호출
            recommendation_reason = self._call_llm_api(prompt)
            
            if recommendation_reason:
                return recommendation_reason
            else:
                # LLM 호출 실패 시 오류 문구 반환
                return "❌ 추천 사유 생성에 실패했습니다. API 서버에 문제가 있을 수 있습니다."
                
        except Exception as e:
            print(f"❌ LLM 추천 사유 생성 실패: {e}")
            # 오류 발생 시 구체적인 오류 문구 반환
            return f"❌ 추천 사유 생성 중 오류가 발생했습니다: {str(e)}"
    
    def _is_fallback_reason_sufficient(self, reason: str) -> bool:
        """기본 추천 사유가 충분한지 판단"""
        # 공통 특징이 2개 이상 있으면 충분하다고 판단
        return "와 같은 특징을 가지고 있어" in reason
    
    def _generate_fallback_reason(self, user_review: str, recommended_track: Dict[str, Any]) -> str:
        """
        LLM 호출 실패 시 사용할 개선된 기본 추천 사유 생성
        """
        try:
            track_title = recommended_track.get("track_title", "Unknown Title")
            artist_name = recommended_track.get("track_artist", "Unknown Artist")
            album_title = recommended_track.get("album_title", "Unknown Album")
            content = recommended_track.get("content", "")
            review_summary = recommended_track.get("review_summary", "")
            
            # 사용자 감상문에서 키워드 추출
            user_keywords = self._extract_keywords_from_review(user_review)
            
            # 추천 곡의 특징 추출
            track_features = self._extract_track_features(content, review_summary)
            
            # 공통점 찾기
            common_features = self._find_common_features(user_keywords, track_features)
            
            # 추천 사유 생성
            if common_features:
                reason = f"'{artist_name} - {track_title}'을 추천합니다. "
                reason += f"사용자의 감상문에서 언급한 {', '.join(common_features[:2])}와 같은 특징을 가지고 있어 "
                reason += f"비슷한 음악적 경험을 제공할 것입니다."
            else:
                reason = f"'{artist_name} - {track_title}'을 추천합니다. "
                reason += f"사용자의 감상문과 유사한 분위기와 스타일을 가지고 있어 "
                reason += f"새로운 음악적 발견의 기회가 될 것입니다."
            
            return reason
            
        except Exception as e:
            print(f"❌ 기본 추천 사유 생성 실패: {e}")
            track_title = recommended_track.get("track_title", "Unknown Title")
            artist_name = recommended_track.get("track_artist", "Unknown Artist")
            return f"'{artist_name} - {track_title}'을 추천합니다. 감상문과 유사한 분위기의 곡입니다."
    
    def _extract_keywords_from_review(self, review: str) -> List[str]:
        """사용자 감상문에서 키워드 추출"""
        keywords = []
        review_lower = review.lower()
        
        # 음악적 특징 키워드
        musical_keywords = {
            "피아노": ["피아노", "piano"],
            "트럼펫": ["트럼펫", "trumpet"],
            "색소폰": ["색소폰", "saxophone"],
            "드럼": ["드럼", "drum"],
            "베이스": ["베이스", "bass"],
            "빅밴드": ["빅밴드", "big band"],
            "재즈": ["재즈", "jazz"],
            "스윙": ["스윙", "swing"],
            "블루스": ["블루스", "blues"],
            "솔로": ["솔로", "solo"],
            "편곡": ["편곡", "arrangement"],
            "하모니": ["하모니", "harmony"],
            "리듬": ["리듬", "rhythm"],
            "멜로디": ["멜로디", "melody"],
            "감성": ["감성", "emotional"],
            "우아": ["우아", "elegant"],
            "세련": ["세련", "sophisticated"],
            "따뜻": ["따뜻", "warm"],
            "밝": ["밝", "bright"],
            "편안": ["편안", "comfortable"]
        }
        
        for keyword, variations in musical_keywords.items():
            if any(var in review_lower for var in variations):
                keywords.append(keyword)
        
        return keywords
    
    def _extract_track_features(self, content: str, review_summary: str) -> List[str]:
        """추천 곡의 특징 추출"""
        features = []
        combined_text = f"{content} {review_summary}".lower()
        
        # 악기 특징
        if any(instrument in combined_text for instrument in ["piano", "피아노"]):
            features.append("피아노")
        if any(instrument in combined_text for instrument in ["trumpet", "트럼펫"]):
            features.append("트럼펫")
        if any(instrument in combined_text for instrument in ["saxophone", "색소폰"]):
            features.append("색소폰")
        if any(instrument in combined_text for instrument in ["drum", "드럼"]):
            features.append("드럼")
        
        # 스타일 특징
        if any(style in combined_text for style in ["big band", "빅밴드"]):
            features.append("빅밴드")
        if any(style in combined_text for style in ["jazz", "재즈"]):
            features.append("재즈")
        if any(style in combined_text for style in ["swing", "스윙"]):
            features.append("스윙")
        if any(style in combined_text for style in ["blues", "블루스"]):
            features.append("블루스")
        
        # 음악적 특징
        if any(feature in combined_text for feature in ["solo", "솔로"]):
            features.append("솔로")
        if any(feature in combined_text for feature in ["arrangement", "편곡"]):
            features.append("편곡")
        if any(feature in combined_text for feature in ["harmony", "하모니"]):
            features.append("하모니")
        
        return features
    
    def _find_common_features(self, user_keywords: List[str], track_features: List[str]) -> List[str]:
        """사용자 키워드와 추천 곡 특징의 공통점 찾기"""
        common = []
        for keyword in user_keywords:
            if keyword in track_features:
                common.append(keyword)
        return common
    
    def _create_recommendation_prompt(self, user_review: str, track_title: str, artist_name: str, 
                                     album_title: str, content: str, review_summary: str) -> str:
        """
        LLM에 보낼 프롬프트 생성
        """
        prompt = f"""
당신은 음악 추천 전문가입니다. 사용자의 감상문을 바탕으로 추천된 곡에 대한 추천 사유를 작성해주세요.

**사용자 감상문:**
{user_review}

**추천된 곡 정보:**
- 아티스트: {artist_name}
- 곡명: {track_title}
- 앨범: {album_title}

**추천된 곡에 대한 전문가 리뷰 내용:**
{content[:500]}...

**추천된 곡에 대한 리뷰 요약:**
{review_summary[:300]}...

**요구사항:**
1. 사용자의 감상문과 추천된 곡의 공통점을 찾아 설명하세요
2. 추천된 곡의 특징과 매력을 간결하게 설명하세요
3. 왜 이 곡을 추천하는지 구체적인 이유를 제시하세요
4. 한국어로 작성하세요
5. 완전한 문장으로 마무리하세요 (문장이 중간에 끊어지지 않도록 주의)
6. 2-3문장으로 간결하게 작성하되, 반드시 완전한 문장으로 끝내세요

**중요:**
- 문장이 중간에 끊어지지 않도록 주의하세요
- 추천 사유만 작성하고, 다른 설명이나 부가 정보는 포함하지 마세요

**추천 사유:**
"""
        return prompt
    
    def _call_llm_api(self, prompt: str) -> Optional[str]:
        """
        OpenAI GPT API를 사용하여 LLM 호출
        """
        try:
            if not self.openai_api_key:
                print("⚠️ OpenAI API 키가 설정되지 않음")
                return None
            
            # OpenAI API 엔드포인트
            api_url = "https://api.openai.com/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "당신은 음악 추천 전문가입니다. 사용자의 감상문을 바탕으로 추천된 곡에 대한 추천 사유를 간결하고 명확하게 작성해주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 300,  # 완전한 문장 생성을 위해 토큰 수 증가
                "temperature": 0.7
            }
            
            print(f"🤖 OpenAI GPT API 호출 중...")
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    generated_text = result["choices"][0]["message"]["content"].strip()
                    print(f"✅ OpenAI 추천 사유 생성 성공: {generated_text[:100]}...")
                    return generated_text
                else:
                    print(f"⚠️ OpenAI 응답 형식 오류: {result}")
                    return None
            elif response.status_code == 429:
                # 할당량 초과 시 오류 문구 반환
                print("❌ OpenAI API 할당량 초과")
                return "⚠️ OpenAI API 할당량이 초과되어 추천 사유를 생성할 수 없습니다. 관리자에게 문의하세요."
            else:
                error_msg = f"OpenAI API 호출 실패 (상태코드: {response.status_code})"
                print(f"❌ {error_msg} - {response.text}")
                return f"❌ {error_msg}"
                
        except Exception as e:
            error_msg = f"OpenAI API 호출 중 네트워크 오류: {str(e)}"
            print(f"❌ {error_msg}")
            return f"❌ {error_msg}"
