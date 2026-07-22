"""
Microserviço de Importação — SAD Consultório na Rua
Valida CSV municipal e persiste no PostGIS.
"""

from __future__ import annotations

import csv
import io
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

IMPORT_MIN_LAT = float(os.getenv("IMPORT_MIN_LAT", "-22.40"))
IMPORT_MAX_LAT = float(os.getenv("IMPORT_MAX_LAT", "-22.25"))
IMPORT_MIN_LON = float(os.getenv("IMPORT_MIN_LON", "-49.15"))
IMPORT_MAX_LON = float(os.getenv("IMPORT_MAX_LON", "-49.00"))
MAX_BYTES = int(os.getenv("IMPORT_MAX_BYTES", str(10 * 1024 * 1024)))
MAX_ROWS = int(os.getenv("IMPORT_MAX_ROWS", "50000"))
SRID: Final[int] = 4326

REQUIRED_PACIENTES = ("nivel_vulnerabilidade", "latitude", "longitude")
OPTIONAL_PACIENTES = (
    "id_anonimizado",
    "sexo",
    "faixa_etaria",
    "probabilidade_ia",
    "data_referencia",
)

TEMPLATE_PACIENTES = (
    "id_anonimizado,sexo,faixa_etaria,nivel_vulnerabilidade,latitude,longitude,probabilidade_ia,data_referencia\n"
    "PSR-EXEMPLO01,M,30-44,4,-22.314900,-49.060600,0.82,2026-07-01\n"
    "PSR-EXEMPLO02,F,45-59,5,-22.320100,-49.055200,0.91,2026-07-01\n"
    "PSR-EXEMPLO03,M,18-29,3,-22.330000,-49.070000,,2026-07-02\n"
)

TEMPLATE_BASES = (
    "nome,tipo,latitude,longitude,ativo\n"
    "UBS Centro,UBS,-22.314900,-49.060600,true\n"
    "CAPS II,CAPS,-22.325000,-49.072000,true\n"
)


@dataclass
class LinhaErro:
    linha: int
    motivo: str

    def to_dict(self) -> dict[str, Any]:
        return {"linha": self.linha, "motivo": self.motivo}


@dataclass
class ResultadoImportacao:
    status: str
    modo: str
    recebidas: int
    importadas: int
    rejeitadas: int
    erros: list[LinhaErro] = field(default_factory=list)
    total_banco: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "modo": self.modo,
            "recebidas": self.recebidas,
            "importadas": self.importadas,
            "rejeitadas": self.rejeitadas,
            "erros": [e.to_dict() for e in self.erros[:100]],
            "erros_truncados": len(self.erros) > 100,
            "total_banco": self.total_banco,
        }


class HealthResponse(BaseModel):
    status: str
    database: str
    detail: str | None = None


class LinhaErroModel(BaseModel):
    linha: int = Field(description="Número da linha no CSV (1 = cabeçalho)")
    motivo: str


class ImportResultadoModel(BaseModel):
    status: str
    modo: str
    recebidas: int
    importadas: int
    rejeitadas: int
    erros: list[LinhaErroModel] = Field(default_factory=list)
    erros_truncados: bool = False
    total_banco: int = 0


def _engine() -> Engine:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "sad_cnr")
    user = os.getenv("POSTGRES_USER", "sad")
    password = os.getenv("POSTGRES_PASSWORD", "sad123")
    return create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}",
        pool_pre_ping=True,
    )


app = FastAPI(
    title="SAD CnR — Microserviço de Importação",
    version="1.0.0",
    description="""
## Objetivo
Validar e carregar CSV municipal (PSR / bases operacionais) no **PostGIS**.

## Contrato
Documentação completa: `docs/FORMATO_IMPORTACAO_DADOS.md`

## UI Swagger
- Interativa: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## SAD Visual
Gateway no Spring Boot: `http://localhost:8081/swagger-ui.html`
""",
    contact={
        "name": "Ever Santoro — UNESP/PPGEP",
        "url": "https://github.com/eversantoro/doutorado-fase1",
    },
    license_info={"name": "Uso acadêmico"},
    openapi_tags=[
        {"name": "Saúde", "description": "Healthcheck do serviço e do banco"},
        {"name": "Contrato", "description": "Schema e templates CSV"},
        {"name": "Importação", "description": "Carga de pacientes e bases operacionais"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Saúde"], response_model=HealthResponse, summary="Healthcheck")
def health() -> dict[str, str]:
    try:
        with _engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "up"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "degraded", "database": "down", "detail": str(exc)}


@app.get(
    "/api/v1/import/schema",
    tags=["Contrato"],
    summary="Contrato JSON de importação",
    description="Colunas obrigatórias/opcionais, bounding box municipal e limites.",
)
def schema() -> dict[str, Any]:
    return {
        "versao": "1.0",
        "encoding": "UTF-8",
        "separador": ",",
        "srid": SRID,
        "bounding_box": {
            "min_lat": IMPORT_MIN_LAT,
            "max_lat": IMPORT_MAX_LAT,
            "min_lon": IMPORT_MIN_LON,
            "max_lon": IMPORT_MAX_LON,
        },
        "pacientes": {
            "obrigatorias": list(REQUIRED_PACIENTES),
            "opcionais": list(OPTIONAL_PACIENTES),
            "nivel_vulnerabilidade": "inteiro 1..5",
            "probabilidade_ia": "float 0..1 (default = nivel/5)",
            "sexo": ["M", "F", "O", None],
        },
        "limites": {"max_bytes": MAX_BYTES, "max_rows": MAX_ROWS},
        "documentacao": "docs/FORMATO_IMPORTACAO_DADOS.md",
    }


@app.get(
    "/api/v1/import/template/pacientes",
    tags=["Contrato"],
    summary="Download do CSV modelo de pacientes",
)
def template_pacientes() -> Response:
    return Response(
        content=TEMPLATE_PACIENTES,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=modelo_pacientes_psr.csv"},
    )


@app.get(
    "/api/v1/import/template/bases",
    tags=["Contrato"],
    summary="Download do CSV modelo de bases operacionais",
)
def template_bases() -> Response:
    return Response(
        content=TEMPLATE_BASES,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=modelo_bases_operacionais.csv"},
    )


def _read_csv_rows(raw: bytes) -> list[dict[str, str]]:
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Arquivo excede {MAX_BYTES} bytes.")
    try:
        text_data = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Arquivo deve estar em UTF-8.") from exc

    reader = csv.DictReader(io.StringIO(text_data))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV sem cabeçalho.")

    headers = [h.strip().lower() for h in reader.fieldnames if h]
    for req in REQUIRED_PACIENTES:
        if req not in headers:
            raise HTTPException(
                status_code=400,
                detail=f"Cabeçalho incompleto. Falta coluna obrigatória: {req}",
            )

    rows: list[dict[str, str]] = []
    for row in reader:
        if row is None:
            continue
        normalized = {
            (k.strip().lower() if k else ""): (v.strip() if v is not None else "")
            for k, v in row.items()
        }
        # ignora linhas totalmente vazias
        if not any(normalized.values()):
            continue
        rows.append(normalized)
        if len(rows) > MAX_ROWS:
            raise HTTPException(status_code=400, detail=f"Máximo de {MAX_ROWS} linhas.")
    return rows


def _parse_paciente(
    row: dict[str, str], linha_num: int, seen_ids: set[str]
) -> tuple[dict[str, Any] | None, LinhaErro | None]:
    try:
        nivel = int(row.get("nivel_vulnerabilidade", "").replace(",", ".").split(".")[0])
    except ValueError:
        return None, LinhaErro(linha_num, "nivel_vulnerabilidade invalido")
    if nivel < 1 or nivel > 5:
        return None, LinhaErro(linha_num, "nivel_vulnerabilidade fora de 1..5")

    try:
        lat = float(row.get("latitude", "").replace(",", "."))
        lon = float(row.get("longitude", "").replace(",", "."))
    except ValueError:
        return None, LinhaErro(linha_num, "latitude/longitude nao numericas")

    if not (IMPORT_MIN_LAT <= lat <= IMPORT_MAX_LAT and IMPORT_MIN_LON <= lon <= IMPORT_MAX_LON):
        return None, LinhaErro(linha_num, "coordenada fora do bounding box municipal")

    sexo = row.get("sexo", "").upper()
    if sexo and sexo not in {"M", "F", "O"}:
        return None, LinhaErro(linha_num, "sexo deve ser M, F ou O")

    prob_raw = row.get("probabilidade_ia", "")
    if prob_raw:
        try:
            prob = float(prob_raw.replace(",", "."))
        except ValueError:
            return None, LinhaErro(linha_num, "probabilidade_ia invalida")
        if not 0.0 <= prob <= 1.0:
            return None, LinhaErro(linha_num, "probabilidade_ia fora de 0..1")
    else:
        prob = nivel / 5.0

    id_anon = row.get("id_anonimizado") or f"PSR-{uuid.uuid4().hex[:12].upper()}"
    if id_anon in seen_ids:
        return None, LinhaErro(linha_num, "id_anonimizado duplicado no arquivo")
    seen_ids.add(id_anon)

    return {
        "id_anonimizado": id_anon,
        "sexo": sexo or None,
        "faixa_etaria": row.get("faixa_etaria") or None,
        "nivel_vulnerabilidade": nivel,
        "probabilidade_ia": round(prob, 4),
        "latitude": lat,
        "longitude": lon,
    }, None


@app.post(
    "/api/v1/import/pacientes",
    tags=["Importação"],
    response_model=ImportResultadoModel,
    summary="Importar CSV de pacientes PSR",
    description="Valida o CSV conforme o contrato e persiste no PostGIS. "
    "Modos: `substituir` (padrão) ou `acrescentar`. Com `strict=true`, aborta na 1ª linha inválida.",
)
async def import_pacientes(
    file: UploadFile = File(..., description="Arquivo .csv UTF-8"),
    modo: Literal["substituir", "acrescentar"] = Form("substituir"),
    strict: bool = Form(False),
) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .csv")

    raw = await file.read()
    rows = _read_csv_rows(raw)

    validos: list[dict[str, Any]] = []
    erros: list[LinhaErro] = []
    seen: set[str] = set()

    for idx, row in enumerate(rows, start=2):  # linha 1 = cabeçalho
        parsed, err = _parse_paciente(row, idx, seen)
        if err:
            erros.append(err)
            if strict:
                raise HTTPException(
                    status_code=400,
                    detail={"mensagem": "Importacao abortada (strict)", "erro": err.to_dict()},
                )
            continue
        assert parsed is not None
        validos.append(parsed)

    inserted = 0
    engine = _engine()
    try:
        with engine.begin() as conn:
            if modo == "substituir":
                conn.execute(
                    text(
                        "TRUNCATE TABLE historico_atendimentos, zonas_calor_preditas, "
                        "pacientes_psr RESTART IDENTITY CASCADE"
                    )
                )

            for p in validos:
                if modo == "acrescentar":
                    exists = conn.execute(
                        text("SELECT 1 FROM pacientes_psr WHERE id_anonimizado = :id"),
                        {"id": p["id_anonimizado"]},
                    ).first()
                    if exists:
                        erros.append(
                            LinhaErro(0, f"id_anonimizado ja existe no banco: {p['id_anonimizado']}")
                        )
                        continue

                conn.execute(
                    text(
                        """
                        INSERT INTO pacientes_psr (
                            id_anonimizado, sexo, faixa_etaria, nivel_vulnerabilidade,
                            probabilidade_ia, coordenada
                        ) VALUES (
                            :id_anon, :sexo, :faixa, :nivel, :prob,
                            ST_SetSRID(ST_MakePoint(:lon, :lat), :srid)
                        )
                        """
                    ),
                    {
                        "id_anon": p["id_anonimizado"],
                        "sexo": p["sexo"],
                        "faixa": p["faixa_etaria"],
                        "nivel": p["nivel_vulnerabilidade"],
                        "prob": p["probabilidade_ia"],
                        "lon": p["longitude"],
                        "lat": p["latitude"],
                        "srid": SRID,
                    },
                )
                inserted += 1

            total = conn.execute(text("SELECT COUNT(*) FROM pacientes_psr")).scalar_one()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha ao persistir: {exc}") from exc

    result = ResultadoImportacao(
        status="ok" if inserted else "vazio",
        modo=modo,
        recebidas=len(rows),
        importadas=inserted,
        rejeitadas=len(erros),
        erros=erros,
        total_banco=int(total),
    )
    return result.to_dict()


def _read_bases(raw: bytes) -> list[dict[str, Any]]:
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"Arquivo excede {MAX_BYTES} bytes.")
    text_data = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text_data))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV sem cabeçalho.")
    headers = [h.strip().lower() for h in reader.fieldnames if h]
    for req in ("nome", "tipo", "latitude", "longitude"):
        if req not in headers:
            raise HTTPException(status_code=400, detail=f"Falta coluna: {req}")

    out: list[dict[str, Any]] = []
    for idx, row in enumerate(reader, start=2):
        norm = {(k.strip().lower() if k else ""): (v.strip() if v else "") for k, v in row.items()}
        if not any(norm.values()):
            continue
        try:
            lat = float(norm["latitude"].replace(",", "."))
            lon = float(norm["longitude"].replace(",", "."))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Linha {idx}: lat/lon invalidas") from exc
        ativo_raw = (norm.get("ativo") or "true").lower()
        out.append(
            {
                "nome": norm["nome"][:120],
                "tipo": norm["tipo"][:40],
                "lat": lat,
                "lon": lon,
                "ativo": ativo_raw in {"1", "true", "sim", "yes"},
            }
        )
    return out


@app.post(
    "/api/v1/import/bases",
    tags=["Importação"],
    summary="Importar CSV de bases operacionais",
    description="Cadastra UBS, CAPS, sede CnR etc. no PostGIS.",
)
async def import_bases(
    file: UploadFile = File(..., description="Arquivo .csv UTF-8"),
    substituir: bool = Form(False),
) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .csv")
    raw = await file.read()
    bases = _read_bases(raw)
    engine = _engine()
    with engine.begin() as conn:
        if substituir:
            conn.execute(text("TRUNCATE TABLE bases_operacionais RESTART IDENTITY CASCADE"))
        for b in bases:
            conn.execute(
                text(
                    """
                    INSERT INTO bases_operacionais (nome, tipo, geom, ativo)
                    VALUES (:nome, :tipo, ST_SetSRID(ST_MakePoint(:lon, :lat), :srid), :ativo)
                    """
                ),
                {**b, "srid": SRID},
            )
        total = conn.execute(text("SELECT COUNT(*) FROM bases_operacionais")).scalar_one()
    return {"status": "ok", "importadas": len(bases), "total_banco": int(total)}


@app.get("/", response_class=PlainTextResponse, include_in_schema=False)
def root() -> str:
    return "SAD CnR Import Service — Swagger UI: /docs | ReDoc: /redoc | OpenAPI: /openapi.json"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("IMPORT_SERVICE_PORT", "8090")),
        reload=False,
    )
