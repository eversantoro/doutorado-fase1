package br.unesp.sadcnr.application;

import br.unesp.sadcnr.domain.PacientePSR;
import br.unesp.sadcnr.infrastructure.persistence.PacientePSRRepository;
import com.opencsv.CSVReaderHeaderAware;
import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.PrecisionModel;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Service
public class PacienteIngestaoService {

    private static final int SRID = 4326;
    private final PacientePSRRepository repository;
    private final GeometryFactory geometryFactory = new GeometryFactory(new PrecisionModel(), SRID);

    public PacienteIngestaoService(PacientePSRRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public int importarCsv(MultipartFile file, boolean limparAntes) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("Arquivo CSV vazio ou ausente.");
        }

        if (limparAntes) {
            repository.truncatePacientes();
        }

        List<PacientePSR> lote = new ArrayList<>();
        try (CSVReaderHeaderAware reader = new CSVReaderHeaderAware(
                new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {

            Map<String, String> row;
            while ((row = reader.readMap()) != null) {
                lote.add(mapearLinha(row));
            }
        } catch (Exception e) {
            throw new IllegalArgumentException("Falha ao processar CSV: " + e.getMessage(), e);
        }

        repository.saveAll(lote);
        return lote.size();
    }

    private PacientePSR mapearLinha(Map<String, String> row) {
        double longitude = parseDouble(row, "longitude", "lon", "lng");
        double latitude = parseDouble(row, "latitude", "lat");
        short vulnerabilidade = parseShort(row, "nivel_vulnerabilidade", "vulnerabilidade", "intensidade");

        if (vulnerabilidade < 1 || vulnerabilidade > 5) {
            throw new IllegalArgumentException("nivel_vulnerabilidade deve estar entre 1 e 5.");
        }

        PacientePSR p = new PacientePSR();
        p.setIdAnonimizado(firstNonBlank(row, "id_anonimizado", "id"));
        p.setSexo(firstNonBlank(row, "sexo"));
        p.setFaixaEtaria(firstNonBlank(row, "faixa_etaria"));
        p.setNivelVulnerabilidade(vulnerabilidade);
        p.setGeom(geometryFactory.createPoint(new Coordinate(longitude, latitude)));
        return p;
    }

    private static double parseDouble(Map<String, String> row, String... keys) {
        String raw = firstNonBlank(row, keys);
        if (raw == null) {
            throw new IllegalArgumentException("Coluna de coordenada ausente: " + String.join("/", keys));
        }
        return Double.parseDouble(raw.trim().replace(',', '.'));
    }

    private static short parseShort(Map<String, String> row, String... keys) {
        String raw = firstNonBlank(row, keys);
        if (raw == null) {
            return 3;
        }
        return Short.parseShort(raw.trim());
    }

    private static String firstNonBlank(Map<String, String> row, String... keys) {
        for (String key : keys) {
            for (Map.Entry<String, String> e : row.entrySet()) {
                if (e.getKey() != null && e.getKey().equalsIgnoreCase(key)) {
                    String v = e.getValue();
                    if (v != null && !v.isBlank()) {
                        return v.trim();
                    }
                }
            }
        }
        return null;
    }
}
