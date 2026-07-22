# SAD Consultório na Rua — Fase 1 (IA preditiva + MVP visual)

Sistema de Apoio à Decisão para o **Consultório na Rua** (tese UNESP / PPGEP).  
Esta fase entrega: PostGIS, pipeline de Machine Learning (K-Means + KDE) e mapa Leaflet com heatmap das predições.

## Papéis

| Camada | Responsabilidade |
|--------|------------------|
| **Python** | IA: mock territorial, clustering, densidade e ingestão no PostGIS |
| **Java (Spring Boot)** | API + UI: lê predições e renderiza o mapa |
| **Docker / PostGIS** | Persistência espacial |

## Estrutura

```
ZonasCalor/
├── infra/docker-compose.yml
├── sql/
│   ├── init.sql                 # schema completo (instalação nova)
│   └── migrate_v2_ia.sql        # migração se o banco já existia
├── scripts/
│   ├── modelo_preditivo_ia.py   # pipeline ML (principal)
│   ├── gerar_mock_bauru.py      # CSV auxiliar (opcional)
│   ├── distance_matrix_service.py
│   └── requirements.txt
├── data/
├── sad-cnr/                     # Spring Boot + Thymeleaf + Leaflet
└── .env.example
```

## Pré-requisitos

- Docker Desktop
- Java 21 (`C:\Program Files\Java\jdk-21`)
- Maven 3.9+
- Python 3.11+

## Como rodar o ecossistema completo

### 1. Banco PostGIS

```powershell
cd c:\java\doutorado\ZonasCalor
copy .env.example .env
cd infra
docker compose up -d
```

Se o volume já existia (schema antigo), aplique a migração:

```powershell
Get-Content c:\java\doutorado\ZonasCalor\sql\migrate_v2_ia.sql | docker exec -i sad-cnr-postgis psql -U sad -d sad_cnr
```

### 2. Pipeline de IA (Python)

```powershell
cd c:\java\doutorado\ZonasCalor\scripts
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python modelo_preditivo_ia.py
```

O script gera ~500 pacientes em Bauru, calcula `probabilidade_ia` (KDE + vulnerabilidade), forma zonas com K-Means e grava em `pacientes_psr` e `zonas_calor_preditas`.

### 3. SAD visual (Spring Boot)

```powershell
$env:JAVA_HOME = "C:\Program Files\Java\jdk-21"
$env:Path = "$env:JAVA_HOME\bin;" + $env:Path
cd c:\java\doutorado\ZonasCalor\sad-cnr
mvn spring-boot:run
```

Abra: [http://localhost:8081](http://localhost:8081)

O frontend chama `GET /api/predicoes/heatmap` e plota o Leaflet.heat.

### Endpoints principais

| Método | URL | Descrição |
|--------|-----|-----------|
| `GET` | `/api/predicoes/heatmap` | `[[lat, lng, intensidade], ...]` (score IA) |
| `GET` | `/api/predicoes/zonas` | GeoJSON dos centroides das zonas |
| `GET` | `/api/predicoes/resumo` | Contagens pacientes/zonas |
| `GET` | `/api/pacientes/count` | Contagem (legado) |
| `POST` | `/api/upload-csv` | Upload CSV manual (opcional) |

## Modelo preditivo (resumo)

1. **Mock**: pontos com distribuição normal em torno de 4 epicentros em Bauru.  
2. **K-Means**: identifica aglomerados territoriais.  
3. **KDE**: estima densidade espacial; combina com vulnerabilidade → `probabilidade_ia` ∈ [0, 1].  
4. **Zonas**: polígonos (envelope) + centroide + intensidade média por cluster.

## OSRM (opcional — Fase 3)

Instruções de malha viária e matriz de distâncias permanecem em seções anteriores do repositório (`distance_matrix_service.py` + Geofabrik Sudeste).

## Fontes de dados reais

| Fonte | Link |
|-------|------|
| CadÚnico / VisData3 | https://aplicacoes.cidadania.gov.br/vis/data3/ |
| Microdados SAGI/MDS | https://www.gov.br/mds/pt-br/servicos/sagi/microdados |
| IPEA TD 2944 | https://repositorio.ipea.gov.br/entities/publication/82841974-8591-413b-8db7-1472520b53cb |

## Stack

- PostgreSQL 16 + PostGIS 3.4  
- Python: Pandas, Scikit-learn, SQLAlchemy  
- Java 21 / Spring Boot 3.3 / Hibernate Spatial / JTS  
- Thymeleaf + Leaflet + leaflet-heat  

## Licença acadêmica

Uso destinado à pesquisa de doutorado (UNESP). Dados sintéticos **não** representam indivíduos reais.
