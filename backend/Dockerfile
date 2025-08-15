# Java 백엔드용 Dockerfile
FROM openjdk:17-jdk-slim

# 작업 디렉토리 설정
WORKDIR /app

# curl 설치
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Gradle Wrapper 디렉토리 생성 및 파일 다운로드
RUN mkdir -p gradle/wrapper
RUN curl -L https://github.com/gradle/gradle/raw/v7.6.3/gradle/wrapper/gradle-wrapper.jar -o gradle/wrapper/gradle-wrapper.jar
RUN curl -L https://github.com/gradle/gradle/raw/v7.6.3/gradle/wrapper/gradle-wrapper.properties -o gradle/wrapper/gradle-wrapper.properties

# Gradle Wrapper와 설정 파일들 복사
COPY gradlew .
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

