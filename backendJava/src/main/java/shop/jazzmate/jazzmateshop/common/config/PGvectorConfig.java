package shop.jazzmate.jazzmateshop.common.config;

import com.pgvector.PGvector;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;

@Configuration
public class PGvectorConfig {

    // PGvector 타입을 PostgreSQL 드라이버에 등록한다.
    // 이 설정 없이는 Hibernate가 vector 컬럼을 읽을 때 타입을 인식하지 못한다.
    @Bean
    public boolean registerPGvector(DataSource dataSource) throws SQLException {
        try (Connection conn = dataSource.getConnection()) {
            PGvector.addVectorType(conn);
        }
        return true;
    }
}
