package br.unesp.sadcnr.application;

import br.unesp.sadcnr.domain.PacientePSR;
import br.unesp.sadcnr.domain.ZonaCalorPredita;
import br.unesp.sadcnr.infrastructure.persistence.PacientePSRRepository;
import br.unesp.sadcnr.infrastructure.persistence.ZonaCalorPreditaRepository;
import org.locationtech.jts.geom.Point;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class PredicaoHeatmapService {

    private final PacientePSRRepository pacienteRepository;
    private final ZonaCalorPreditaRepository zonaRepository;

    public PredicaoHeatmapService(
            PacientePSRRepository pacienteRepository,
            ZonaCalorPreditaRepository zonaRepository) {
        this.pacienteRepository = pacienteRepository;
        this.zonaRepository = zonaRepository;
    }

    /**
     * Pontos no formato Leaflet.heat: [lat, lng, intensidade],
     * usando probabilidade_ia do pipeline Python (K-Means + KDE).
     */
    @Transactional(readOnly = true)
    public List<double[]> pontosHeatmapPredito() {
        List<PacientePSR> pacientes = pacienteRepository.findAll();
        List<double[]> pontos = new ArrayList<>(pacientes.size());

        for (PacientePSR p : pacientes) {
            Point coord = p.getCoordenada();
            if (coord == null) {
                continue;
            }
            double intensidade;
            if (p.getProbabilidadeIa() != null) {
                intensidade = p.getProbabilidadeIa();
            } else if (p.getNivelVulnerabilidade() != null) {
                intensidade = p.getNivelVulnerabilidade() / 5.0;
            } else {
                intensidade = 0.5;
            }
            pontos.add(new double[]{coord.getY(), coord.getX(), intensidade});
        }
        return pontos;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> resumoPredicoes() {
        long pacientes = pacienteRepository.count();
        long zonas = zonaRepository.count();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("totalPacientes", pacientes);
        body.put("totalZonas", zonas);
        body.put("fonte", "modelo_preditivo_ia.py (KMeans + KDE)");
        return body;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> zonasGeoJson() {
        List<ZonaCalorPredita> zonas = zonaRepository.findAll();
        List<Map<String, Object>> features = new ArrayList<>();

        for (ZonaCalorPredita z : zonas) {
            Point c = z.getCentroide();
            if (c == null) {
                continue;
            }
            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "Point");
            geometry.put("coordinates", List.of(c.getX(), c.getY()));

            Map<String, Object> properties = new HashMap<>();
            properties.put("cluster_id", z.getClusterId());
            properties.put("rotulo", z.getRotulo());
            properties.put("intensidade", z.getIntensidade());
            properties.put("n_pacientes", z.getNPacientes());
            properties.put("vulnerabilidade_media", z.getVulnerabilidadeMedia());
            properties.put("metodo", z.getMetodo());

            Map<String, Object> feature = new LinkedHashMap<>();
            feature.put("type", "Feature");
            feature.put("geometry", geometry);
            feature.put("properties", properties);
            features.add(feature);
        }

        Map<String, Object> collection = new LinkedHashMap<>();
        collection.put("type", "FeatureCollection");
        collection.put("features", features);
        return collection;
    }
}
