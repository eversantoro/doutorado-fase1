-- Migração v2: IA preditiva (banco já existente com coluna geom)
-- Aplicar em ambiente já provisionado: docker exec ... -f /path ou psql

ALTER TABLE pacientes_psr
    ADD COLUMN IF NOT EXISTS probabilidade_ia DOUBLE PRECISION;

ALTER TABLE pacientes_psr
    ADD COLUMN IF NOT EXISTS cluster_id INTEGER;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pacientes_psr' AND column_name = 'geom'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pacientes_psr' AND column_name = 'coordenada'
    ) THEN
        ALTER TABLE pacientes_psr RENAME COLUMN geom TO coordenada;
    END IF;
END $$;

DROP INDEX IF EXISTS idx_pacientes_psr_geom;
CREATE INDEX IF NOT EXISTS idx_pacientes_psr_coordenada
    ON pacientes_psr USING GIST (coordenada);
CREATE INDEX IF NOT EXISTS idx_pacientes_psr_probabilidade
    ON pacientes_psr (probabilidade_ia);

CREATE TABLE IF NOT EXISTS zonas_calor_preditas (
    id                      BIGSERIAL PRIMARY KEY,
    cluster_id              INTEGER NOT NULL,
    rotulo                  VARCHAR(80),
    intensidade             DOUBLE PRECISION NOT NULL CHECK (intensidade >= 0 AND intensidade <= 1),
    n_pacientes             INTEGER NOT NULL DEFAULT 0,
    vulnerabilidade_media   DOUBLE PRECISION,
    metodo                  VARCHAR(40) NOT NULL DEFAULT 'KMEANS_KDE',
    geom                    geometry(Polygon, 4326) NOT NULL,
    centroide               geometry(Point, 4326) NOT NULL,
    gerado_em               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_zonas_calor_geom
    ON zonas_calor_preditas USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_zonas_calor_centroide
    ON zonas_calor_preditas USING GIST (centroide);
