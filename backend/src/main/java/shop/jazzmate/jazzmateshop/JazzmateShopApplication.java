package shop.jazzmate.jazzmateshop;

import io.github.cdimascio.dotenv.Dotenv;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
@SpringBootApplication
public class JazzmateShopApplication {

    public static void main(String[] args) {
        Dotenv dotenv = Dotenv.load();
        String SERVER_PORT = dotenv.get("SERVER_PORT");
        String DB_USERNAME = dotenv.get("DB_USERNAME");
        String DB_PASSWORD = dotenv.get("DB_PASSWORD");
        String DB_DRIVER = dotenv.get("DB_DRIVER");
        String DB_URL = dotenv.get("DB_URL");

        // 시스템 프로퍼티로 설정
        System.setProperty("server.port", SERVER_PORT != null ? SERVER_PORT : "8080");
        System.setProperty("spring.datasource.username", DB_USERNAME != null ? DB_USERNAME : "postgres");
        System.setProperty("spring.datasource.password", DB_PASSWORD != null ? DB_PASSWORD : "");
        System.setProperty("spring.datasource.driver-class-name", DB_DRIVER != null ? DB_DRIVER : "org.postgresql.Driver");
        System.setProperty("spring.datasource.url", DB_URL != null ? DB_URL : "jdbc:postgresql://localhost:5432/postgres");


        SpringApplication.run(JazzmateShopApplication.class, args);
    }

}
