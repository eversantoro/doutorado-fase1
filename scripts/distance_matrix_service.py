"""
Calcula matriz de custos (tempo/distância) via OSRM Table API.

Pré-requisito: container OSRM processado e escutando em OSRM_URL.
Saída: data/matriz_distancias.json — pronta para motores de otimização (Fase 3).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

OSRM_URL: Final[str] = os.getenv("OSRM_URL", "http://localhost:5000").rstrip("/")
OUTPUT_PATH: Final[Path] = (
    Path(__file__).resolve().parent.parent / "data" / "matriz_distancias.json"
)


@dataclass(frozen=True)
class Ponto:
    id: int
    nome: str
    lon: float
    lat: float
    tipo: str  # BASE | PACIENTE | CLUSTER


def _engine() -> Engine:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "sad_cnr")
    user = os.getenv("POSTGRES_USER", "sad")
    password = os.getenv("POSTGRES_PASSWORD", "sad123")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


def carregar_bases(engine: Engine) -> list[Ponto]:
    sql = text(
        """
        SELECT id, nome,
               ST_X(geom) AS lon, ST_Y(geom) AS lat
        FROM bases_operacionais
        WHERE ativo = TRUE
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()
    return [
        Ponto(id=r["id"], nome=r["nome"], lon=r["lon"], lat=r["lat"], tipo="BASE")
        for r in rows
    ]


def carregar_clusters(engine: Engine, grid_deg: float = 0.01) -> list[Ponto]:
    """Agrega pacientes em células de grade (aprox. 1 km) para reduzir o Table API."""
    sql = text(
        """
        SELECT
            ROW_NUMBER() OVER () AS id,
            ROUND(CAST(ST_X(geom) AS numeric) / :g) * :g AS lon,
            ROUND(CAST(ST_Y(geom) AS numeric) / :g) * :g AS lat,
            COUNT(*) AS n,
            AVG(nivel_vulnerabilidade) AS vuln_media
        FROM pacientes_psr
        GROUP BY 2, 3
        HAVING COUNT(*) >= 1
        ORDER BY n DESC
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"g": grid_deg}).mappings().all()
    return [
        Ponto(
            id=int(r["id"]),
            nome=f"cluster-{r['id']}(n={r['n']},v={round(float(r['vuln_media']),1)})",
            lon=float(r["lon"]),
            lat=float(r["lat"]),
            tipo="CLUSTER",
        )
        for r in rows
    ]


def osrm_table(
    fontes: list[Ponto], destinos: list[Ponto]
) -> dict[str, Any]:
    coords = ";".join(
        f"{p.lon},{p.lat}" for p in (*fontes, *destinos)
    )
    n_src = len(fontes)
    n_dst = len(destinos)
    sources = ";".join(str(i) for i in range(n_src))
    destinations = ";".join(str(i) for i in range(n_src, n_src + n_dst))

    url = (
        f"{OSRM_URL}/table/v1/driving/{coords}"
        f"?sources={sources}&destinations={destinations}"
        f"&annotations=duration,distance"
    )
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != "Ok":
        raise RuntimeError(f"OSRM Table falhou: {payload}")
    return payload


def montar_matriz(
    fontes: list[Ponto], destinos: list[Ponto], table: dict[str, Any]
) -> dict[str, Any]:
    durations = table.get("durations") or []
    distances = table.get("distances") or []
    celulas: list[dict[str, Any]] = []
    for i, origem in enumerate(fontes):
        for j, destino in enumerate(destinos):
            celulas.append(
                {
                    "origem": asdict(origem),
                    "destino": asdict(destino),
                    "duracao_segundos": durations[i][j] if durations else None,
                    "distancia_metros": distances[i][j] if distances else None,
                }
            )
    return {
        "fonte_api": OSRM_URL,
        "n_origens": len(fontes),
        "n_destinos": len(destinos),
        "celulas": celulas,
    }


def main() -> None:
    engine = _engine()
    bases = carregar_bases(engine)
    clusters = carregar_clusters(engine)
    if not bases:
        raise SystemExit("Nenhuma base operacional encontrada.")
    if not clusters:
        raise SystemExit("Nenhum paciente/cluster encontrado. Importe o CSV primeiro.")

    print(f"Bases: {len(bases)} | Clusters: {len(clusters)}")
    print(f"Consultando OSRM em {OSRM_URL} ...")
    table = osrm_table(bases, clusters)
    matriz = montar_matriz(bases, clusters, table)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(matriz, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Matriz salva em {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
