from typing import Dict, Any, Optional
import logging
from pipeline_services import SupabaseService, OpenAIService
from pipeline_services.exceptions import BatchFailedError

logger = logging.getLogger(__name__)


class GptResultProcessor:
    """GPT 결과 처리 서비스"""
    
    def __init__(self, supabase_service: SupabaseService, openai_service: OpenAIService):

        self.db = supabase_service
        self.openai = openai_service
    
    def process_batch_results(
        self,
        batch_id: str,
        batch_num: int,
        batch_status: str
    ) -> Dict[str, Any]:
        """
        GPT Batch 결과 처리 (전체 프로세스)
        """
        logger.info(
            f"🚀 Processing GPT result: {batch_id} "
            f"(status={batch_status}, batch_num={batch_num})"
        )
        
        # ⚠️ 부분 성공 시 경고
        if batch_status == 'partial_success':
            logger.warning(
                f"⚠️ Processing partial success batch: "
                f"Only successful items will be processed."
            )

        # 배치가 실패/만료/취소로 확정된 경우 결과 처리를 건너뛰고 downstream을 중단한다.
        if batch_status in ('failed', 'expired', 'cancelled'):
            batch_info = self.openai.check_batch_status(batch_id)
            if batch_info and batch_info.get('errors'):
                logger.error(f"❌ OpenAI batch failure details: {batch_info['errors']}")
            msg = (
                f"Batch {batch_id} is {batch_status} (batch_num={batch_num}). "
                "Result download skipped; task must fail so the run is visible as failed."
            )
            logger.error(f"❌ {msg}")
            raise BatchFailedError(msg)

        # 1. 결과 다운로드
        results_file = self.openai.download_batch_results(batch_id)
        if not results_file:
            raise Exception(f"Failed to download batch results: {batch_id}")
        
        # 2. 결과 파싱
        parse_result = self.openai.parse_batch_results(results_file)
        summaries = parse_result['summaries']
        parsing_success = parse_result['parsing_success']
        parsing_failed = parse_result['parsing_failed']
        parsing_errors = parse_result['errors']
        token_usage = parse_result.get('token_usage', {})
        
        logger.info(
            f"📊 파싱 결과: 성공 {parsing_success}개, 실패 {parsing_failed}개, "
            f"저장 대상 {len(summaries)}개"
        )
        
        # 3. 저장 처리
        save_result = self._save_summaries(
            summaries=summaries,
            batch_num=batch_num,
            batch_id=batch_id
        )
        
        # 4. 통계 집계
        total_failed = parsing_failed + save_result['failed_count']
        
        error_messages = []
        if parsing_failed > 0:
            error_messages.append(f"파싱 실패: {parsing_failed}개")
        if save_result['failed_count'] > 0:
            error_messages.append(f"저장 실패: {save_result['failed_count']}개")

        error_message = "; ".join(error_messages) if error_messages else None
        error_details = None
        if parsing_errors or save_result['failed_count'] > 0:
            error_details = {
                'parsing_errors': parsing_errors[:10],  # 최대 10개만 저장
                'parsing_failed_count': parsing_failed,
                'storage_failed_count': save_result['failed_count'],
                'total_failed': total_failed
            }
        
        logger.info(
            f"✅ Processing completed: "
            f"parsing_success={parsing_success}, "
            f"parsing_failed={parsing_failed}, "
            f"saved={save_result['success_count']}, "
            f"skipped={save_result['skipped_count']}, "
            f"storage_failed={save_result['failed_count']}, "
            f"total_failed={total_failed}"
        )
        
        # 파싱 실패 항목의 raw_id 추출 (재제출용)
        failed_raw_ids = [
            self._parse_custom_id(e['custom_id'])
            for e in parsing_errors
            if e.get('custom_id')
        ]
        failed_raw_ids = [rid for rid in failed_raw_ids if rid]

        return {
            'success_count': save_result['success_count'],
            'failed_count': total_failed,
            'skipped_count': save_result['skipped_count'],
            'parsing_success': parsing_success,
            'parsing_failed': parsing_failed,
            'parsing_errors': parsing_errors,
            'failed_raw_ids': failed_raw_ids,
            'error_message': error_message,
            'error_details': error_details,
            'token_usage': token_usage,
        }
    
    def _save_summaries(
        self,
        summaries: Dict[str, Dict[str, Any]],
        batch_num: int,
        batch_id: str
    ) -> Dict[str, int]:
        """
        요약 데이터 저장
        """
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        logger.info(f"🔄 Starting to save {len(summaries)} summaries to processed_summary table...")

        # OpenAI가 처리해서 돌려준 모든 raw_id 목록
        all_raw_ids = [
            self._parse_custom_id(cid)
            for cid in summaries.keys()
        ]
        all_raw_ids = [rid for rid in all_raw_ids if rid] # None 필터링

        # all_raw_ids에서 processed_summary 테이블에 저장되어 있는 것들 (Set)
        existing_raw_ids = self.db.get_existing_raw_ids_sync(all_raw_ids)
        if existing_raw_ids:
            logger.info(f"⏭️ {len(existing_raw_ids)} raw_ids already processed, will skip")

        for idx, (custom_id, summary_data) in enumerate(summaries.items(), 1):
            try:
                # custom_id 파싱
                raw_id = self._parse_custom_id(custom_id)
                if not raw_id:
                    error_count += 1
                    continue
                
                # 요약 텍스트 추출
                summary_text = self._extract_summary_text(summary_data)
                
                # 중복 확인 (메모리 Set 조회, DB 쿼리 없음)
                if raw_id in existing_raw_ids:
                    logger.debug(f"⏭️ Skipping duplicate: raw_id={raw_id} already exists")
                    skipped_count += 1
                    continue
                
                # 저장
                processed_id = self.db.save_processed_summary_sync(
                    raw_id=raw_id,
                    summary=summary_text,
                    batch_num=batch_num,
                    model_id=self.openai.model,
                    summary_data=summary_data if isinstance(summary_data, dict) else {'summary': summary_text}
                )
                
                if processed_id:
                    if (idx % 10 == 0) or (idx == len(summaries)):
                        logger.info(f"✅ Progress: {idx}/{len(summaries)} saved (raw_id={raw_id})")
                    else:
                        logger.debug(f"✅ Summary saved: raw_id={raw_id}, processed_id={processed_id}")
                    success_count += 1
                else:
                    logger.warning(f"⚠️ Failed to save summary: raw_id={raw_id}")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Failed to save summary ({custom_id}): {e}", exc_info=True)
                error_count += 1
        
        return {
            'success_count': success_count,
            'failed_count': error_count,
            'skipped_count': skipped_count
        }
    
    def _parse_custom_id(self, custom_id: str) -> Optional[str]:
        """
        custom_id에서 raw_id 추출
        """
        parts = custom_id.split('_')
        if len(parts) < 4:
            logger.warning(f"⚠️ Invalid custom_id: {custom_id}")
            return None
        return parts[3]  # UUID 문자열
    
    def _extract_summary_text(self, summary_data: Any) -> str:
        """
        summary_data에서 요약 텍스트 추출
        """
        if isinstance(summary_data, dict):
            return summary_data.get('summary') or \
                summary_data.get('summary_text') or \
                summary_data.get('content') or \
                str(summary_data)
        elif isinstance(summary_data, str):
            return summary_data
        else:
            return str(summary_data)
    
