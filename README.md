# SAD Consultório na Rua — Fase 1 (MVP Visual)

Sistema de Apoio à Decisão para otimização territorial do **Consultório na Rua** (tese UNESP).  
Esta fase entrega: banco espacial (PostGIS), dados sintéticos de Bauru-SP, API Spring Boot e mapa interativo com **heatmap** (Leaflet).

## Estrutura

```
ZonasCalor/
├── infra/docker-compose.yml     # PostGIS (+ OSRM opcional)
├── sql/init.sql                 # Schema espacial
├── scripts/
│   ├── gerar_mock_bauru.py      # Gera data/mock_pacientes.csv
│   ├── distance_matrix_service.py
│   └── requirements.txt
├── data/                        # CSV / matrizes geradas
├── sad-cnr/                     # Spring Boot (backend + UI)
└── .env.example
```

## Pré-requisitos

- Docker Desktop
- Java 21+
- Maven 3.9+
- Python 3.11+ (apenas para gerar o CSV mock)

## 1. Banco de dados (Docker)

```powershell
cd c:\java\doutorado\ZonasCalor
copy .env.example .env
cd infra
docker compose up -d
```

Aguarde o healthcheck. O script `sql/init.sql` cria as tabelas `pacientes_psr`, `bases_operacionais` e `historico_atendimentos` com índices GiST.

## 2. Gerar dados sintéticos (Python)

```powershell
cd c:\java\doutorado\ZonasCalor\scripts
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python gerar_mock_bauru.py
```

Saída: `data/mock_pacientes.csv` (~500 pontos em 4 clusters em Bauru).

## 3. Subir o SAD (Spring Boot)

```powershell
cd c:\java\doutorado\ZonasCalor\sad-cnr
mvn spring-boot:run
```

Abra: [http://localhost:8080](http://localhost:8080)

1. Selecione `data/mock_pacientes.csv`
2. Clique em **Importar e atualizar mapa**
3. As zonas de calor aparecem sobre o mapa de Bauru

### Endpoints

| Método | URL | Descrição |
|--------|-----|-----------|
| `POST` | `/api/upload-csv?limpar=true` | Importa CSV → PostGIS |
| `GET`  | `/api/pacientes/heatmap` | `[[lat, lng, intensidade], ...]` |
| `GET`  | `/api/pacientes/geojson` | FeatureCollection |
| `GET`  | `/api/pacientes/count` | Contagem |

## 4. OSRM (opcional — matriz de distâncias)

O Geofabrik **não publica extrato só de Bauru**. Use a malha do **Sudeste** (ou recorte com Osmium).

### Download

```powershell
cd c:\java\doutorado\ZonasCalor\infra\osrm-data
# ~850 MB — Sudeste/BR
curl.exe -L -o sudeste-latest.osm.pbf https://download.geofabrik.de/south-america/brazil/sudeste-latest.osm.pbf
```

### Processar e servir (Docker)

```powershell
cd c:\java\doutorado\ZonasCalor\infra

docker run -t -v "${PWD}/osrm-data:/data" ghcr.io/project-osrm/osrm-backend:latest `
  osrm-extract -p /opt/car.lua /data/sudeste-latest.osm.pbf

docker run -t -v "${PWD}/osrm-data:/data" ghcr.io/project-osrm/osrm-backend:latest `
  osrm-partition /data/sudeste-latest.osrm

docker run -t -v "${PWD}/osrm-data:/data" ghcr.io/project-osrm/osrm-backend:latest `
  osrm-customize /data/sudeste-latest.osrm

docker run -t -p 5000:5000 -v "${PWD}/osrm-data:/data" ghcr.io/project-osrm/osrm-backend:latest `
  osrm-routed --algorithm mld /data/sudeste-latest.osrm
```

Teste: [http://localhost:5000/route/v1/driving/-49.0606,-22.3149;-49.0720,-22.3250?overview=false](http://localhost:5000/route/v1/driving/-49.0606,-22.3149;-49.0720,-22.3250?overview=false)

### Matriz de custos (após importar pacientes)

```powershell
cd c:\java\doutorado\ZonasCalor\scripts
.\.venv\Scripts\Activate.ps1
python distance_matrix_service.py
```

Gera `data/matriz_distancias.json` (bases → clusters) para a Fase 3 (otimização).

> Dica: para acelerar o extract, recorte o PBF com [Osmium](https://osmcode.org/osmium-tool/) usando um polígono de Bauru antes do `osrm-extract`.

## Fontes de dados reais (próximos passos)

Dados oficiais agregados **não substituem** coordenadas de ponto de vivência (LGPD), mas calibram o mock e a validação:

| Fonte | Uso | Link |
|-------|-----|------|
| **CadÚnico / VisData3** | Séries de famílias em situação de rua | [aplicacoes.cidadania.gov.br/vis/data3](https://aplicacoes.cidadania.gov.br/vis/data3/) |
| **Microdados SAGI/MDS** | Bases amostrais desidentificadas; censo histórico PSR | [gov.br/mds — microdados](https://www.gov.br/mds/pt-br/servicos/sagi/microdados) |
| **IPEA TD 2944** | Diagnóstico CadÚnico / método de organização | [Repositório IPEA](https://repositorio.ipea.gov.br/entities/publication/82841974-8591-413b-8db7-1472520b53cb) |
| **SolicitaCad** | Base identificada (cessão formal + LGPD) | [gov.br — solicitar CadÚnico](https://www.gov.br/pt-br/servicos/solicitar-cessao-de-dados-identificados-do-cadastro-unico) |
| **Censo SUAS / Centros POP** | Capacidade da rede socioassistencial | Painéis MDS / Censo SUAS |

Para o mapa municipal, o caminho pragmático é: **parceria com a SMS/SUAS de Bauru** (e-SUS APS / prontuário CnR anonimizado) + calibração com totais do CadÚnico/IPEA.

## Stack

- PostgreSQL 16 + PostGIS 3.4  
- Java 21 / Spring Boot 3.3 / Hibernate Spatial / JTS  
- Thymeleaf + Leaflet + leaflet-heat  
- Python (Faker, NumPy, Pandas) para mock  
- OSRM (Table API) para matriz logística  

## Licença acadêmica

Uso destinado à pesquisa de doutorado (UNESP / PPGEP). Dados sintéticos **não** representam indivíduos reais.
