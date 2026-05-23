"""
OpenAI API 서비스

GPT를 사용한 리뷰 요약 및 분석

두 가지 모드 지원:
1. Realtime Mode: 일반 Chat API (즉시 처리, 정상 가격)
2. Batch Mode: Batch API (24시간 이내 처리, 50% 할인)
"""
import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIService:
    """OpenAI API 서비스 클래스"""
    
    def __init__(self):
        """OpenAI 클라이언트 초기화"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"  
        logger.info("✅ OpenAI 클라이언트 초기화 완료")
    
    def _get_prompt_template(self) -> str:
        """GPT API용 프롬프트 템플릿 반환"""
        return """
# Music Review Categorization Prompt (JSON Output)

You are an expert music editor and reviewer. I will provide a detailed, technical English review of a music album or performance.

## Task
1. Analyze the original review carefully, paragraph by paragraph.
2. Identify and categorize each portion of the review into meaningful categories. Common categories include:
   - 'artist_info': artist background, style, influences
   - 'album_info': album context, recording style, production
   - 'track_info': individual track descriptions, compositional structure, notable moments (can be further divided by 'track_name')
   - 'performance_note': live/studio performance insights, improvisation, group interaction
   - 'cultural_context': historical or cultural references, musical traditions
   - 'instrumentation': instruments used, playing techniques
   - 'composition_influence': inspirations from other musicians or genres
   - 'reviewer_opinion': reviewer's evaluation, personal impressions
   - 'vocal_style': vocal characteristics, singing techniques, vocal performance (ONLY if vocal-related keywords are present)
   - (Optional) Add additional categories if the review includes content such as 'political_context', 'social_significance', or other unique aspects
3. If a paragraph contains multiple aspects (e.g., track description + instrumentation), split the information into relevant categories.
4. Summarize the content **clearly and concisely**, but maintain richness and nuance:
   - Keep all original musical terms, artist names, track titles, and technical expressions intact.
   - Avoid reducing rich descriptive passages to a single sentence.
5. Provide output in **JSON format** with:
   - "summary": overall review summary in both English and Korean
   - "categories": detailed categorization with English and Korean versions

## Output Format

{{
  "summary": {{
    "english": "Overall review summary in English here...",
    "korean": "전체 리뷰 요약이 한국어로 여기 들어갑니다..."
  }},
  "categories": {{
    "artist_info": {{
      "english": "Artist background and style information here...",
      "korean": "아티스트 배경과 스타일 정보가 여기 들어갑니다..."
    }},
    "album_info": {{
      "english": "Album context and production details here...",
      "korean": "앨범 맥락과 프로덕션 세부사항이 여기 들어갑니다..."
    }},
    "track_info": {{
      "english": "Individual track descriptions here...",
      "korean": "개별 트랙 설명이 여기 들어갑니다..."
    }},
    "performance_note": {{
      "english": "Performance insights and group interaction here...",
      "korean": "공연 인사이트와 그룹 상호작용이 여기 들어갑니다..."
    }},
    "cultural_context": {{
      "english": "Historical or cultural references here...",
      "korean": "역사적 또는 문화적 참조가 여기 들어갑니다..."
    }},
    "instrumentation": {{
      "english": "Instruments and playing techniques here...",
      "korean": "악기와 연주 기법이 여기 들어갑니다..."
    }},
    "composition_influence": {{
      "english": "Influences from other musicians or genres here...",
      "korean": "다른 음악가나 장르에서 받은 영향 요약이 여기 들어갑니다..."
    }},
    "reviewer_opinion": {{
      "english": "Reviewer's final opinion and evaluation here...",
      "korean": "평론가의 평가와 개인적 감상 요약이 여기 들어갑니다..."
    }},
    "vocal_style": {{
      "english": "Vocal characteristics, singing techniques, and vocal performance details here...",
      "korean": "보컬 특성, 노래 기법, 보컬 퍼포먼스 세부사항이 여기 들어갑니다..."
    }}
  }}
}}


### Instructions for GPT API
- Analyze every paragraph carefully; do not omit details.
- If a paragraph includes content that does not fit existing categories, create a new descriptive category.
- Maintain a balance between clarity for a general audience and preserving technical richness.
- For track descriptions, include track_name as a sub-key.
- Provide natural, fluent Korean translations that reflect nuance.
- **VOCAL STYLE ANALYSIS**: If the review contains any of these vocal-related keywords: 'vocal', 'voice', 'singing', 'singer', 'vocalist', 'vocal style', 'vocal technique', 'breath', 'phrasing', 'tone', 'timbre', 'vocal range', 'falsetto', 'head voice', 'chest voice', 'vibrato', 'scat', 'vocal improvisation', then include a 'vocal_style' category with detailed analysis of vocal characteristics, singing techniques, and vocal performance aspects.
- CRITICAL: Return output strictly in JSON format following the structure above.
- IMPORTANT: Do not wrap the JSON in markdown code blocks. Return pure JSON only.
- ESSENTIAL: Ensure all JSON objects are properly closed with matching braces.
- REQUIRED: Validate that your JSON is complete and valid before returning.
- MANDATORY: Your response must start with {{ and end with }}. No other text before or after.
- STRICT: If you cannot provide valid JSON, return an error message starting with "ERROR:".
- FORMAT: Your entire response must be parseable as valid JSON. No exceptions.

## Review Data
Use the following complete review data for analysis:

{{
  "url": {url},
  "title": {title},
  "reviewer": {reviewer},
  "date": {date},
  "content": {content},
  "album_info": {album_info},
  "youtube_info": {youtube_info},
  "rating": {rating},
  "track_listing": {track_listing},
  "personnel": {personnel}
}}

Important: Return pure JSON only, and do not include any other text. 반드시 JSON만 출력하고 마크다운·설명문을 붙이지 말 것.
"""
    
    def summarize_review(self, review: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        단일 리뷰를 GPT로 요약 및 카테고리화
        
        Args:
            review: 리뷰 데이터 딕셔너리
            
        Returns:
            요약 및 카테고리 데이터 (JSON)
        """
        try:
            # 프롬프트 생성
            prompt = self._get_prompt_template().format(
                url=review.get('url', ''),
                title=review.get('title', ''),
                reviewer=review.get('reviewer', ''),
                date=review.get('date', ''),
                content=review.get('content', ''),
                album_info=json.dumps(review.get('album_info', {})),
                youtube_info=json.dumps(review.get('youtube_info', {})),
                rating=review.get('rating'),
                track_listing=review.get('track_listing', ''),
                personnel=json.dumps(review.get('personnel', []))
            )
            
            # GPT API 호출
            logger.info(f"🤖 GPT 요약 시작: {review.get('title', 'Unknown')[:60]}...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            # 응답 파싱
            gpt_response = response.choices[0].message.content
            
            # JSON 파싱 시도
            try:
                summary_data = json.loads(gpt_response)
                logger.info(f"✅ GPT 요약 성공: {review.get('title', 'Unknown')[:60]}")
                return summary_data
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON 파싱 실패: {e}")
                logger.error(f"응답: {gpt_response[:200]}...")
                
                # 마크다운 코드 블록 제거 시도
                if gpt_response.startswith("```"):
                    gpt_response = gpt_response.strip("`").strip()
                    if gpt_response.startswith("json"):
                        gpt_response = gpt_response[4:].strip()
                    try:
                        summary_data = json.loads(gpt_response)
                        logger.info(f"✅ 코드 블록 제거 후 파싱 성공")
                        return summary_data
                    except:
                        pass
                
                return None
                
        except Exception as e:
            logger.error(f"❌ GPT 요약 실패: {e}")
            return None
    
    def summarize_reviews_batch(self, reviews: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """
        여러 리뷰를 순차적으로 요약
        
        Args:
            reviews: 리뷰 데이터 리스트
            
        Returns:
            요약이 추가된 리뷰 리스트
        """
        logger.info(f"🤖 {len(reviews)}개 리뷰 GPT 요약 시작")
        
        reviews_with_summary = []
        success_count = 0
        error_count = 0
        
        for idx, review in enumerate(reviews, 1):
            logger.info(f"📝 [{idx}/{len(reviews)}] 요약 중: {review.get('title', 'Unknown')[:60]}...")
            
            summary = self.summarize_review(review)
            
            if summary:
                review['review_summary'] = summary
                success_count += 1
            else:
                # 요약 실패 시 기본 구조 추가
                review['review_summary'] = {
                    "summary": {
                        "english": f"Summary failed for: {review.get('title', 'Unknown')}",
                        "korean": f"요약 실패: {review.get('title', 'Unknown')}"
                    },
                    "categories": {}
                }
                error_count += 1
            
            reviews_with_summary.append(review)
        
        logger.info(f"✅ GPT 요약 완료: 성공 {success_count}개, 실패 {error_count}개")
        return reviews_with_summary
    
    # ========================================
    # Batch API 메서드 (50% 비용 절감)
    # ========================================
    
    def build_batch_requests(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """개별 리뷰들을 하나의 Batch API 요청으로 변환"""
        
        logger.info(f"🔄 {len(reviews)}개 리뷰를 Batch API 요청으로 변환 중...")
        
        batch_requests = []
        for i, review in enumerate(reviews):
            try:
                prompt = self._get_prompt_template().format(
                    url=review.get('url', ''),
                    title=review.get('title', ''),
                    reviewer=review.get('reviewer', ''),
                    date=review.get('date', ''),
                    content=review.get('content', ''),
                    album_info=json.dumps(review.get('album_info', {})),
                    youtube_info=json.dumps(review.get('youtube_info', {})),
                    rating=review.get('rating'),
                    track_listing=review.get('track_listing', ''),
                    personnel=json.dumps(review.get('personnel', []))
                )
                
                # Batch API 요청 형식
                # custom_id에 batch_num을 포함하여 중복 방지
                url_suffix = review.get('url', 'unknown').split('/')[-1][:30]
                request = {
                    "custom_id": f"batch_{review.get('batch_num', 1)}_review_{review.get('id', i)}_{url_suffix}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.3
                    }
                }
                batch_requests.append(request)
                
            except Exception as e:
                logger.error(f"❌ 리뷰 {i} 변환 실패: {e}")
        
        logger.info(f"✅ {len(batch_requests)}개 Batch 요청 생성 완료")
        return batch_requests
    
    def upload_batch_file(self, batch_requests: List[Dict[str, Any]], batch_num: int) -> str:
        """Batch 요청 파일을 OpenAI에 업로드"""
        from pipeline_services.exceptions import NetworkError

        filename = f"/tmp/batch_requests_{batch_num}.jsonl"

        # 각 파일들을 하나의 JSONL 파일로 생성
        logger.info(f"📤 Batch 파일 생성 중: {filename}")
        with open(filename, 'w', encoding='utf-8') as f:
            for request in batch_requests:
                f.write(json.dumps(request) + '\n') # JSON 문자열로 직렬화

        # OpenAI에 업로드
        logger.info(f"📤 Batch 파일 업로드 중...")
        try:
            with open(filename, 'rb') as f:
                # files : Files API를 호출하기 위한 네임스페이스(객체)
                file_response = self.client.files.create(
                    file=f,
                    purpose='batch'
                )
        except Exception as e:
            err_str = str(e).lower()
            if 'connection' in err_str or 'timeout' in err_str or 'network' in err_str:
                raise NetworkError(f"OpenAI 파일 업로드 네트워크 오류 (재시도 가능): {e}") from e
            raise

        file_id = file_response.id
        logger.info(f"✅ 파일 업로드 성공: {file_id}")
        return file_id
    
    def create_batch_job(self, file_id: str) -> Optional[str]:
        """Batch 작업 생성 (Chat Completions용)"""

        try:
            logger.info("🚀 Batch 작업 생성 중...")
            
            batch_response = self.client.batches.create(
                input_file_id=file_id,
                endpoint="/v1/chat/completions",
                completion_window="24h"
            )
            
            batch_id = batch_response.id
            logger.info(f"✅ Batch 작업 생성 성공: {batch_id}")
            logger.info(f"📊 상태: {batch_response.status}")
            
            return batch_id
            
        except Exception as e:
            err_str = str(e).lower()
            if 'billing_hard_limit_reached' in err_str or 'billing hard limit' in err_str:
                from pipeline_services.exceptions import BillingLimitError
                raise BillingLimitError(f"OpenAI 결제 한도 도달: {e}") from e
            if 'enqueued token limit' in err_str or 'enqueued token' in err_str:
                from pipeline_services.exceptions import RateLimitError
                raise RateLimitError(f"OpenAI 대기 토큰 한도 초과 (잠시 후 재시도): {e}") from e
            logger.error(f"❌ Batch 작업 생성 실패: {e}")
            return None

    def create_embedding_batch_requests(
        self, 
        processed_summaries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Embedding Batch API 요청 생성"""
        
        logger.info(f"🔄 {len(processed_summaries)}개 요약을 Embedding Batch 요청으로 변환 중...")
        
        batch_requests = []
        for i, summary in enumerate(processed_summaries):
            try:
                # 임베딩할 텍스트 (summary_text 사용)
                text = summary.get('summary_text', '')
                if not text:
                    logger.warning(f"⚠️ processed_id {summary.get('id')}: summary_text 없음, 스킵")
                    continue
                
                # Batch API 요청 형식
                # custom_id에 processed_id와 raw_id 포함 (나중에 매핑용)
                processed_id = summary.get('id')
                raw_id = summary.get('raw_id')
                request = {
                    "custom_id": f"embedding_{processed_id}_{raw_id}",
                    "method": "POST",
                    "url": "/v1/embeddings",  # ✅ Embeddings 엔드포인트
                    "body": {
                        "model": "text-embedding-3-small",
                        "input": text
                    }
                }
                batch_requests.append(request)
                
            except Exception as e:
                logger.error(f"❌ 요약 {i} 변환 실패: {e}")
        
        logger.info(f"✅ {len(batch_requests)}개 Embedding Batch 요청 생성 완료")
        return batch_requests
    
    def create_embedding_batch_job(
        self, 
        file_id: str
    ) -> Optional[str]:
        """
        Embedding Batch 작업 생성
        
        Args:
            file_id: 업로드된 파일 ID
            
        Returns:
            Batch ID (성공 시) 또는 None
        """
        try:
            logger.info("🚀 Embedding Batch 작업 생성 중...")
            
            batch_response = self.client.batches.create(
                input_file_id=file_id,
                endpoint="/v1/embeddings",  # ✅ Embeddings 엔드포인트
                completion_window="24h"
            )
            
            batch_id = batch_response.id
            logger.info(f"✅ Embedding Batch 작업 생성 성공: {batch_id}")
            logger.info(f"📊 상태: {batch_response.status}")
            
            return batch_id
            
        except Exception as e:
            logger.error(f"❌ Embedding Batch 작업 생성 실패: {e}")
            return None
    
    def check_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Batch 상태 확인
        
        Args:
            batch_id: Batch ID
            
        Returns:
            Batch 상태 정보
        """
        try:
            logger.info(f"📊 Batch 상태 확인 중: {batch_id}")
            
            batch_response = self.client.batches.retrieve(batch_id)
            status = batch_response.status
            
            logger.info(f"📊 Batch 상태: {status}")
            
            request_counts = {}
            if hasattr(batch_response, 'request_counts'):
                counts = batch_response.request_counts
                request_counts = {
                    'total': getattr(counts, 'total', 0),
                    'completed': getattr(counts, 'completed', 0),
                    'failed': getattr(counts, 'failed', 0)
                }
                logger.info(f"📊 요청 통계:")
                logger.info(f"  - 총 요청: {request_counts['total']}")
                logger.info(f"  - 완료: {request_counts['completed']}")
                logger.info(f"  - 실패: {request_counts['failed']}")
            
            return {
                'id': batch_response.id,
                'status': status,
                'created_at': batch_response.created_at,
                'completed_at': getattr(batch_response, 'completed_at', None),
                'failed_at': getattr(batch_response, 'failed_at', None),
                'output_file_id': getattr(batch_response, 'output_file_id', None),
                'error_file_id': getattr(batch_response, 'error_file_id', None),
                'request_counts': request_counts
            }
            
        except Exception as e:
            logger.error(f"❌ 상태 확인 실패: {e}")
            return None
    
    def download_batch_results(self, batch_id: str, output_dir: str = "/tmp") -> Optional[str]:
        """
        Batch 결과 다운로드
        
        Args:
            batch_id: Batch ID
            output_dir: 결과 파일 저장 디렉토리
            
        Returns:
            결과 파일 경로 (성공 시) 또는 None
        """
        try:
            logger.info(f"📥 Batch 결과 다운로드 중: {batch_id}")
            
            # 상태 확인
            batch_info = self.check_batch_status(batch_id)
            if not batch_info or batch_info['status'] != 'completed':
                logger.warning(f"⚠️ Batch 미완료 상태: {batch_info.get('status') if batch_info else 'Unknown'}")
                return None
            
            # 결과 파일 다운로드
            output_file_id = batch_info.get('output_file_id')
            if not output_file_id:
                logger.error("❌ 출력 파일 ID를 찾을 수 없습니다.")
                return None
            
            file_content = self.client.files.content(output_file_id)
            
            # 파일 저장
            output_path = f"{output_dir}/batch_results_{batch_id}.jsonl"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(file_content.text)
            
            logger.info(f"✅ 결과 다운로드 완료: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ 결과 다운로드 실패: {e}")
            return None
    
    def parse_batch_results(self, results_file: str) -> Dict[str, Any]:
        """
        Batch 결과 파일 파싱
        
        Args:
            results_file: 결과 파일 경로
            
        Returns:
            Dict: {
                'summaries': Dict[str, Dict[str, Any]],  # custom_id를 키로 하는 요약 데이터
                'parsing_success': int,  # 파싱 성공 개수
                'parsing_failed': int,   # 파싱 실패 개수
                'errors': List[Dict]     # 에러 상세 정보
            }
        """
        logger.info(f"📖 Batch 결과 파싱 중: {results_file}")

        summaries = {}
        success_count = 0
        error_count = 0
        errors = []  # 에러 상세 정보
        total_prompt_tokens = 0
        total_completion_tokens = 0

        with open(results_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        result = json.loads(line.strip())
                        custom_id = result.get('custom_id', '')

                        # GPT 응답 파싱
                        if result.get('response', {}).get('status_code') == 200:
                            body = result['response']['body']
                            gpt_response = body['choices'][0]['message']['content']

                            # 토큰 사용량 집계
                            usage = body.get('usage', {})
                            total_prompt_tokens += usage.get('prompt_tokens', 0)
                            total_completion_tokens += usage.get('completion_tokens', 0)

                            # JSON 파싱
                            try:
                                summary_data = json.loads(gpt_response)
                                summaries[custom_id] = summary_data
                                success_count += 1
                            except json.JSONDecodeError as e:
                                logger.warning(f"⚠️ {custom_id}: JSON 파싱 실패")
                                error_count += 1
                                errors.append({
                                    'custom_id': custom_id,
                                    'error_type': 'json_parse_error',
                                    'error_message': str(e),
                                    'raw_response': gpt_response[:200]  # 처음 200자만
                                })
                        else:
                            status_code = result.get('response', {}).get('status_code', 'unknown')
                            error_msg = result.get('response', {}).get('body', {}).get('error', {}).get('message', 'Unknown API error')
                            logger.warning(f"⚠️ {custom_id}: API 오류 (status_code={status_code})")
                            error_count += 1
                            errors.append({
                                'custom_id': custom_id,
                                'error_type': 'api_error',
                                'error_message': f"Status {status_code}: {error_msg}",
                                'status_code': status_code
                            })

                    except Exception as e:
                        logger.error(f"❌ 결과 처리 오류: {e}")
                        error_count += 1
                        errors.append({
                            'custom_id': result.get('custom_id', 'unknown'),
                            'error_type': 'parse_error',
                            'error_message': str(e)
                        })

        logger.info(
            f"✅ 파싱 완료: 성공 {success_count}개, 실패 {error_count}개 | "
            f"토큰: prompt={total_prompt_tokens}, completion={total_completion_tokens}"
        )
        return {
            'summaries': summaries,
            'parsing_success': success_count,
            'parsing_failed': error_count,
            'errors': errors,
            'token_usage': {
                'prompt_tokens': total_prompt_tokens,
                'completion_tokens': total_completion_tokens,
                'total_tokens': total_prompt_tokens + total_completion_tokens,
            },
        }

    def parse_embedding_batch_results(self, results_file: str) -> Dict[str, Any]:
        """
        Embedding Batch 결과 파일 파싱 (/v1/embeddings 응답 형식)

        Args:
            results_file: 결과 JSONL 파일 경로

        Returns:
            Dict: {
                'items': List[Dict],  # [{'processed_id': str, 'raw_id': str, 'embedding': List[float]}]
                'parsing_success': int,
                'parsing_failed': int,
                'errors': List[Dict]
            }
        """
        logger.info(f"📖 Embedding batch 결과 파싱 중: {results_file}")
        items = []
        success_count = 0
        error_count = 0
        errors = []
        total_prompt_tokens = 0

        with open(results_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    result = json.loads(line.strip())
                    custom_id = result.get('custom_id', '')
                    # custom_id 형식: embedding_{processed_id}_{raw_id}
                    parts = custom_id.split('_', 2)
                    if len(parts) != 3 or parts[0] != 'embedding':
                        error_count += 1
                        errors.append({'custom_id': custom_id, 'error_type': 'invalid_custom_id'})
                        continue
                    processed_id, raw_id = parts[1], parts[2]

                    if result.get('response', {}).get('status_code') != 200:
                        status_code = result.get('response', {}).get('status_code', 'unknown')
                        error_msg = result.get('response', {}).get('body', {}).get('error', {}).get('message', 'Unknown')
                        error_count += 1
                        errors.append({
                            'custom_id': custom_id,
                            'error_type': 'api_error',
                            'status_code': status_code,
                            'error_message': error_msg,
                        })
                        continue

                    body = result.get('response', {}).get('body', {})

                    # 토큰 사용량 집계 (embedding은 prompt_tokens만 존재)
                    usage = body.get('usage', {})
                    total_prompt_tokens += usage.get('prompt_tokens', 0)

                    data = body.get('data') or []
                    if not data or 'embedding' not in data[0]:
                        error_count += 1
                        errors.append({'custom_id': custom_id, 'error_type': 'missing_embedding'})
                        continue

                    embedding = data[0]['embedding']
                    items.append({
                        'processed_id': processed_id,
                        'raw_id': raw_id,
                        'embedding': embedding,
                    })
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append({
                        'custom_id': result.get('custom_id', 'unknown'),
                        'error_type': 'parse_error',
                        'error_message': str(e),
                    })

        logger.info(
            f"✅ Embedding 파싱 완료: 성공 {success_count}개, 실패 {error_count}개 | "
            f"토큰: prompt={total_prompt_tokens}"
        )
        return {
            'items': items,
            'parsing_success': success_count,
            'parsing_failed': error_count,
            'errors': errors,
            'token_usage': {
                'prompt_tokens': total_prompt_tokens,
                'completion_tokens': 0,
                'total_tokens': total_prompt_tokens,
            },
        }

