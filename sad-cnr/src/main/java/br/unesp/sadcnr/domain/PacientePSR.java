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

import java.time.OffsetDateTime;

@Entity
@Table(name = "pacientes_psr")
public class PacientePSR {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "id_anonimizado", length = 64, unique = true)
    private String idAnonimizado;

    @Column(length = 1)
    private String sexo;

    @Column(name = "faixa_etaria", length = 20)
    private String faixaEtaria;

    @Column(name = "nivel_vulnerabilidade", nullable = false)
    private Short nivelVulnerabilidade;

    @Column(name = "probabilidade_ia")
    private Double probabilidadeIa;

    @Column(name = "cluster_id")
    private Integer clusterId;

    @JdbcTypeCode(SqlTypes.GEOMETRY)
    @Column(name = "coordenada", columnDefinition = "geometry(Point,4326)", nullable = false)
    private Point coordenada;

    @Column(name = "criado_em", nullable = false, insertable = false, updatable = false)
    private OffsetDateTime criadoEm;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getIdAnonimizado() {
        return idAnonimizado;
    }

    public void setIdAnonimizado(String idAnonimizado) {
        this.idAnonimizado = idAnonimizado;
    }

    public String getSexo() {
        return sexo;
    }

    public void setSexo(String sexo) {
        this.sexo = sexo;
    }

    public String getFaixaEtaria() {
        return faixaEtaria;
    }

    public void setFaixaEtaria(String faixaEtaria) {
        this.faixaEtaria = faixaEtaria;
    }

    public Short getNivelVulnerabilidade() {
        return nivelVulnerabilidade;
    }

    public void setNivelVulnerabilidade(Short nivelVulnerabilidade) {
        this.nivelVulnerabilidade = nivelVulnerabilidade;
    }

    public Double getProbabilidadeIa() {
        return probabilidadeIa;
    }

    public void setProbabilidadeIa(Double probabilidadeIa) {
        this.probabilidadeIa = probabilidadeIa;
    }

    public Integer getClusterId() {
        return clusterId;
    }

    public void setClusterId(Integer clusterId) {
        this.clusterId = clusterId;
    }

    public Point getCoordenada() {
        return coordenada;
    }

    public void setCoordenada(Point coordenada) {
        this.coordenada = coordenada;
    }

    public OffsetDateTime getCriadoEm() {
        return criadoEm;
    }
}
