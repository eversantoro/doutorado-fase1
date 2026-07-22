package br.unesp.sadcnr.application;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.Map;

@Service
public class ImportacaoGatewayService {

    private final RestTemplate restTemplate = new RestTemplate();
    private final String importServiceUrl;

    public ImportacaoGatewayService(
            @Value("${import.service.url:http://localhost:8090}") String importServiceUrl) {
        this.importServiceUrl = importServiceUrl.replaceAll("/$", "");
    }

    public Map<String, Object> health() {
        return getJson("/health");
    }

    public Map<String, Object> schema() {
        return getJson("/api/v1/import/schema");
    }

    public byte[] templatePacientes() {
        ResponseEntity<byte[]> response = restTemplate.getForEntity(
                importServiceUrl + "/api/v1/import/template/pacientes", byte[].class);
        return response.getBody() != null ? response.getBody() : new byte[0];
    }

    public Map<String, Object> importarPacientes(MultipartFile file, String modo, boolean strict)
            throws IOException {
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new NamedByteArrayResource(file.getBytes(), file.getOriginalFilename()));
        body.add("modo", modo);
        body.add("strict", String.valueOf(strict));

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        try {
            ResponseEntity<Map> response = restTemplate.exchange(
                    importServiceUrl + "/api/v1/import/pacientes",
                    HttpMethod.POST,
                    new HttpEntity<>(body, headers),
                    Map.class);
            @SuppressWarnings("unchecked")
            Map<String, Object> payload = response.getBody();
            return payload != null ? payload : Map.of("status", "vazio");
        } catch (HttpStatusCodeException ex) {
            throw new IllegalArgumentException(extrairErro(ex));
        } catch (RestClientException ex) {
            throw new IllegalStateException(
                    "Microservico de importacao indisponivel em " + importServiceUrl + ": " + ex.getMessage(),
                    ex);
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> getJson(String path) {
        try {
            ResponseEntity<Map> response = restTemplate.getForEntity(importServiceUrl + path, Map.class);
            return response.getBody() != null ? response.getBody() : Map.of();
        } catch (RestClientException ex) {
            throw new IllegalStateException(
                    "Microservico de importacao indisponivel em " + importServiceUrl, ex);
        }
    }

    private static String extrairErro(HttpStatusCodeException ex) {
        String body = ex.getResponseBodyAsString();
        if (body == null || body.isBlank()) {
            return "Falha na importacao: HTTP " + ex.getStatusCode().value();
        }
        return body;
    }

    private static final class NamedByteArrayResource extends ByteArrayResource {
        private final String filename;

        private NamedByteArrayResource(byte[] byteArray, String filename) {
            super(byteArray);
            this.filename = filename != null ? filename : "upload.csv";
        }

        @Override
        public String getFilename() {
            return filename;
        }
    }
}
