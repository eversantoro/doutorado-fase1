"""
Gera mock_pacientes.csv com coordenadas sintéticas em Bauru-SP.

Os pontos seguem distribuição normal em torno de epicentros (clusters),
simulando praças, albergues e viadutos — "zonas de calor" para o MVP.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd
from faker import Faker

# Bounding box aproximado do município de Bauru-SP (WGS84)
BAURU_BBOX: Final[dict[str, float]] = {
    "min_lon": -49.15,
    "max_lon": -49.00,
    "min_lat": -22.40,
    "max_lat": -22.25,
}

# Epicentros sintéticos (lon, lat, peso relativo do cluster)
EPICENTROS: Final[list[tuple[float, float, float]]] = [
    (-49.0606, -22.3149, 0.35),  # Centro / Praça
    (-49.0720, -22.3260, 0.25),  # Terminal / entorno
    (-49.0450, -22.3500, 0.20),  # Zona sul / industrial
    (-49.0850, -22.2950, 0.20),  # Zona norte
]

SIGMA_GRAUS: Final[float] = 0.008  # ~800–900 m de dispersão
DEFAULT_N: Final[int] = 500
SEED: Final[int] = 42


def _clip_to_bbox(lon: float, lat: float) -> tuple[float, float]:
    lon = float(np.clip(lon, BAURU_BBOX["min_lon"], BAURU_BBOX["max_lon"]))
    lat = float(np.clip(lat, BAURU_BBOX["min_lat"], BAURU_BBOX["max_lat"]))
    return lon, lat


def gerar_pacientes(n: int = DEFAULT_N, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    fake = Faker("pt_BR")
    Faker.seed(seed)

    pesos = np.array([e[2] for e in EPICENTROS], dtype=float)
    pesos /= pesos.sum()
    escolhas = rng.choice(len(EPICENTROS), size=n, p=pesos)

    linhas: list[dict[str, object]] = []
    for i, idx in enumerate(escolhas, start=1):
        lon0, lat0, _ = EPICENTROS[idx]
        lon = lon0 + rng.normal(0.0, SIGMA_GRAUS)
        lat = lat0 + rng.normal(0.0, SIGMA_GRAUS)
        lon, lat = _clip_to_bbox(lon, lat)

        # Intensidade correlacionada ao cluster (centro tende a vulnerabilidade maior)
        base_vuln = 4 if idx == 0 else 3
        nivel = int(np.clip(rng.integers(base_vuln - 1, base_vuln + 2), 1, 5))

        linhas.append(
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
                "cluster_id": int(idx),
            }
        )

    return pd.DataFrame(linhas)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera CSV sintético de PSR em Bauru-SP")
    parser.add_argument("-n", "--quantidade", type=int, default=DEFAULT_N)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "mock_pacientes.csv",
    )
    args = parser.parse_args()

    df = gerar_pacientes(n=args.quantidade)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding="utf-8")
    print(f"Gerados {len(df)} pacientes -> {args.output}")


if __name__ == "__main__":
    main()
