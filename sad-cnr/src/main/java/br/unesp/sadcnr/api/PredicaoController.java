package br.unesp.sadcnr.api;

import br.unesp.sadcnr.application.PredicaoHeatmapService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/predicoes")
@Tag(name = "Predições", description = "Endpoints de zonas de calor e scores da IA")
public class PredicaoController {

    private final PredicaoHeatmapService predicaoHeatmapService;

    public PredicaoController(PredicaoHeatmapService predicaoHeatmapService) {
        this.predicaoHeatmapService = predicaoHeatmapService;
    }

    @GetMapping("/heatmap")
    @Operation(
            summary = "Heatmap predito",
            description = "Retorna pontos no formato Leaflet.heat: [lat, lng, intensidade], "
                    + "usando probabilidade_ia (K-Means + KDE).")
    @ApiResponse(responseCode = "200", description = "Lista de pontos do heatmap")
    public ResponseEntity<List<double[]>> heatmap() {
        return ResponseEntity.ok(predicaoHeatmapService.pontosHeatmapPredito());
    }

    @GetMapping("/zonas")
    @Operation(summary = "Zonas de calor (GeoJSON)", description = "Centroides das zonas preditas pela IA.")
    @ApiResponse(responseCode = "200", description = "FeatureCollection GeoJSON",
            content = @Content(schema = @Schema(implementation = Map.class)))
    public ResponseEntity<Map<String, Object>> zonas() {
        return ResponseEntity.ok(predicaoHeatmapService.zonasGeoJson());
    }

    @GetMapping("/resumo")
    @Operation(summary = "Resumo das predições", description = "Totais de pacientes e zonas no PostGIS.")
    public ResponseEntity<Map<String, Object>> resumo() {
        return ResponseEntity.ok(predicaoHeatmapService.resumoPredicoes());
    }
}
