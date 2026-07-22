# SAD Consultório na Rua — Fase 1

Sistema de Apoio à Decisão (SAD) desenvolvido no doutorado em Engenharia de Produção (UNESP / PPGEP) para apoiar a gestão logística do **Consultório na Rua** (CnR) no cuidado à População em Situação de Rua (PSR).

---

## O que a aplicação faz (exatamente)

Nesta Fase 1, a aplicação **não otimiza rotas ainda**. Ela entrega a **fundação territorial e preditiva** do SAD:

1. **Simula** a distribuição espacial de ~500 pessoas em situação de rua no município de **Bauru-SP** (dados sintéticos, enquanto os microdados reais do SUS/SUAS não estão disponíveis).
2. **Processa** esses pontos com Inteligência Artificial (aprendizado não supervisionado):
   - **K-Means** → identifica aglomerados (clusters) no território;
   - **KDE (Kernel Density Estimation)** → estima densidade espacial;
   - combina densidade + nível de vulnerabilidade → gera um score `probabilidade_ia` entre 0 e 1.
3. **Persiste** no PostGIS:
   - pacientes com coordenada e score preditivo;
   - **zonas de calor preditas** (polígono + centroide + intensidade média por cluster).
4. **Exibe** em um mapa interativo (Leaflet) as manchas de calor (heatmap) e os centroides das zonas, para o gestor visualizar onde a IA aponta maior concentração de vulnerabilidade.

### O que você vê na tela (`http://localhost:8081`)

| Elemento | Função |
|----------|--------|
| **Mapa de Bauru** | Malha urbana (OpenStreetMap) centrada em Bauru-SP |
| **Camada heatmap** | Manchas coloridas: azul/verde = menor intensidade; amarelo/vermelho = maior `probabilidade_ia` |
| **Marcadores das zonas** | Centroides dos clusters da IA; ao clicar, mostram intensidade, nº de pacientes e método |
| **Painel lateral** | Explica que os dados vêm do pipeline Python; botão **Atualizar heatmap** recarrega a API |
| **Contadores** | Total de pacientes e de zonas preditas no banco |

### O que a aplicação **ainda não** faz (fases seguintes)

- Otimização de escalas (Nurse Rostering)
- Roteamento de equipes (VRP / OSRM + solvers)
- Integração oficial com e-SUS APS / CadÚnico em produção

---

## Arquitetura (visão rápida)

```
┌─────────────────────┐     grava      ┌──────────────────┐     lê      ┌─────────────────────┐
│  Python (IA)        │ ─────────────► │  PostGIS         │ ◄───────── │  Spring Boot (SAD)  │
│  modelo_preditivo   │   pacientes +  │  pacientes_psr   │   REST     │  + Thymeleaf/Leaflet│
│  _ia.py             │   zonas calor  │  zonas_calor_*   │            │  mapa no navegador  │
└─────────────────────┘                └──────────────────┘            └─────────────────────┘
```

| Camada | Tecnologia | Responsabilidade |
|--------|------------|------------------|
| Infra | Docker + PostgreSQL 16 / PostGIS 3.4 | Banco espacial |
| IA | Python, Scikit-learn, SQLAlchemy | Mock + ML + ingestão |
| Backend | Java 21, Spring Boot 3, Hibernate Spatial | API e página web |
| Frontend | Thymeleaf, Leaflet, leaflet-heat | Visualização do heatmap |

**Não há microsserviços**: um monólito Java + um script Python batch + o banco.

---

## Pré-requisitos

Antes de começar, tenha instalado e funcionando:

1. **Docker Desktop** (ligado)
2. **Java 21** (ex.: `C:\Program Files\Java\jdk-21`)
3. **Maven 3.9+**
4. **Python 3.11+**

---

## Passo a passo — do zero até o mapa

### Passo 0 — Abrir o projeto

```powershell
cd c:\java\doutorado\ZonasCalor
```

Copie as variáveis de ambiente (credenciais do banco):

```powershell
copy .env.example .env
```

---

### Passo 1 — Subir o banco espacial (PostGIS)

```powershell
cd c:\java\doutorado\ZonasCalor\infra
docker compose up -d
```

Aguarde o container ficar **healthy**:

```powershell
docker ps
```

Você deve ver `sad-cnr-postgis` com status healthy na porta `5432`.

Na **primeira** subida, o arquivo `sql/init.sql` cria automaticamente:

- `pacientes_psr` (pontos + vulnerabilidade + `probabilidade_ia`)
- `zonas_calor_preditas` (clusters da IA)
- `bases_operacionais` e `historico_atendimentos` (preparação das fases seguintes)

Se o banco **já existia** com schema antigo, rode a migração:

```powershell
Get-Content c:\java\doutorado\ZonasCalor\sql\migrate_v2_ia.sql | docker exec -i sad-cnr-postgis psql -U sad -d sad_cnr
```

---

### Passo 2 — Rodar o pipeline de Inteligência Artificial

Este passo **popula o banco** com dados sintéticos e com as predições.

```powershell
cd c:\java\doutorado\ZonasCalor\scripts
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python modelo_preditivo_ia.py
```

**O que o script faz, em ordem:**

1. Gera ~500 pacientes com coordenadas dentro do bounding box de Bauru, concentrados em 4 epicentros (praça/centro, terminal, zona sul, zona norte).
2. Aplica **K-Means** (4 clusters) para descobrir aglomerados.
3. Aplica **KDE** para estimar densidade e calcula `probabilidade_ia`.
4. Monta polígonos/centroides das **zonas de calor**.
5. Grava tudo no PostGIS (substitui dados anteriores dessas tabelas).

Saída esperada no terminal (exemplo):

```text
Gerando pacientes sinteticos (Bauru-SP)...
  -> 500 pacientes
Aplicando K-Means + KDE...
  -> 4 zonas de calor preditas
Persistindo no PostGIS...
Concluido. Pacientes e zonas_calor_preditas atualizados.
```

> Sem este passo, o mapa abre, mas fica sem manchas de calor (banco vazio de predições).

---

### Passo 3 — Subir o Sistema Visual (Spring Boot)

Em um **novo** terminal PowerShell:

```powershell
$env:JAVA_HOME = "C:\Program Files\Java\jdk-21"
$env:Path = "$env:JAVA_HOME\bin;" + $env:Path
cd c:\java\doutorado\ZonasCalor\sad-cnr
mvn spring-boot:run
```

Aguarde a mensagem `Started SadCnrApplication`.

> A aplicação escuta na porta **8081** (a 8080 costuma estar ocupada pelo Docker Desktop neste ambiente).

---

### Passo 4 — Visualizar a tela

Abra o navegador em:

**http://localhost:8081**

1. O frontend chama automaticamente `GET /api/predicoes/heatmap`.
2. O Leaflet.heat desenha as zonas de calor.
3. Os centroides das zonas da IA aparecem como marcadores clicáveis.
4. Use **Atualizar heatmap** se tiver rodado o Python de novo com a página já aberta.

---

## Fluxo de uso no dia a dia

| Situação | O que fazer |
|----------|-------------|
| Primeira vez | Passos 1 → 2 → 3 → 4 |
| Só regenerar predições | Rodar de novo `python modelo_preditivo_ia.py` e clicar **Atualizar heatmap** |
| Reiniciar só a UI | `mvn spring-boot:run` no módulo `sad-cnr` |
| Reiniciar o banco | `docker compose up -d` em `infra` |
| Parar o banco | `docker compose down` em `infra` |

---

## APIs disponíveis

| Método | URL | O que retorna |
|--------|-----|----------------|
| `GET` | `/api/predicoes/heatmap` | Lista `[[lat, lng, intensidade], ...]` para o Leaflet.heat (usa `probabilidade_ia`) |
| `GET` | `/api/predicoes/zonas` | GeoJSON dos centroides das zonas preditas |
| `GET` | `/api/predicoes/resumo` | Totais de pacientes e zonas + nome da fonte do modelo |
| `GET` | `/api/pacientes/count` | Contagem de pacientes |
| `GET` | `/api/pacientes/geojson` | GeoJSON dos pacientes |
| `POST` | `/api/upload-csv` | Importação manual de CSV (opcional; o fluxo principal é o Python) |

---

## Estrutura do repositório

```text
ZonasCalor/
├── infra/
│   └── docker-compose.yml          # sobe o PostGIS
├── sql/
│   ├── init.sql                    # schema na 1ª instalação
│   └── migrate_v2_ia.sql           # migração para bancos antigos
├── scripts/
│   ├── modelo_preditivo_ia.py      # pipeline ML (passo principal de dados)
│   ├── gerar_mock_bauru.py         # gera CSV auxiliar (opcional)
│   ├── distance_matrix_service.py  # preparação Fase 3 (OSRM)
│   └── requirements.txt
├── data/                           # saídas locais (CSV/JSON; não versionar segredos)
├── sad-cnr/                        # aplicação Java (API + tela)
├── .env.example
└── README.md
```

---

## Credenciais padrão do banco (desenvolvimento)

Definidas em `.env.example` (e usadas pelo Docker / Spring / Python):

| Variável | Valor padrão |
|----------|--------------|
| Host | `localhost` |
| Porta | `5432` |
| Database | `sad_cnr` |
| Usuário | `sad` |
| Senha | `sad123` |

**Não** versionar o arquivo `.env` com senhas reais.

---

## Dados reais (próximos passos da pesquisa)

Os pontos atuais são **sintéticos**. Para calibração futura:

| Fonte | Uso |
|-------|-----|
| [CadÚnico / VisData3](https://aplicacoes.cidadania.gov.br/vis/data3/) | Totais agregados de famílias em situação de rua |
| [Microdados SAGI/MDS](https://www.gov.br/mds/pt-br/servicos/sagi/microdados) | Bases amostrais desidentificadas |
| [IPEA TD 2944](https://repositorio.ipea.gov.br/entities/publication/82841974-8591-413b-8db7-1472520b53cb) | Diagnóstico e método de análise CadÚnico |
| Parceria SMS / SUAS Bauru | Coordenadas operacionais anonimizadas do CnR (respeitando LGPD) |

---

## Solução rápida de problemas

| Problema | Causa provável | Solução |
|----------|----------------|---------|
| Mapa sem calor | Pipeline Python não rodou | Executar `modelo_preditivo_ia.py` |
| Erro de conexão JDBC | PostGIS parado | `docker compose up -d` em `infra` |
| Porta 8081 em uso | Outra instância Java | Encerrar o processo Java anterior e subir de novo |
| `Schema-validation` no Spring | Banco desatualizado | Rodar `migrate_v2_ia.sql` |
| `JAVA_HOME` aponta para Java 8 | PATH antigo | Forçar JDK 21 como no Passo 3 |
| Docker “connection refused” | Docker Desktop desligado | Abrir o Docker Desktop e esperar ficar Ready |

---

## Licença acadêmica

Uso destinado à pesquisa de doutorado (UNESP — Câmpus de Bauru).  
Os dados sintéticos **não representam** pessoas reais e não devem ser usados como estatística oficial.
