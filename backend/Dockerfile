# Java 백엔드용 Dockerfile
FROM openjdk:17-jdk-slim

# 작업 디렉토리 설정
WORKDIR /app

# Gradle Wrapper와 설정 파일들 복사
COPY gradlew .
COPY gradle gradle
COPY build.gradle .
COPY settings.gradle .

# 소스 코드 복사
COPY src src

# Gradle 빌드 실행
RUN ./gradlew build -x test

# 포트 노출
EXPOSE 8080

# 애플리케이션 실행
CMD ["./gradlew", "bootRun"]

