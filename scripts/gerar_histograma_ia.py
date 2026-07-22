"""Gera figura tipo histograma explicando a IA atual (K-Means + KDE + score)."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from modelo_preditivo_ia import aplicar_modelo_preditivo, gerar_pacientes_sinteticos  # noqa: E402

OUT = ROOT / "docs" / "histograma_ia_probabilidade.png"


def main() -> None:
    df = gerar_pacientes_sinteticos(500)
    df, zonas = aplicar_modelo_preditivo(df)

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.facecolor": "#0f1c24",
            "figure.facecolor": "#0f1c24",
            "text.color": "#e8f1f4",
            "axes.labelcolor": "#e8f1f4",
            "xtick.color": "#9bb0ba",
            "ytick.color": "#9bb0ba",
            "axes.edgecolor": "#243844",
            "grid.color": "#243844",
        }
    )

    fig = plt.figure(figsize=(14, 8.5), dpi=160)
    gs = fig.add_gridspec(
        2,
        2,
        height_ratios=[1.15, 1],
        hspace=0.35,
        wspace=0.28,
        left=0.07,
        right=0.97,
        top=0.88,
        bottom=0.08,
    )

    fig.suptitle(
        "Como a IA transforma pontos territoriais em prioridade (probabilidade_ia)",
        fontsize=15,
        fontweight="bold",
        color="#e8f1f4",
        y=0.96,
    )
    fig.text(
        0.5,
        0.915,
        "Pipeline atual: K-Means (zonas) + KDE (densidade) + score hibrido 0,65 dens + 0,35 vulnerabilidade",
        ha="center",
        fontsize=10,
        color="#9bb0ba",
    )

    cores = ["#2b6cb0", "#38a169", "#d69e2e", "#c53030"]

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.hist(df["probabilidade_ia"], bins=20, color="#3d9b8f", edgecolor="#0f1c24", alpha=0.92)
    media = float(df["probabilidade_ia"].mean())
    ax1.axvline(media, color="#e8b86d", linestyle="--", linewidth=2, label=f"Media = {media:.2f}")
    ax1.set_title("1) Distribuicao do score probabilidade_ia", fontsize=12, pad=8)
    ax1.set_xlabel("probabilidade_ia (0 = menor prioridade | 1 = maior)")
    ax1.set_ylabel("Numero de pacientes")
    ax1.grid(axis="y", alpha=0.35)
    ax1.legend(facecolor="#162832", edgecolor="#243844", labelcolor="#e8f1f4")

    ax2 = fig.add_subplot(gs[0, 1])
    for cid in sorted(df["cluster_id"].unique()):
        subset = df.loc[df["cluster_id"] == cid, "probabilidade_ia"]
        ax2.hist(
            subset,
            bins=12,
            alpha=0.55,
            color=cores[int(cid) % 4],
            label=f"Zona {int(cid) + 1} (n={len(subset)})",
            edgecolor="#0f1c24",
        )
    ax2.set_title("2) Score separado por zona (K-Means)", fontsize=12, pad=8)
    ax2.set_xlabel("probabilidade_ia")
    ax2.set_ylabel("Numero de pacientes")
    ax2.grid(axis="y", alpha=0.35)
    ax2.legend(facecolor="#162832", edgecolor="#243844", labelcolor="#e8f1f4", fontsize=8)

    ax3 = fig.add_subplot(gs[1, 0])
    sample = df.sort_values("probabilidade_ia").iloc[:: max(len(df) // 8, 1)].head(8).copy()
    vuln_c = sample["nivel_vulnerabilidade"].to_numpy(dtype=float) / 5.0
    dens_c = np.clip((sample["probabilidade_ia"].to_numpy(dtype=float) - 0.35 * vuln_c) / 0.65, 0, 1)
    contrib_d = 0.65 * dens_c
    contrib_v = 0.35 * vuln_c
    x = np.arange(len(sample))
    ax3.bar(x, contrib_d, color="#3d9b8f", label="0,65 x densidade (KDE)", width=0.7)
    ax3.bar(x, contrib_v, bottom=contrib_d, color="#e8b86d", label="0,35 x vulnerabilidade/5", width=0.7)
    ax3.set_xticks(x)
    ax3.set_xticklabels([f"P{i + 1}" for i in range(len(sample))], fontsize=8)
    ax3.set_ylim(0, 1.05)
    ax3.set_title("3) Composicao do score (amostra de pacientes)", fontsize=12, pad=8)
    ax3.set_ylabel("Contribuicao para probabilidade_ia")
    ax3.set_xlabel("Pacientes (amostra do menor ao maior score)")
    ax3.legend(facecolor="#162832", edgecolor="#243844", labelcolor="#e8f1f4", fontsize=8)
    ax3.grid(axis="y", alpha=0.35)

    ax4 = fig.add_subplot(gs[1, 1])
    labels = [f"Zona {z.cluster_id + 1}" for z in zonas]
    intens = [z.intensidade for z in zonas]
    ns = [z.n_pacientes for z in zonas]
    bars = ax4.bar(
        labels,
        intens,
        color=[cores[z.cluster_id % 4] for z in zonas],
        edgecolor="#0f1c24",
    )
    for b, n, v in zip(bars, ns, intens):
        ax4.text(
            b.get_x() + b.get_width() / 2,
            b.get_height() + 0.02,
            f"{v:.2f}\nn={n}",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#e8f1f4",
        )
    ax4.set_ylim(0, 1.15)
    ax4.set_title("4) Intensidade media por zona de calor", fontsize=12, pad=8)
    ax4.set_ylabel("Media de probabilidade_ia na zona")
    ax4.grid(axis="y", alpha=0.35)

    fig.text(
        0.5,
        0.015,
        "Fonte: modelo_preditivo_ia.py | SAD Consultorio na Rua — Fase 1 (UNESP/PPGEP) | Dados sinteticos de demonstracao",
        ha="center",
        fontsize=8,
        color="#9bb0ba",
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=160)
    print(f"Gerado: {OUT}")


if __name__ == "__main__":
    main()
