package br.unesp.sadcnr.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.servers.Server;
import io.swagger.v3.oas.models.tags.Tag;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI sadCnrOpenApi() {
        return new OpenAPI()
                .info(new Info()
                        .title("SAD Consultório na Rua — API")
                        .description("""
                                API do Sistema de Apoio à Decisão (Fase 1).

                                Inclui:
                                - Predições territoriais (heatmap / zonas de calor)
                                - Gateway para o microserviço de importação de CSV municipal
                                - Consultas auxiliares de pacientes

                                Microserviço de importação (OpenAPI nativo): http://localhost:8090/docs
                                """)
                        .version("0.1.0")
                        .contact(new Contact()
                                .name("Ever Santoro — UNESP/PPGEP")
                                .url("https://github.com/eversantoro/doutorado-fase1"))
                        .license(new License()
                                .name("Uso acadêmico")
                                .url("https://github.com/eversantoro/doutorado-fase1")))
                .servers(List.of(
                        new Server().url("http://localhost:8081").description("SAD local")))
                .tags(List.of(
                        new Tag().name("Predições").description("Heatmap e zonas geradas pela IA"),
                        new Tag().name("Importação").description("Proxy para o microserviço de importação CSV"),
                        new Tag().name("Pacientes").description("Consultas e upload legado")));
    }
}
