package br.unesp.sadcnr.api;

import br.unesp.sadcnr.application.HeatmapService;
import br.unesp.sadcnr.application.PacienteIngestaoService;
import br.unesp.sadcnr.infrastructure.persistence.PacientePSRRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@Tag(name = "Pacientes", description = "Consultas e upload legado (preferir /api/importacao para carga municipal)")
public class PacienteController {

    private final PacienteIngestaoService ingestaoService;
    private final HeatmapService heatmapService;
    private final PacientePSRRepository repository;

    public PacienteController(
            PacienteIngestaoService ingestaoService,
            HeatmapService heatmapService,
            PacientePSRRepository repository) {
        this.ingestaoService = ingestaoService;
        this.heatmapService = heatmapService;
        this.repository = repository;
    }

    @PostMapping(value = "/upload-csv", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @Operation(summary = "Upload CSV legado (direto no SAD)", deprecated = true)
    public ResponseEntity<Map<String, Object>> uploadCsv(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "limpar", defaultValue = "true") boolean limpar) {

        int importados = ingestaoService.importarCsv(file, limpar);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("mensagem", "Importação concluída");
        body.put("registros", importados);
        body.put("totalBanco", repository.count());
        return ResponseEntity.ok(body);
    }

    @GetMapping("/pacientes/heatmap")
    @Operation(summary = "Heatmap a partir da tabela de pacientes")
    public ResponseEntity<List<double[]>> heatmap() {
        return ResponseEntity.ok(heatmapService.pontosHeatmap());
    }

    @GetMapping("/pacientes/geojson")
    @Operation(summary = "GeoJSON dos pacientes")
    public ResponseEntity<Map<String, Object>> geoJson() {
        return ResponseEntity.ok(heatmapService.geoJson());
    }

    @GetMapping("/pacientes/count")
    @Operation(summary = "Contagem de pacientes no banco")
    public ResponseEntity<Map<String, Long>> count() {
        return ResponseEntity.ok(Map.of("total", repository.count()));
    }
}
