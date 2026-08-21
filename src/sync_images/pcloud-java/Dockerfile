# Stage 1: Build
FROM eclipse-temurin:17-jdk AS build
WORKDIR /app
COPY gradlew settings.gradle ./
COPY gradle ./gradle
COPY app ./app
RUN chmod +x gradlew && ./gradlew :app:bootJar --no-daemon

# Stage 2: Run
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /app/app/build/libs/*.jar app.jar

ADD https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar /app/opentelemetry-javaagent.jar
RUN chmod 644 /app/opentelemetry-javaagent.jar

USER 1000:1000

ENV OTEL_SERVICE_NAME=java-api
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

EXPOSE 8080
ENTRYPOINT ["java", "-javaagent:/app/opentelemetry-javaagent.jar", "-jar", "app.jar"]
