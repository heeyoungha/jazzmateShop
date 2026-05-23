"""
리뷰 크롤러 서비스

단일 리뷰 상세 페이지 크롤링만 담당합니다.
"""

from typing import Dict, Any, Optional, Tuple
import logging
from bs4 import BeautifulSoup
from pipeline_services.exceptions import (
    RetryableError,
    PermanentError,
    NetworkError,
    BlockedError,
    ParseError
)

logger = logging.getLogger(__name__)


class ReviewCrawlerService:
    """리뷰 크롤러 서비스 - 단일 리뷰 상세 크롤링"""

    def __init__(self):
        """ReviewCrawlerService 초기화"""
        self.crawler = None

    async def initialize(self):
        """크롤러 초기화"""
        from dags.crawling.crawlers.playwright_crawler import PlaywrightJazzCrawler
        from dags.crawling.core.config import CrawlerConfig

        # 중앙 설정 사용
        crawler_config = CrawlerConfig.from_env()
        self.crawler = PlaywrightJazzCrawler(crawler_config=crawler_config)
        await self.crawler.start()
        logger.info("✅ Playwright crawler started")

    async def close(self):
        """크롤러 종료"""
        if self.crawler:
            await self.crawler.close()
            logger.info("✅ Playwright crawler closed")

    async def crawl_review_details(self, url: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:

        if not self.crawler:
            raise RuntimeError("Crawler not initialized. Call initialize() first.")

        original_html = None
        try:
            logger.info(f"📖 Crawling: {url[:60]}...")

            # HTML 가져오기
            html = await self.crawler.fetch_html(url, referer=self.crawler.reviews_url)
            original_html = html  # 원본 HTML 저장

            if not html:
                # fetch_html이 None 반환 → 차단 또는 영구 실패
                logger.warning(f"⚠️ HTML fetch failed: {url[:60]}")
                return None, None

            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(html, 'html.parser')

            # 리뷰 상세 정보 추출
            review_data = self.crawler.extract_review_details(soup, url)

            if not review_data or not review_data.get('content'):
                logger.warning(f"⚠️ Content extraction failed: {url[:60]}")
                # 파싱 실패 → 영구 실패로 간주 (원본 HTML은 반환)
                return None, original_html

            return review_data, original_html

        except RetryableError as e:
            # ✅ 재시도 가능한 에러 → Airflow가 재시도하도록 재전파
            logger.warning(f"⚠️ Retryable error: {url[:60]} - {e}")
            raise
        except PermanentError as e:
            # ✅ 영구 실패 (ParseError, BlockedError, ValidationError 등) → (None, html) 반환
            logger.error(f"❌ Permanent error: {url[:60]} - {e}")
            return None, original_html
        except Exception as e:
            # ✅ 예상치 못한 에러 → 영구 실패로 간주 (재시도 안 함)
            # ParseError로 변환하여 PermanentError로 처리
            logger.error(f"❌ Unexpected error: {url[:60]} - {e}")
            raise ParseError(f"Unexpected error: {e}") from e

