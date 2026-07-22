package br.unesp.sadcnr.application;

import br.unesp.sadcnr.domain.PacientePSR;
import br.unesp.sadcnr.infrastructure.persistence.PacientePSRRepository;
import org.locationtech.jts.geom.Point;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class HeatmapService {

    private final PacientePSRRepository repository;

    public HeatmapService(PacientePSRRepository repository) {
        this.repository = repository;
    }

    @Transactional(readOnly = true)
    public List<double[]> pontosHeatmap() {
        List<PacientePSR> pacientes = repository.findAll();
        List<double[]> pontos = new ArrayList<>(pacientes.size());
        for (PacientePSR p : pacientes) {
            Point geom = p.getGeom();
            if (geom == null) {
                continue;
            }
            // leaflet-heat: [lat, lng, intensity]
            double intensidade = p.getNivelVulnerabilidade() / 5.0;
            pontos.add(new double[]{geom.getY(), geom.getX(), intensidade});
        }
        return pontos;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> geoJson() {
        List<PacientePSR> pacientes = repository.findAll();
        List<Map<String, Object>> features = new ArrayList<>();

        for (PacientePSR p : pacientes) {
            Point geom = p.getGeom();
            if (geom == null) {
                continue;
            }

            Map<String, Object> geometry = new LinkedHashMap<>();
            geometry.put("type", "Point");
            geometry.put("coordinates", List.of(geom.getX(), geom.getY()));

            Map<String, Object> properties = new HashMap<>();
            properties.put("id", p.getId());
            properties.put("nivel_vulnerabilidade", p.getNivelVulnerabilidade());
            properties.put("sexo", p.getSexo());
            properties.put("faixa_etaria", p.getFaixaEtaria());

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
