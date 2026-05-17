"""
embedding_service.py 단위 테스트

test-guide 원칙 적용:
1. 행동 중심 테스트 - 임베딩 벡터가 올바르게 반환되는지 검증
2. 외부 의존성 Mock - HuggingFace API, requests 모듈 Mock
3. 핵심 로직만 테스트 - 성공/실패 대표 케이스
"""

import pytest
import os
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from services.embedding_service import EmbeddingService


class TestEmbeddingService:
    """EmbeddingService 단위 테스트"""

    @pytest.fixture
    def service(self):
        """테스트용 EmbeddingService 인스턴스"""
        return EmbeddingService()

    @pytest.fixture
    def sample_track_data(self):
        """테스트용 샘플 트랙 데이터"""
        return {
            "album_title": "Kind of Blue",
            "album_artist": "Miles Davis",
            "album_year": "1959",
            "album_label": "Columbia",
            "review_summary": "A masterpiece of modal jazz",
            "content": "This album revolutionized jazz music with its modal approach..."
        }

    # ============================================
    # 1. initialize() 테스트
    # ============================================

    @patch.dict(os.environ, {"HF_TOKEN": "test-token"})
    @patch('services.embedding_service.InferenceClient')
    def test_initialize_성공(self, mock_client, service):
        """HF_TOKEN이 있을 때 초기화 성공"""
        # Given
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance

        # When
        asyncio.run(service.initialize())

        # Then
        assert service.client is not None
        mock_client.assert_called_once_with(token="test-token")

    @patch.dict(os.environ, {}, clear=True)
    def test_initialize_실패_토큰없음(self, service):
        """HF_TOKEN이 없을 때 초기화 실패"""
        # When
        asyncio.run(service.initialize())

        # Then
        assert service.client is None

    # ============================================
    # 2. get_embedding() 테스트 - 핵심 비즈니스 로직
    # ============================================

    @patch('requests.post')
    @patch.dict(os.environ, {"HF_TOKEN": "test-token"})
    def test_get_embedding_성공_리스트반환(self, mock_post, service, sample_track_data):
        """임베딩 생성 성공 - API가 리스트 반환"""
        # Given
        service.client = Mock()  # Client 설정
        mock_embedding = [[0.1, 0.2, 0.3, 0.4, 0.5]]  # 1024차원 대신 간단히
        mock_response = Mock()
        mock_response.json.return_value = mock_embedding
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # When
        result = asyncio.run(service.get_embedding(sample_track_data))

        # Then
        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert isinstance(result, list)
        assert len(result) > 0

        # API 호출 검증
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        # 첫 번째 위치 인자가 URL
        assert "intfloat/multilingual-e5-large" in call_args.args[0]
        # json 파라미터 검증
        assert call_args.kwargs['json']['inputs'].startswith("query: ")

    def test_get_embedding_실패_클라이언트없음(self, service, sample_track_data):
        """Client가 없을 때 None 반환"""
        # Given
        service.client = None

        # When
        result = asyncio.run(service.get_embedding(sample_track_data))

        # Then
        assert result is None

    @patch('requests.post')
    @patch.dict(os.environ, {"HF_TOKEN": "test-token"})
    def test_get_embedding_실패_API에러(self, mock_post, service, sample_track_data):
        """API 호출 실패 시 None 반환 (예외 처리 대표 케이스)"""
        # Given
        service.client = Mock()
        mock_post.side_effect = Exception("API Error")

        # When
        result = asyncio.run(service.get_embedding(sample_track_data))

        # Then
        assert result is None

    # ============================================
    # 3. get_embeddings_batch() 테스트
    # ============================================

    def test_get_embeddings_batch_성공(self, service, sample_track_data):
        """배치 임베딩 생성 성공"""
        # Given
        service.client = Mock()
        mock_results = [
            Mock(tolist=Mock(return_value=[0.1, 0.2, 0.3])),
            Mock(tolist=Mock(return_value=[0.4, 0.5, 0.6]))
        ]
        service.client.feature_extraction = Mock(return_value=mock_results)

        track_data_list = [sample_track_data, sample_track_data]

        # When
        results = asyncio.run(service.get_embeddings_batch(track_data_list))

        # Then
        assert len(results) == 2
        assert results[0] == [0.1, 0.2, 0.3]
        assert results[1] == [0.4, 0.5, 0.6]

    def test_get_embeddings_batch_실패_클라이언트없음(self, service, sample_track_data):
        """Client가 없을 때 None 리스트 반환"""
        # Given
        service.client = None
        track_data_list = [sample_track_data, sample_track_data]

        # When
        results = asyncio.run(service.get_embeddings_batch(track_data_list))

        # Then
        assert len(results) == 2
        assert all(r is None for r in results)

    # ============================================
    # 4. _create_text() 테스트 - 텍스트 생성 로직
    # ============================================

    def test_create_text_모든필드포함(self, service, sample_track_data):
        """모든 필드가 있을 때 텍스트 생성"""
        # When
        text = service._create_text(sample_track_data)

        # Then
        assert "앨범 제목: Kind of Blue" in text
        assert "아티스트: Miles Davis" in text
        assert "발매년도: 1959" in text
        assert "레이블: Columbia" in text
        assert "리뷰 요약: A masterpiece of modal jazz" in text
        assert "리뷰 내용:" in text

    def test_create_text_일부필드만있음(self, service):
        """일부 필드만 있을 때도 텍스트 생성"""
        # Given
        partial_data = {
            "album_title": "Blue Train",
            "album_artist": "John Coltrane"
        }

        # When
        text = service._create_text(partial_data)

        # Then
        assert "앨범 제목: Blue Train" in text
        assert "아티스트: John Coltrane" in text
        assert text.count(":") == 2  # 2개 필드만

    def test_create_text_빈데이터(self, service):
        """빈 데이터일 때 빈 문자열 반환"""
        # When
        text = service._create_text({})

        # Then
        assert text == ""

    # ============================================
    # 5. 실패 데이터 관리 테스트
    # ============================================

    def test_get_failed_data_count(self, service):
        """실패 데이터 개수 반환"""
        # Given
        service.failed_data = [{"test": 1}, {"test": 2}]

        # When
        count = service.get_failed_data_count()

        # Then
        assert count == 2

    @patch('builtins.open', create=True)
    @patch('pickle.dump')
    def test_save_failed_data_임베딩있음(self, mock_pickle_dump, mock_open, service, sample_track_data):
        """임베딩이 있을 때만 실패 데이터 저장"""
        # Given
        embedding = [0.1, 0.2, 0.3]
        error_msg = "Test error"

        # When
        service._save_failed_data(sample_track_data, error_msg, embedding)

        # Then
        assert len(service.failed_data) == 1
        assert service.failed_data[0]['embedding'] == embedding
        assert service.failed_data[0]['error_message'] == error_msg

    def test_save_failed_data_임베딩없음(self, service, sample_track_data):
        """임베딩이 없으면 저장하지 않음"""
        # Given
        error_msg = "Test error"

        # When
        service._save_failed_data(sample_track_data, error_msg, embedding=None)

        # Then
        assert len(service.failed_data) == 0


# ============================================
# 통합 시나리오 테스트 (Optional)
# ============================================

class TestEmbeddingServiceIntegration:
    """실제 사용 시나리오 테스트"""

    @patch('requests.post')
    @patch.dict(os.environ, {"HF_TOKEN": "test-token"})
    @patch('services.embedding_service.InferenceClient')
    def test_전체플로우_초기화부터임베딩생성까지(self, mock_client, mock_post):
        """초기화 → 임베딩 생성 전체 플로우"""
        # Given
        service = EmbeddingService()
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance

        mock_embedding = [[0.1, 0.2, 0.3]]
        mock_response = Mock()
        mock_response.json.return_value = mock_embedding
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        track_data = {
            "album_title": "Test Album",
            "album_artist": "Test Artist"
        }

        # When
        asyncio.run(service.initialize())
        result = asyncio.run(service.get_embedding(track_data))

        # Then
        assert service.client is not None
        assert result == [0.1, 0.2, 0.3]
