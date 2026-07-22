"""
Módulo de IA preditiva — Fase 1 (Consultório na Rua / Bauru-SP).

1) Gera ~500 pacientes sintéticos em clusters (mock realista).
2) Aplica K-Means (aglomerados) + Kernel Density Estimation (intensidade).
3) Persiste pacientes e zonas_calor_preditas no PostGIS via SQLAlchemy.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from faker import Faker
from sklearn.cluster import KMeans
from sklearn.neighbors import KernelDensity
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BAURU_BBOX: Final[dict[str, float]] = {
    "min_lon": -49.15,
    "max_lon": -49.00,
    "min_lat": -22.40,
    "max_lat": -22.25,
}

EPICENTROS: Final[list[tuple[float, float, float]]] = [
    (-49.0606, -22.3149, 0.35),
    (-49.0720, -22.3260, 0.25),
    (-49.0450, -22.3500, 0.20),
    (-49.0850, -22.2950, 0.20),
]

SIGMA_GRAUS: Final[float] = 0.008
DEFAULT_N: Final[int] = 500
N_CLUSTERS: Final[int] = 4
SEED: Final[int] = 42
SRID: Final[int] = 4326


@dataclass(frozen=True)
class ZonaCalor:
    cluster_id: int
    rotulo: str
    intensidade: float
    n_pacientes: int
    vulnerabilidade_media: float
    wkt_polygon: str
    lon_centroide: float
    lat_centroide: float


def _engine() -> Engine:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "sad_cnr")
    user = os.getenv("POSTGRES_USER", "sad")
    password = os.getenv("POSTGRES_PASSWORD", "sad123")
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}")


def _clip(lon: float, lat: float) -> tuple[float, float]:
    lon = float(np.clip(lon, BAURU_BBOX["min_lon"], BAURU_BBOX["max_lon"]))
    lat = float(np.clip(lat, BAURU_BBOX["min_lat"], BAURU_BBOX["max_lat"]))
    return lon, lat


def gerar_pacientes_sinteticos(n: int = DEFAULT_N, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    fake = Faker("pt_BR")
    Faker.seed(seed)

    pesos = np.array([e[2] for e in EPICENTROS], dtype=float)
    pesos /= pesos.sum()
    escolhas = rng.choice(len(EPICENTROS), size=n, p=pesos)

    rows: list[dict[str, object]] = []
    for idx in escolhas:
        lon0, lat0, _ = EPICENTROS[int(idx)]
        lon, lat = _clip(lon0 + rng.normal(0, SIGMA_GRAUS), lat0 + rng.normal(0, SIGMA_GRAUS))
        base_vuln = 4 if idx == 0 else 3
        nivel = int(np.clip(rng.integers(base_vuln - 1, base_vuln + 2), 1, 5))
        rows.append(
            {
                "id_anonimizado": f"PSR-{fake.unique.hexify(text='^^^^^^^^').upper()}",
                "sexo": rng.choice(["M", "F", "O"], p=[0.75, 0.22, 0.03]),
                "faixa_etaria": rng.choice(
                    ["0-17", "18-29", "30-44", "45-59", "60+"],
                    p=[0.05, 0.25, 0.35, 0.25, 0.10],
                ),
                "nivel_vulnerabilidade": nivel,
                "longitude": round(lon, 6),
                "latitude": round(lat, 6),
            }
        )
    return pd.DataFrame(rows)


def aplicar_modelo_preditivo(df: pd.DataFrame, n_clusters: int = N_CLUSTERS, seed: int = SEED) -> tuple[pd.DataFrame, list[ZonaCalor]]:
    """K-Means para aglomerados + KDE para probabilidade_ia (densidade territorial)."""
    coords = df[["longitude", "latitude"]].to_numpy(dtype=float)

    kmeans = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
    labels = kmeans.fit_predict(coords)

    # KDE em graus (~banda ~800 m)
    kde = KernelDensity(bandwidth=0.008, kernel="gaussian")
    kde.fit(coords)
    log_dens = kde.score_samples(coords)
    dens = np.exp(log_dens)
    dens_norm = (dens - dens.min()) / (dens.max() - dens.min() + 1e-12)

    vuln = df["nivel_vulnerabilidade"].to_numpy(dtype=float) / 5.0
    # Score híbrido: densidade espacial + vulnerabilidade clínica
    probabilidade = np.clip(0.65 * dens_norm + 0.35 * vuln, 0.0, 1.0)

    out = df.copy()
    out["cluster_id"] = labels.astype(int)
    out["probabilidade_ia"] = np.round(probabilidade, 4)

    zonas: list[ZonaCalor] = []
    for cid in sorted(out["cluster_id"].unique()):
        subset = out[out["cluster_id"] == cid]
        pts = subset[["longitude", "latitude"]].to_numpy(dtype=float)
        cx, cy = float(pts[:, 0].mean()), float(pts[:, 1].mean())
        intens = float(subset["probabilidade_ia"].mean())
        vuln_media = float(subset["nivel_vulnerabilidade"].mean())

        # Envelope (bounding box expandido) como polígono da zona
        pad = 0.004
        minx, maxx = float(pts[:, 0].min()) - pad, float(pts[:, 0].max()) + pad
        miny, maxy = float(pts[:, 1].min()) - pad, float(pts[:, 1].max()) + pad
        wkt = (
            f"POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, "
            f"{minx} {maxy}, {minx} {miny}))"
        )
        zonas.append(
            ZonaCalor(
                cluster_id=int(cid),
                rotulo=f"Zona de calor {cid + 1}",
                intensidade=round(intens, 4),
                n_pacientes=int(len(subset)),
                vulnerabilidade_media=round(vuln_media, 2),
                wkt_polygon=wkt,
                lon_centroide=round(cx, 6),
                lat_centroide=round(cy, 6),
            )
        )
    return out, zonas


def persistir_postgis(df: pd.DataFrame, zonas: list[ZonaCalor], engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE historico_atendimentos, zonas_calor_preditas, pacientes_psr RESTART IDENTITY CASCADE"))

        for _, row in df.iterrows():
            conn.execute(
                text(
                    """
                    INSERT INTO pacientes_psr (
                        id_anonimizado, sexo, faixa_etaria, nivel_vulnerabilidade,
                        probabilidade_ia, cluster_id, coordenada
                    ) VALUES (
                        :id_anon, :sexo, :faixa, :nivel,
                        :prob, :cluster,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), :srid)
                    )
                    """
                ),
                {
                    "id_anon": row["id_anonimizado"],
                    "sexo": row["sexo"],
                    "faixa": row["faixa_etaria"],
                    "nivel": int(row["nivel_vulnerabilidade"]),
                    "prob": float(row["probabilidade_ia"]),
                    "cluster": int(row["cluster_id"]),
                    "lon": float(row["longitude"]),
                    "lat": float(row["latitude"]),
                    "srid": SRID,
                },
            )

        for z in zonas:
            conn.execute(
                text(
                    """
                    INSERT INTO zonas_calor_preditas (
                        cluster_id, rotulo, intensidade, n_pacientes,
                        vulnerabilidade_media, metodo, geom, centroide
                    ) VALUES (
                        :cid, :rotulo, :intens, :n,
                        :vuln, 'KMEANS_KDE',
                        ST_GeomFromText(:wkt, :srid),
                        ST_SetSRID(ST_MakePoint(:clon, :clat), :srid)
                    )
                    """
                ),
                {
                    "cid": z.cluster_id,
                    "rotulo": z.rotulo,
                    "intens": z.intensidade,
                    "n": z.n_pacientes,
                    "vuln": z.vulnerabilidade_media,
                    "wkt": z.wkt_polygon,
                    "clon": z.lon_centroide,
                    "clat": z.lat_centroide,
                    "srid": SRID,
                },
            )


def main() -> None:
    print("Gerando pacientes sinteticos (Bauru-SP)...")
    df = gerar_pacientes_sinteticos()
    print(f"  -> {len(df)} pacientes")

    print("Aplicando K-Means + KDE...")
    df_pred, zonas = aplicar_modelo_preditivo(df)
    print(f"  -> {len(zonas)} zonas de calor preditas")
    for z in zonas:
        print(
            f"     cluster={z.cluster_id} n={z.n_pacientes} "
            f"intensidade={z.intensidade:.3f} vuln_media={z.vulnerabilidade_media:.2f}"
        )

    engine = _engine()
    print("Persistindo no PostGIS...")
    persistir_postgis(df_pred, zonas, engine)
    print("Concluido. Pacientes e zonas_calor_preditas atualizados.")


if __name__ == "__main__":
    main()
