-- SAD Consultório na Rua — Schema espacial inicial (Fase 1)
-- Executado automaticamente na primeira subida do container PostGIS

CREATE EXTENSION IF NOT EXISTS postgis;

-- Pacientes (PSR) — núcleo do MVP visual
CREATE TABLE IF NOT EXISTS pacientes_psr (
    id              BIGSERIAL PRIMARY KEY,
    id_anonimizado  VARCHAR(64) UNIQUE,
    sexo            CHAR(1) CHECK (sexo IS NULL OR sexo IN ('M', 'F', 'O')),
    faixa_etaria    VARCHAR(20),
    nivel_vulnerabilidade SMALLINT NOT NULL CHECK (nivel_vulnerabilidade BETWEEN 1 AND 5),
    geom            geometry(Point, 4326) NOT NULL,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pacientes_psr_geom
    ON pacientes_psr USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_pacientes_psr_vulnerabilidade
    ON pacientes_psr (nivel_vulnerabilidade);

-- Bases operacionais das equipes (UBS, Caps, sede CnR)
CREATE TABLE IF NOT EXISTS bases_operacionais (
    id          BIGSERIAL PRIMARY KEY,
    nome        VARCHAR(120) NOT NULL,
    tipo        VARCHAR(40) NOT NULL,
    geom        geometry(Point, 4326) NOT NULL,
    ativo       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_bases_operacionais_geom
    ON bases_operacionais USING GIST (geom);

-- Histórico de atendimentos (preparação Fase 2)
CREATE TABLE IF NOT EXISTS historico_atendimentos (
    id              BIGSERIAL PRIMARY KEY,
    paciente_id     BIGINT NOT NULL REFERENCES pacientes_psr(id) ON DELETE CASCADE,
    data_hora       TIMESTAMPTZ NOT NULL,
    tipo_demanda    VARCHAR(40) NOT NULL
                    CHECK (tipo_demanda IN ('MEDICA', 'PSIQUIATRICA', 'ASSISTENCIA_SOCIAL')),
    geom            geometry(Point, 4326) NOT NULL,
    observacao      TEXT
);

CREATE INDEX IF NOT EXISTS idx_historico_paciente
    ON historico_atendimentos (paciente_id);

CREATE INDEX IF NOT EXISTS idx_historico_geom
    ON historico_atendimentos USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_historico_data
    ON historico_atendimentos (data_hora);

-- Bases sintéticas iniciais em Bauru-SP (referência operacional)
INSERT INTO bases_operacionais (nome, tipo, geom)
SELECT v.nome, v.tipo, v.geom
FROM (VALUES
    ('UBS Centro', 'UBS', ST_SetSRID(ST_MakePoint(-49.0606, -22.3149), 4326)),
    ('CAPS II Bauru', 'CAPS', ST_SetSRID(ST_MakePoint(-49.0720, -22.3250), 4326)),
    ('Sede Consultório na Rua', 'CNR', ST_SetSRID(ST_MakePoint(-49.0550, -22.3200), 4326))
) AS v(nome, tipo, geom)
WHERE NOT EXISTS (SELECT 1 FROM bases_operacionais LIMIT 1);
