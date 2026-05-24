package shop.jazzmate.jazzmateshop;

import com.tngtech.archunit.core.domain.JavaClass;
import com.tngtech.archunit.core.domain.JavaClasses;
import com.tngtech.archunit.core.domain.JavaField;
import com.tngtech.archunit.core.domain.JavaParameterizedType;
import com.tngtech.archunit.core.domain.JavaType;
import com.tngtech.archunit.core.importer.ClassFileImporter;
import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.lang.ArchCondition;
import com.tngtech.archunit.lang.ArchRule;
import com.tngtech.archunit.lang.ConditionEvents;
import com.tngtech.archunit.lang.SimpleConditionEvent;
import jakarta.persistence.Entity;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.net.http.HttpClient;
import java.util.List;

import static com.tngtech.archunit.base.DescribedPredicate.describe;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.classes;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.fields;
import static com.tngtech.archunit.lang.syntax.ArchRuleDefinition.noClasses;

class ArchitectureTest {

    private static final JavaClasses PRODUCTION_CLASSES = new ClassFileImporter()
            .withImportOption(new ImportOption.DoNotIncludeTests())
            .importPackages("shop.jazzmate.jazzmateshop");

    @Test
    @DisplayName("Entity는 Lombok @Data를 사용하지 않고 필요한 접근자만 노출한다")
    void entities_must_not_use_lombok_data() {
        ArchRule rule = classes()
                .that().areAnnotatedWith(Entity.class)
                .should().notBeAnnotatedWith("lombok.Data");

        rule.check(PRODUCTION_CLASSES);
    }

    @Test
    @DisplayName("Response DTO는 Entity 타입을 응답 필드로 직접 노출하지 않는다")
    void response_dtos_must_not_expose_entity_fields() {
        ArchRule rule = fields()
                .that().areDeclaredInClassesThat().resideInAPackage("..dto..")
                .and().areDeclaredInClassesThat().haveSimpleNameEndingWith("Response")
                .should(notExposeEntityType());

        rule.check(PRODUCTION_CLASSES);
    }

    @Test
    @DisplayName("Service는 저수준 HTTP 클라이언트에 직접 의존하지 않고 전용 Client 컴포넌트에 위임한다")
    void services_must_not_directly_depend_on_http_clients() {
        ArchRule rule = noClasses()
                .that().resideInAPackage("..")
                .and().haveSimpleNameEndingWith("Service")
                .should().dependOnClassesThat(describe("are low-level HTTP client types",
                        javaClass -> javaClass.isAssignableTo(HttpClient.class)
                                || javaClass.getName().equals("org.springframework.web.client.RestTemplate")
                                || javaClass.getName().equals("org.springframework.web.reactive.function.client.WebClient")));

        rule.check(PRODUCTION_CLASSES);
    }

    private static ArchCondition<JavaField> notExposeEntityType() {
        return new ArchCondition<>("not expose Entity types directly") {
            @Override
            public void check(JavaField field, ConditionEvents events) {
                List<JavaClass> entityTypes = entityTypesOf(field.getType());
                if (entityTypes.isEmpty()) {
                    return;
                }

                String message = "%s exposes Entity type(s): %s".formatted(
                        field.getFullName(),
                        entityTypes.stream().map(JavaClass::getName).toList()
                );
                events.add(SimpleConditionEvent.violated(field, message));
            }
        };
    }

    private static List<JavaClass> entityTypesOf(JavaType type) {
        if (type.toErasure().isAnnotatedWith(Entity.class)) {
            return List.of(type.toErasure());
        }

        if (type instanceof JavaParameterizedType parameterizedType) {
            return parameterizedType.getActualTypeArguments().stream()
                    .flatMap(argument -> entityTypesOf(argument).stream())
                    .toList();
        }

        return List.of();
    }
}
