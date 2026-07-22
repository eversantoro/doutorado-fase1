package br.unesp.sadcnr.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.Polygon;

import java.time.OffsetDateTime;

@Entity
@Table(name = "zonas_calor_preditas")
public class ZonaCalorPredita {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "cluster_id", nullable = false)
    private Integer clusterId;

    @Column(length = 80)
    private String rotulo;

    @Column(nullable = false)
    private Double intensidade;

    @Column(name = "n_pacientes", nullable = false)
    private Integer nPacientes;

    @Column(name = "vulnerabilidade_media")
    private Double vulnerabilidadeMedia;

    @Column(nullable = false, length = 40)
    private String metodo;

    @JdbcTypeCode(SqlTypes.GEOMETRY)
    @Column(columnDefinition = "geometry(Polygon,4326)", nullable = false)
    private Polygon geom;

    @JdbcTypeCode(SqlTypes.GEOMETRY)
    @Column(columnDefinition = "geometry(Point,4326)", nullable = false)
    private Point centroide;

    @Column(name = "gerado_em", nullable = false, insertable = false, updatable = false)
    private OffsetDateTime geradoEm;

    public Long getId() {
        return id;
    }

    public Integer getClusterId() {
        return clusterId;
    }

    public String getRotulo() {
        return rotulo;
    }

    public Double getIntensidade() {
        return intensidade;
    }

    public Integer getNPacientes() {
        return nPacientes;
    }

    public Double getVulnerabilidadeMedia() {
        return vulnerabilidadeMedia;
    }

    public String getMetodo() {
        return metodo;
    }

    public Polygon getGeom() {
        return geom;
    }

    public Point getCentroide() {
        return centroide;
    }

    public OffsetDateTime getGeradoEm() {
        return geradoEm;
    }
}
