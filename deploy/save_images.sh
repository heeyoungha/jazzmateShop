#!/bin/bash

# 운영서버용 Docker 이미지를 빌드하고 tar 파일로 저장하는 스크립트
# 사용법: ./deploy/save_images.sh

set -e

# 스크립트가 있는 디렉토리 (deploy 폴더)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 프로젝트 루트 디렉토리
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

echo "🐳 JazzMate Shop 운영서버용 도커 이미지 빌드 및 저장을 시작합니다..."

# 저장할 디렉토리 생성 (프로젝트 루트)
mkdir -p "$PROJECT_ROOT/docker_images_backup"

# 현재 날짜로 백업 파일명 생성
OUTPUT_FILE="$PROJECT_ROOT/docker_images_backup/jazzmateshop_images_$(date +%Y%m%d_%H%M%S).tar"

echo "📦 출력 파일: $OUTPUT_FILE"
echo ""

# docker-compose로 모든 이미지 빌드 및 nginx 다운로드
echo "🔨 모든 이미지 빌드 중..."
docker-compose -f docker-compose.prod.yml build

if [ $? -ne 0 ]; then
    echo "❌ 이미지 빌드 실패"
    exit 1
fi

echo "📥 nginx 이미지 다운로드 중..."
docker-compose -f docker-compose.prod.yml pull nginx

if [ $? -ne 0 ]; then
    echo "❌ nginx 이미지 다운로드 실패"
    exit 1
fi

echo "✅ 모든 이미지 준비 완료"
echo ""

# docker-compose 파일에서 이미지 이름 목록 추출
IMAGES=$(docker-compose -f docker-compose.prod.yml config --images | tr '\n' ' ')

# 모든 이미지를 하나의 tar 파일로 저장
echo "💾 이미지를 tar 파일로 저장 중..."
docker save $IMAGES -o "$OUTPUT_FILE"

FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
echo ""
echo "✅ 성공적으로 저장됨: $OUTPUT_FILE"
echo "📊 파일 크기: $FILE_SIZE"
echo ""
echo "🔄 이미지 복원 방법:"
echo "   docker load -i $OUTPUT_FILE"

