package br.unesp.sadcnr.api;

import br.unesp.sadcnr.application.PredicaoHeatmapService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/predicoes")
public class PredicaoController {

    private final PredicaoHeatmapService predicaoHeatmapService;

    public PredicaoController(PredicaoHeatmapService predicaoHeatmapService) {
        this.predicaoHeatmapService = predicaoHeatmapService;
    }

    @GetMapping("/heatmap")
    public ResponseEntity<List<double[]>> heatmap() {
        return ResponseEntity.ok(predicaoHeatmapService.pontosHeatmapPredito());
    }

    @GetMapping("/zonas")
    public ResponseEntity<Map<String, Object>> zonas() {
        return ResponseEntity.ok(predicaoHeatmapService.zonasGeoJson());
    }

    @GetMapping("/resumo")
    public ResponseEntity<Map<String, Object>> resumo() {
        return ResponseEntity.ok(predicaoHeatmapService.resumoPredicoes());
    }
}
