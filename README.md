# SAD Consultório na Rua — Fase 1

Sistema de Apoio à Decisão (SAD) para o **Consultório na Rua** (CnR), desenvolvido no doutorado em Engenharia de Produção (UNESP / PPGEP — Bauru).

Esta fase entrega a **fundação espacial + IA preditiva + importação municipal + MVP visual**, base para os próximos módulos de otimização (escalas e roteamento).

---

## Sumário rápido

| Item | Link / comando |
|------|----------------|
| Mapa de calor | http://localhost:8081 |
| Tela de importação | http://localhost:8081/importacao |
| Swagger do SAD | http://localhost:8081/swagger-ui.html |
| Swagger do microserviço | http://localhost:8090/docs |
| Contrato CSV (prefeitura) | [`docs/FORMATO_IMPORTACAO_DADOS.md`](docs/FORMATO_IMPORTACAO_DADOS.md) |
| Apresentação orientadora | [`docs/Apresentacao_Orientadora_Fase1_Artigos.pptx`](docs/Apresentacao_Orientadora_Fase1_Artigos.pptx) |

---

## O que a aplicação faz

Nesta Fase 1 a aplicação **ainda não otimiza rotas/escalas**. Ela:

1. **Importa** CSV anonimizado da prefeitura via **microserviço** (validação de contrato + PostGIS).
2. **Gera ou recalcula** predições com **Machine Learning** (K-Means + KDE) → `probabilidade_ia`.
3. **Persiste** pacientes e **zonas de calor** no PostGIS.
4. **Exibe** heatmap interativo (Leaflet) para apoiar a decisão territorial do CnR.
5. **Documenta** as APIs em **Swagger/OpenAPI** nos dois serviços HTTP.

### O que você vê nas telas

| Tela | Conteúdo |
|------|----------|
| **Mapa** (`/`) | Heatmap por `probabilidade_ia`, centroides das zonas IA, contadores, botão atualizar |
| **Importação** (`/importacao`) | Download do modelo CSV, upload, modos substituir/acrescentar, relatório de erros, status do microserviço |

### O que vem nas fases seguintes

- Nurse Rostering (escalas multidisciplinares)
- VRP / OSRM + solvers (roteamento)
- Integração oficial e-SUS / CadÚnico (com LGPD)

---

## Arquitetura

```text
 Prefeitura (CSV UTF-8, anonimizado)
              │
              ▼
 ┌────────────────────────────────┐
 │  Microserviço de Importação    │  FastAPI  :8090
 │  validação + carga PostGIS     │  Swagger: /docs
 └───────────────┬────────────────┘
                 │
                 ▼
          ┌─────────────┐
          │   PostGIS   │  :5432
          │ pacientes / │
          │ zonas calor │
          └──────▲──────┘
                 │
     ┌───────────┴───────────┐
     │                       │
     │ lê                    │ grava (batch IA)
     │                       │
 ┌───┴────────────────┐   ┌──┴──────────────────────┐
 │ SAD Visual         │   │ Pipeline IA             │
 │ Spring Boot :8081  │   │ modelo_preditivo_ia.py  │
 │ mapa + gateway     │   │ K-Means + KDE           │
 │ Swagger UI         │   └─────────────────────────┘
 └────────────────────┘
```

| Componente | Stack | Porta | Responsabilidade |
|------------|-------|-------|------------------|
| `import-service` | Python FastAPI | **8090** | Microserviço de importação CSV |
| `sad-cnr` | Java 21 / Spring Boot 3 | **8081** | SAD visual + gateway + Swagger |
| PostGIS | PostgreSQL 16 + PostGIS 3.4 | **5432** | Banco espacial |
| `modelo_preditivo_ia.py` | Scikit-learn | — | IA preditiva (job batch) |

> A porta **8080** costuma ficar ocupada pelo Docker Desktop neste ambiente; por isso o SAD usa **8081**.

---

## Pré-requisitos

1. **Docker Desktop** ligado  
2. **Java 21** (ex.: `C:\Program Files\Java\jdk-21`)  
3. **Maven 3.9+**  
4. **Python 3.11+** (para o pipeline de IA local; o microserviço também pode rodar via Docker)

---

## Passo a passo (do zero ao mapa)

### Passo 0 — Configurar ambiente

```powershell
cd c:\java\doutorado\ZonasCalor
copy .env.example .env
```

### Passo 1 — Subir PostGIS + microserviço de importação

```powershell
cd c:\java\doutorado\ZonasCalor\infra
docker compose up -d --build
```

Verificar:

```powershell
docker ps
curl.exe http://localhost:8090/health
curl.exe -o NUL -w "%{http_code}" http://localhost:8090/docs
```

Esperado:

- container `sad-cnr-postgis` **healthy**
- container `sad-cnr-import` em execução
- health `{"status":"ok","database":"up"}`
- Swagger do import em `/docs` respondendo **200**

**Alternativa** (microserviço fora do Docker):

```powershell
cd c:\java\doutorado\ZonasCalor\import-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8090
```

### Passo 2 — Popular dados

#### Opção A — Prefeitura (fluxo real)

1. Suba o SAD (Passo 3).
2. Abra http://localhost:8081/importacao  
3. Baixe o **modelo CSV**.  
4. Preencha conforme [`docs/FORMATO_IMPORTACAO_DADOS.md`](docs/FORMATO_IMPORTACAO_DADOS.md) (**sem** nome/CPF/CNS).  
5. Importe (Substituir ou Acrescentar).  
6. Abra o mapa e clique em **Atualizar heatmap**.

#### Opção B — Dados sintéticos + IA (fluxo acadêmico)

```powershell
cd c:\java\doutorado\ZonasCalor\scripts
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python modelo_preditivo_ia.py
```

O script gera ~500 pacientes em Bauru, aplica **K-Means + KDE**, grava `probabilidade_ia` e `zonas_calor_preditas`.

### Passo 3 — Subir o SAD (Spring Boot)

```powershell
$env:JAVA_HOME = "C:\Program Files\Java\jdk-21"
$env:Path = "$env:JAVA_HOME\bin;" + $env:Path
cd c:\java\doutorado\ZonasCalor\sad-cnr
mvn spring-boot:run
```

Aguarde `Started SadCnrApplication`.

### Passo 4 — Abrir as interfaces

| Interface | URL |
|-----------|-----|
| Mapa | http://localhost:8081 |
| Importação | http://localhost:8081/importacao |
| Swagger SAD | http://localhost:8081/swagger-ui.html |
| Swagger Import | http://localhost:8090/docs |
| ReDoc Import | http://localhost:8090/redoc |

---

## Inteligência Artificial (o que roda hoje)

| Técnica | Papel |
|---------|--------|
| **K-Means** | Descobre aglomerados territoriais (zonas) |
| **KDE** | Estima densidade espacial contínua |
| **Score híbrido** | `probabilidade_ia ≈ 0,65×densidade + 0,35×(vulnerabilidade/5)` |

- Implementação: `scripts/modelo_preditivo_ia.py`  
- Visualização: `GET /api/predicoes/heatmap` → Leaflet.heat  
- **Não** é chatbot/LLM: é ML não supervisionado para priorização territorial.

---

## Documentação Swagger / OpenAPI

| Serviço | Swagger UI | OpenAPI JSON | ReDoc |
|---------|------------|--------------|-------|
| SAD Spring Boot `:8081` | [/swagger-ui.html](http://localhost:8081/swagger-ui.html) | [/v3/api-docs](http://localhost:8081/v3/api-docs) | — |
| Import FastAPI `:8090` | [/docs](http://localhost:8090/docs) | [/openapi.json](http://localhost:8090/openapi.json) | [/redoc](http://localhost:8090/redoc) |

Tags no SAD: **Predições**, **Importação**, **Pacientes**.  
Tags no Import: **Saúde**, **Contrato**, **Importação**.

---

## Principais endpoints

### Microserviço (`:8090`)

| Método | Caminho | Descrição |
|--------|---------|-----------|
| `GET` | `/health` | Saúde do serviço e do banco |
| `GET` | `/api/v1/import/schema` | Contrato JSON |
| `GET` | `/api/v1/import/template/pacientes` | CSV modelo |
| `GET` | `/api/v1/import/template/bases` | CSV bases |
| `POST` | `/api/v1/import/pacientes` | Importa pacientes |
| `POST` | `/api/v1/import/bases` | Importa bases operacionais |

### Gateway / SAD (`:8081`)

| Método | Caminho | Descrição |
|--------|---------|-----------|
| `GET` | `/api/importacao/health` | Proxy health |
| `GET` | `/api/importacao/schema` | Proxy schema |
| `GET` | `/api/importacao/template` | Proxy template |
| `POST` | `/api/importacao/pacientes` | Proxy importação |
| `GET` | `/api/predicoes/heatmap` | `[[lat,lng,intensidade],...]` |
| `GET` | `/api/predicoes/zonas` | GeoJSON dos centroides |
| `GET` | `/api/predicoes/resumo` | Totais pacientes/zonas |
| `GET` | `/api/pacientes/count` | Contagem |

---

## Estrutura do repositório

```text
ZonasCalor/
├── docs/
│   ├── FORMATO_IMPORTACAO_DADOS.md      # contrato para prefeituras
│   └── Apresentacao_Orientadora_*.pptx  # slides da Fase 1 + 2 artigos
├── import-service/                      # microserviço FastAPI (+ Dockerfile)
├── infra/
│   └── docker-compose.yml               # PostGIS + import-service
├── sql/
│   ├── init.sql                         # schema inicial
│   └── migrate_v2_ia.sql                # migração bancos antigos
├── scripts/
│   ├── modelo_preditivo_ia.py           # pipeline ML
│   ├── gerar_mock_bauru.py
│   ├── distance_matrix_service.py       # preparação Fase 3 (OSRM)
│   └── gerar_apresentacao_orientadora.py
├── sad-cnr/                             # Spring Boot (UI + API + Swagger)
├── data/                                # artefatos locais (CSV etc.)
├── .env.example
└── README.md
```

---

## Credenciais e variáveis (desenvolvimento)

| Variável / serviço | Valor padrão |
|--------------------|--------------|
| PostGIS | `localhost:5432`, db `sad_cnr`, user `sad`, senha `sad123` |
| `IMPORT_SERVICE_URL` | `http://localhost:8090` |
| SAD | `http://localhost:8081` |
| Bounding box Bauru | lat `-22.40`…`-22.25`, lon `-49.15`…`-49.00` |

Arquivo de referência: `.env.example` (não versionar `.env` com segredos reais).

---

## Fluxo do dia a dia

| Objetivo | Ação |
|----------|------|
| Subir infra | `docker compose up -d --build` em `infra` |
| Regenerar predições sintéticas | `python scripts/modelo_preditivo_ia.py` |
| Importar CSV municipal | Tela `/importacao` ou Swagger `:8090/docs` |
| Reiniciar só a UI | `mvn spring-boot:run` em `sad-cnr` |
| Explorar APIs | Swagger `:8081` e `:8090` |

---

## Solução rápida de problemas

| Problema | Causa provável | Solução |
|----------|----------------|---------|
| Importação: microserviço indisponível | Container parado | `docker compose up -d --build` em `infra` |
| CSV rejeitado | Cabeçalho/coords/LGPD | Ver `FORMATO_IMPORTACAO_DADOS.md` |
| Mapa sem manchas | Banco sem dados | Importar CSV ou rodar pipeline IA |
| `Schema-validation` no Spring | Schema antigo | Rodar `sql/migrate_v2_ia.sql` |
| Porta 8081 em uso | Outra JVM | Encerrar processo Java anterior |
| `JAVA_HOME` em Java 8 | PATH antigo | Forçar JDK 21 no Passo 3 |
| Swagger 404 no SAD | App não subiu | Confirmar `Started SadCnrApplication` |

---

## Estratégia científica (resumo)

- **Artigo 1:** predição territorial / zonas de calor / DSS (Fases 1–2)  
- **Artigo 2:** otimização NRP + VRP integrada à demanda predita (Fases 3–5)  

Detalhes na apresentação em `docs/`.

---

## Licença acadêmica

Uso destinado à pesquisa de doutorado (UNESP — Câmpus de Bauru).  
Dados sintéticos **não representam** pessoas reais.  
Cargas municipais devem cumprir a **LGPD** (apenas identificadores anonimizados).
