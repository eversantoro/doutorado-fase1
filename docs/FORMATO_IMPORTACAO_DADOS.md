# Formato de Importação de Dados — SAD Consultório na Rua

Documento destinado a **prefeituras, SMS, SUAS e equipes de TI** que desejem utilizar o protótipo do Sistema de Apoio à Decisão (SAD) para o Consultório na Rua.

Versão do contrato: **1.0**  
Encoding obrigatório: **UTF-8**  
Separador CSV: **vírgula (`,`)**  
Decimal: **ponto (`.`)** em latitude/longitude  
SRID geográfico: **EPSG:4326 (WGS84)**

---

## 1. Visão geral do fluxo

```text
Arquivo CSV da prefeitura
        │
        ▼
┌───────────────────────────┐
│  Microserviço de Importação│  (Python FastAPI — porta 8090)
│  - valida schema           │
│  - valida domínio/faixas   │
│  - valida coordenadas      │
│  - persiste no PostGIS     │
└───────────────────────────┘
        │
        ▼
   Banco PostGIS
        │
        ▼
┌───────────────────────────┐
│  SAD Visual (Spring Boot)  │  mapa / heatmap / gestão
└───────────────────────────┘
```

A tela **Importação** no SAD (`/importacao`) envia o arquivo ao microserviço.  
Após a carga, recomenda-se executar o pipeline de IA (`modelo_preditivo_ia.py`) **somente se** quiser recalcular clusters/zonas a partir dos pontos importados. Se o CSV já trouxer `probabilidade_ia`, o mapa pode exibir imediatamente.

---

## 2. Arquivo principal: pacientes PSR

### 2.1 Nome sugerido

`pacientes_psr_YYYYMMDD.csv`  
Exemplo: `pacientes_psr_20260722.csv`

### 2.2 Cabeçalho (obrigatório na 1ª linha)

```csv
id_anonimizado,sexo,faixa_etaria,nivel_vulnerabilidade,latitude,longitude,probabilidade_ia,data_referencia
```

Colunas **obrigatórias** e **opcionais**:

| Coluna | Obrigatória | Tipo | Domínio / regras |
|--------|-------------|------|------------------|
| `id_anonimizado` | Não* | texto ≤ 64 | Identificador **não nominativo**. Se vazio, o sistema gera um UUID. *Recomendado para reimportações idempotentes. |
| `sexo` | Não | texto | `M`, `F` ou `O`. Vazio permitido. |
| `faixa_etaria` | Não | texto ≤ 20 | Ex.: `0-17`, `18-29`, `30-44`, `45-59`, `60+`. |
| `nivel_vulnerabilidade` | **Sim** | inteiro | **1 a 5** (1=menor; 5=maior). |
| `latitude` | **Sim** | decimal | WGS84. Ex.: `-22.314900`. Faixa Brasil típica: `-33` a `5`. |
| `longitude` | **Sim** | decimal | WGS84. Ex.: `-49.060600`. Faixa Brasil típica: `-74` a `-34`. |
| `probabilidade_ia` | Não | decimal 0–1 | Score preditivo. Se omitido, o importador usa `nivel_vulnerabilidade / 5.0`. |
| `data_referencia` | Não | data `YYYY-MM-DD` | Data do cadastro/atendimento de referência (metadado; não grava coluna dedicada na v1 se ausente no schema — reservado para evolução). |

### 2.3 Exemplo válido (3 linhas)

```csv
id_anonimizado,sexo,faixa_etaria,nivel_vulnerabilidade,latitude,longitude,probabilidade_ia,data_referencia
PSR-A1B2C3D4,M,30-44,4,-22.314900,-49.060600,0.82,2026-07-01
PSR-E5F6G7H8,F,45-59,5,-22.320100,-49.055200,0.91,2026-07-01
PSR-I9J0K1L2,M,18-29,3,-22.330000,-49.070000,,2026-07-02
```

Na 3ª linha, `probabilidade_ia` vazia → o sistema assume `3/5 = 0.6`.

### 2.4 Regras de validação (rejeição de linha)

Uma linha é **rejeitada** (não impede o restante, salvo modo `strict`) quando:

1. Faltam `nivel_vulnerabilidade`, `latitude` ou `longitude`.
2. `nivel_vulnerabilidade` fora de 1–5.
3. Latitude/longitude não numéricas.
4. Coordenada fora do bounding box configurado do município (padrão Bauru; configurável).
5. `sexo` informado e diferente de `M`/`F`/`O`.
6. `probabilidade_ia` informada e fora de `[0, 1]`.
7. `id_anonimizado` duplicado **dentro do mesmo arquivo**.

### 2.5 Modos de carga

| Modo | Parâmetro | Comportamento |
|------|-----------|---------------|
| Substituir | `modo=substituir` (padrão na tela) | Apaga pacientes/zonas/histórico anteriores e carrega o arquivo. |
| Acrescentar | `modo=acrescentar` | Insere novos registros. Conflito de `id_anonimizado` → linha rejeitada. |
| Estrito | `strict=true` | Qualquer linha inválida **aborta** toda a importação (rollback). |

### 2.6 Limites técnicos (v1)

| Limite | Valor |
|--------|-------|
| Tamanho máximo do arquivo | 10 MB |
| Linhas máximas por arquivo | 50.000 |
| Extensão | `.csv` apenas |

---

## 3. Arquivo opcional: bases operacionais

Para cadastrar UBS, CAPS, sede do CnR etc.

### 3.1 Cabeçalho

```csv
nome,tipo,latitude,longitude,ativo
```

| Coluna | Obrigatória | Domínio |
|--------|-------------|---------|
| `nome` | Sim | texto ≤ 120 |
| `tipo` | Sim | ex.: `UBS`, `CAPS`, `CNR`, `CRAS`, `CENTRO_POP` |
| `latitude` / `longitude` | Sim | WGS84 |
| `ativo` | Não | `true`/`false` (padrão `true`) |

Endpoint: `POST /api/v1/import/bases` no microserviço.

---

## 4. Privacidade e LGPD (obrigatório ler)

1. **Não envie nome, CPF, CNS, endereço residencial completo ou telefone.**
2. Use apenas `id_anonimizado` gerado pela prefeitura (hash/UUID interno).
3. Coordenadas devem refletir **ponto de vivência/abordagem operacional**, não documento civil.
4. Preferir agregação temporal (ex.: última abordagem do mês) quando possível.
5. O protótipo é acadêmico; implantação municipal exige DPIA, termo de uso e base legal (LGPD).

---

## 5. Bounding box padrão (Bauru-SP)

Configurável por variáveis de ambiente no microserviço:

| Variável | Padrão |
|----------|--------|
| `IMPORT_MIN_LAT` | `-22.40` |
| `IMPORT_MAX_LAT` | `-22.25` |
| `IMPORT_MIN_LON` | `-49.15` |
| `IMPORT_MAX_LON` | `-49.00` |

Para outro município, ajuste esses valores **antes** da importação.

---

## 6. API do microserviço de importação (Swagger)

Base URL padrão: `http://localhost:8090`

**Documentação interativa (Swagger UI):** [http://localhost:8090/docs](http://localhost:8090/docs)  
**ReDoc:** [http://localhost:8090/redoc](http://localhost:8090/redoc)  
**OpenAPI JSON:** [http://localhost:8090/openapi.json](http://localhost:8090/openapi.json)

Gateway documentado no SAD: [http://localhost:8081/swagger-ui.html](http://localhost:8081/swagger-ui.html)

| Método | Caminho | Descrição |
|--------|---------|-----------|
| `GET` | `/health` | Saúde do serviço |
| `GET` | `/api/v1/import/schema` | JSON do contrato (colunas, tipos, regras) |
| `GET` | `/api/v1/import/template/pacientes` | Download do CSV modelo |
| `POST` | `/api/v1/import/pacientes` | Multipart: `file` + `modo` + `strict` |
| `POST` | `/api/v1/import/bases` | Multipart: `file` |

### 6.1 Exemplo de resposta de sucesso

```json
{
  "status": "ok",
  "modo": "substituir",
  "recebidas": 520,
  "importadas": 500,
  "rejeitadas": 20,
  "erros": [
    {"linha": 14, "motivo": "nivel_vulnerabilidade fora de 1..5"},
    {"linha": 88, "motivo": "coordenada fora do bounding box municipal"}
  ],
  "total_banco": 500
}
```

---

## 7. Integração com a tela do SAD

1. Abra `http://localhost:8081/importacao`.
2. Baixe o **modelo CSV**.
3. Preencha com dados anonimizados da prefeitura.
4. Selecione o arquivo e o modo (Substituir / Acrescentar).
5. Clique em **Importar**.
6. Confira o relatório (importadas × rejeitadas).
7. Vá ao **Mapa** (`/`) e atualize o heatmap.

O SAD Java encaminha o upload ao microserviço (`IMPORT_SERVICE_URL`), sem misturar regra de validação no monólito visual.

---

## 8. Checklist da prefeitura

- [ ] CSV em UTF-8 com cabeçalho exatamente como no template  
- [ ] Sem dados pessoais identificáveis  
- [ ] Vulnerabilidade 1–5 preenchida  
- [ ] Lat/lon em WGS84 dentro do município  
- [ ] Microserviço de importação no ar (`:8090`)  
- [ ] PostGIS no ar (`:5432`)  
- [ ] Teste com arquivo pequeno (10–20 linhas) antes da carga completa  

---

## 9. Contato técnico do protótipo

Projeto acadêmico — UNESP / PPGEP (Bauru).  
Repositório e README do ecossistema: raiz do projeto `ZonasCalor`.
