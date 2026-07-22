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
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]