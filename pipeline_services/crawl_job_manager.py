import asyncio
import logging
from typing import Dict

from dags.crawling.services.resource_monitor import ResourceMonitor
from dags.crawling.core.config import ResourceThresholds
from pipeline_services.exceptions import (
    RetryableError,
    PermanentError,
    NetworkError,
)

logger = logging.getLogger(__name__)

class CrawlJobManager:
    def __init__(self, superbase_service):
        self.db = superbase_service
        
    async def process_crawl_jobs(
        self,
        batch_id: str,
        batch_num: int,
    ) -> Dict[str, int]:
        """크롤러 초기화 → pending 작업 처리 → 크롤러 종료"""
        from pipeline_services.review_crawler_service import ReviewCrawlerService

        review_crawler = ReviewCrawlerService()
        await review_crawler.initialize()
        resource_monitor = ResourceMonitor(thresholds=ResourceThresholds.default())
        try:
            # 크롤링할 url 조회
            pending_jobs = self.db.get_pending_jobs(batch_id)

            if not pending_jobs:
                logger.info("✅ No pending jobs found")
                return {'success_count': 0, 'failed_count': 0}

            logger.info(f"🔄 Processing {len(pending_jobs)} pending jobs (batch_id={batch_id})")

            success_count = 0
            failed_count = 0

            for job in pending_jobs:
                try:
                    result = await self._process_one_job(
                        job=job,
                        batch_id=batch_id,
                        batch_num=batch_num,
                        review_crawler=review_crawler,
                        resource_monitor=resource_monitor,
                    )

                    if result == 'success':
                        success_count += 1
                    elif result == 'failed':
                        failed_count += 1

                except RetryableError:
                    # ✅ 재시도 가능한 에러 → Airflow가 재시도하도록 재전파
                    raise
                except Exception as e:
                    # DNS 에러는 재시도 가능 → Airflow가 재시도하도록 재전파
                    if self._is_dns_error(e):
                        url = job.get('url', '')
                        logger.error(f"❌ DNS failure: {url[:60]} - {e}")
                        raise NetworkError(f"DNS failure: {e}") from e
                    # 예상치 못한 에러 → 영구 실패로 간주하고 다음으로 진행
                    url = job['url']
                    logger.error(f"❌ Error processing {url[:60]}: {e}")
                    self._record_failed_job(
                        batch_id=batch_id,
                        batch_num=batch_num,
                        crawl_job_id=job['id'],
                        error_type='crawl_error',
                        error_message=str(e),
                    )
                    failed_count += 1

            logger.info(f"✅ Processing completed: success={success_count}, failed={failed_count}")

            return {
                'success_count': success_count,
                'failed_count': failed_count
            }
        finally:
            await review_crawler.close()

    async def _process_one_job(
        self,
        *,
        job: Dict,
        batch_id: str,
        batch_num: int,
        review_crawler,
        resource_monitor: ResourceMonitor,
    ) -> str:
        """단일 crawl_job 처리. 반환값: success 또는 failed."""
        from datetime import datetime
        from dags.crawling.utils.validation import validate_review_data, is_data_complete

        resource_info = resource_monitor.check_resources()

        if resource_info.status == 'critical':
            resource_monitor.log_resource_info(resource_info, batch_num)
            logger.warning(
                f"Memory critical ({resource_info.memory_percent:.1f}%) — "
                f"pausing {resource_info.recommended_wait}s before crawl"
            )
            await asyncio.sleep(resource_info.recommended_wait)
            raise RetryableError(
                f"Memory critical ({resource_info.memory_percent:.1f}%) — task will retry"
            )
        elif resource_info.status == 'high':
            resource_monitor.log_resource_info(resource_info, batch_num)
            logger.warning(f"Memory high ({resource_info.memory_percent:.1f}%) — proceeding with caution")

        crawl_job_id = job['id']
        url = job['url']

        # raw 테이블에 있으면 상태값 success로 싱크 맞추기
        if job.get('has_raw'):
            logger.info(f"⏭️ allthatjazz_raw에 이미 존재, success로 보정: {url[:60]}")
            self.db.update_crawl_job_status(crawl_job_id, 'success')
            return 'success'

        # 상태: pending → running
        self.db.update_crawl_job_status(crawl_job_id, 'running')

        # 크롤링 실행 (원본 HTML 포함)
        original_html = None
        try:
            # 크롤링 실행 (튜플 반환: review_data, original_html)
            review_data, original_html = await review_crawler.crawl_review_details(url)
        except RetryableError as e:
            # ✅ 재시도 가능한 에러 → Airflow가 재시도하도록 재전파
            logger.warning(f"⚠️ Retryable error for {url[:60]}: {e}")
            raise
        except PermanentError as e:
            # ✅ 영구 실패 → error_history에 기록하고 다음으로 진행
            self._record_failed_job(
                batch_id=batch_id,
                batch_num=batch_num,
                crawl_job_id=crawl_job_id,
                error_type='permanent_error',
                error_message=str(e),
                original_html=original_html,
            )
            logger.error(f"❌ Permanent error: {url[:60]} - {e}")
            return 'failed'

        if not review_data:
            
            self._record_failed_job(
                batch_id=batch_id,
                batch_num=batch_num,
                crawl_job_id=crawl_job_id,
                error_type='parse_error',
                error_message='Review content extraction failed',
                original_html=original_html,
            )
            return 'failed'

        # 원본 HTML 저장
        html_path = None
        if original_html:
            html_path = self.db.save_original_html(original_html, batch_num, crawl_job_id)

        # crawled_at 추가
        review_data['crawled_at'] = datetime.now().isoformat()

        # date 필드를 published_date_raw로 매핑
        if 'date' in review_data and not review_data.get('published_date_raw'):
            date_value = review_data.pop('date', '')
            review_data['published_date_raw'] = date_value
        elif 'date' not in review_data:
            review_data['published_date_raw'] = ''

        # published_date 파싱
        if review_data.get('published_date_raw') and review_data['published_date_raw'].strip():
            from dags.crawling.utils.date_parser import parse_date
            parsed_date = parse_date(review_data['published_date_raw'])
            review_data['published_date'] = parsed_date if parsed_date else ''
        else:
            review_data['published_date'] = ''

        # Validation
        is_valid, missing_fields, error_msg = validate_review_data(review_data)

        if not is_valid:
            # Validation 실패 → error_history에 기록
            self._record_failed_job(
                batch_id=batch_id,
                batch_num=batch_num,
                crawl_job_id=crawl_job_id,
                error_type='validation_error',
                error_message=f'Validation failed: {error_msg}',
                error_details={'missing_fields': missing_fields},
                html_path=html_path,
            )
            logger.warning(f"⚠️ Validation failed: {url[:60]} - {error_msg}")
            return 'failed'

        # 데이터 완성도 체크
        review_data['is_fully_complete'] = is_data_complete(review_data)

        review_data['crawl_job_id'] = crawl_job_id
        review_data['s3_original_html_path'] = html_path

        # url, batch_num 제거
        review_data.pop('url', None)
        review_data.pop('batch_num', None)

        try:
            response = self.db.client.table('allthatjazz_raw')\
                .insert(review_data)\
                .execute()

            if response.data:
                self.db.update_crawl_job_status(crawl_job_id, 'success')

                if review_data['is_fully_complete']:
                    logger.info(f"✅ Saved (complete): {review_data.get('title', 'Unknown')[:50]}")
                else:
                    logger.info(f"✅ Saved (incomplete): {review_data.get('title', 'Unknown')[:50]}")
                return 'success'

            self._record_failed_job(
                batch_id=batch_id,
                batch_num=batch_num,
                crawl_job_id=crawl_job_id,
                error_type='db_save_error',
                error_message='DB save returned no data',
                html_path=html_path,
            )
            logger.error(f"❌ DB save returned no data: {url[:60]}")
            return 'failed'
        except Exception as e:
            if self._is_dns_error(e):
                # DNS 해석 실패 → 일시적 네트워크 장애, Airflow가 재시도하도록 재전파
                logger.error(f"❌ DNS failure during DB save: {url[:60]} - {e}")
                raise NetworkError(f"DNS failure during DB save: {e}") from e

            # DB 저장 실패
            self._record_failed_job(
                batch_id=batch_id,
                batch_num=batch_num,
                crawl_job_id=crawl_job_id,
                error_type='db_save_error',
                error_message=f'DB save failed: {str(e)}',
                html_path=html_path,
            )
            logger.error(f"❌ DB save failed: {url[:60]} - {e}")
            return 'failed'


    def _record_failed_job(
        self,
        *,
        batch_id: str,
        batch_num: int,
        crawl_job_id: str,
        error_type: str,
        error_message: str,
        original_html: str | None = None,
        html_path: str | None = None,
        error_details: Dict | None = None,
    ) -> None:
        if original_html and not html_path:
            html_path = self.db.save_original_html(original_html, batch_num, crawl_job_id)

        self.db.save_error_history(
            stage='crawl',
            batch_id=batch_id,
            crawl_job_id=crawl_job_id,
            error_type=error_type,
            error_message=error_message,
            error_details=error_details,
            s3_original_html_path=html_path,
        )
        self.db.update_crawl_job_status(crawl_job_id, 'failed')

    def _is_dns_error(self, error: Exception) -> bool:
        error_message = str(error).lower()
        return (
            'name or service not known' in error_message
            or 'temporary failure in name resolution' in error_message
            or 'nodename nor servname provided' in error_message
            or 'failed to resolve' in error_message
            or 'dns' in error_message
        )
