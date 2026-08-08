#!/bin/bash
set -euo pipefail

# ── 배포 대상 ──
# 도메인 사용: IP는 인스턴스 재시작/무인 업데이트로 바뀔 수 있어 하드코딩하지 않는다.
REMOTE="ubuntu@actlog.shop"
PEM="jazzmateShop.pem"
TAR_FILE="jazzmate-images.tar"
REMOTE_DIR="/home/ubuntu"

# 운영서버로 보낼 compose 파일 (airflow는 마운트 없는 prod 버전 사용)
COMPOSE_MAIN="docker-compose.yml"                      # nginx, java-backend, ai-api
COMPOSE_AIRFLOW="deploy/docker-compose.airflow.prod.yaml"  # airflow (이미지의 코드/config 사용)

IMAGES=(
  "jazzmateshop-nginx"
  "jazzmateshop-java-backend"
  "jazzmateshop-ai-api"
  "jazzmateshop-airflow-standalone"
)

echo "=== 1. 이미지 빌드 ==="
# standalone.yaml에 build:가 있으므로 airflow도 image 이름(jazzmateshop-airflow-standalone:latest)으로 빌드된다.
# 로컬에서 테스트한 바로 이 이미지가 그대로 운영에 간다(dev/prod parity).
docker compose -f "$COMPOSE_MAIN" build
docker compose -f docker-compose.airflow.standalone.yaml build

echo "=== 2. 이미지 tar 생성 ==="
docker save "${IMAGES[@]}" -o "$TAR_FILE"
echo "$(du -h "$TAR_FILE" | cut -f1) 크기의 $TAR_FILE 생성 완료"

echo "=== 3. 서버로 전송 (이미지 + compose 파일) ==="
# 운영서버는 이미지 + compose만 둔다. prod compose는 deploy/ 경로를 유지해 전송.
ssh -i "$PEM" "$REMOTE" "mkdir -p $REMOTE_DIR/deploy"
scp -i "$PEM" "$TAR_FILE"        "$REMOTE:$REMOTE_DIR/"
scp -i "$PEM" "$COMPOSE_MAIN"    "$REMOTE:$REMOTE_DIR/"
scp -i "$PEM" "$COMPOSE_AIRFLOW" "$REMOTE:$REMOTE_DIR/deploy/"

echo "=== 4. 서버에서 이미지 로드 ==="
ssh -i "$PEM" "$REMOTE" "docker load -i $REMOTE_DIR/$TAR_FILE && rm $REMOTE_DIR/$TAR_FILE"

echo "=== 5. 런타임 폴더 권한 정리 ==="
# logs/data는 마운트되는 런타임 폴더다. root 소유로 남아 있으면 컨테이너의
# airflow 유저(UID 50000)가 쓰지 못해 Permission denied로 기동 실패한다.
ssh -i "$PEM" "$REMOTE" "sudo mkdir -p $REMOTE_DIR/logs $REMOTE_DIR/data && \
  sudo chown -R 50000:0 $REMOTE_DIR/logs $REMOTE_DIR/data"

echo "=== 6. 서버에서 컨테이너 재기동 ==="
# 새 이미지를 반영하려면 재생성이 필요하다(restart는 environment/이미지 변경을 반영하지 못함).
ssh -i "$PEM" "$REMOTE" "cd $REMOTE_DIR && \
  docker compose -f $COMPOSE_MAIN up -d && \
  docker compose -f $COMPOSE_AIRFLOW up -d"

echo "=== 7. 로컬 tar 정리 ==="
rm "$TAR_FILE"

echo "=== 배포 완료 ==="
echo "확인: ssh -i $PEM $REMOTE 'docker ps'"
