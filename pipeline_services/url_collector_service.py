
from typing import TYPE_CHECKING, List, Set
import logging

if TYPE_CHECKING:
    from .supabase_service import SupabaseService

logger = logging.getLogger(__name__)


class URLCollectorService:
    def __init__(self, supabase_service: 'SupabaseService'):
        self.db = supabase_service

    async def collect_review_urls(
        self,
        start_page: int,
        end_page: int,
    ) -> List[str]:
        from dags.crawling.crawlers.playwright_crawler import PlaywrightJazzCrawler
        from dags.crawling.core.config import CrawlerConfig

        logger.info(f"🚀 Starting URL collection: {start_page} ~ {end_page}")

        crawler_config = CrawlerConfig.from_env()
        crawler = PlaywrightJazzCrawler(crawler_config=crawler_config)

        try:
            await crawler.start()
            logger.info("✅ Playwright crawler started")

            all_review_urls = await crawler.collect_links_in_single_tab(
                start_page=start_page,
                end_page=end_page
            )

            logger.info(f"📋 Total {len(all_review_urls)} URLs collected")

            unique_urls = list(dict.fromkeys(all_review_urls))
            logger.info(f"🔍 After deduplication: {len(unique_urls)} unique URLs")

            # crawl_targets에 이미 있는 URL은 크롤링 대상에서 제외
            if unique_urls:
                existing_urls: Set[str] = self.db.get_successful_crawl_target_urls(unique_urls)
                if existing_urls:
                    unique_urls = [u for u in unique_urls if u not in existing_urls]
                    logger.info(f"⏭️ crawl_targets 기존 제외: {len(existing_urls)}개 → 신규 대상 {len(unique_urls)}개")

            return unique_urls

        finally:
            await crawler.close()
            logger.info("✅ Playwright crawler closed")
