# Como funciona a Inteligência Artificial na Fase 1 do SAD

Este texto descreve, de forma direta, a Inteligência Artificial (IA) que o protótipo do **Sistema de Apoio à Decisão do Consultório na Rua** utiliza **neste momento**.

---

## 1. Em uma frase

A IA atual é um **modelo preditivo espacial não supervisionado**: ela observa onde as pessoas estão no mapa, agrupa essas localizações em “zonas” e calcula um **índice de prioridade territorial** (`probabilidade_ia`) que alimenta o mapa de calor.

Não se trata de chatbot, nem de modelo de linguagem (LLM). É **Machine Learning clássico** aplicado a coordenadas geográficas e ao grau de vulnerabilidade.

---

## 2. Por que usar IA nesta fase

O Consultório na Rua atua em território urbano dinâmico. Antes de otimizar escalas e rotas (Pesquisa Operacional), o sistema precisa responder:

> **Onde a concentração e a vulnerabilidade tendem a ser maiores, para orientar a presença das equipes?**

A IA da Fase 1 responde a essa pergunta produzindo:

- **clusters territoriais** (aglomerados);
- um **score contínuo** por ponto (`probabilidade_ia` entre 0 e 1);
- **zonas de calor** persistidas no banco e visualizadas no mapa.

Esses resultados serão, nas fases seguintes, a **demanda espacial** que alimentará os algoritmos de roteamento e alocação de turnos.

---

## 3. De onde vêm os dados que a IA processa

Hoje há dois caminhos:

1. **Dados sintéticos (fluxo acadêmico):** o próprio script gera cerca de 500 pontos em Bauru-SP, concentrados em epicentros (centro, terminal, zona sul, zona norte), com nível de vulnerabilidade de 1 a 5.
2. **Dados municipais (fluxo prefeitura):** CSV anonimizado importado pelo microserviço, com latitude, longitude e vulnerabilidade (e, opcionalmente, um score já calculado).

Em ambos os casos, a unidade básica de análise é um **ponto georreferenciado** (WGS84) associado a um indicador de vulnerabilidade.

---

## 4. As duas técnicas usadas

O pipeline está no arquivo `scripts/modelo_preditivo_ia.py` e combina duas técnicas do Scikit-learn.

### 4.1 K-Means — “onde se formam os aglomerados?”

O **K-Means** é um algoritmo de agrupamento (clustering). Ele recebe apenas as coordenadas `(longitude, latitude)` e particiona os pontos em **K grupos** (no protótipo, K = 4).

Intuição:

- pontos próximos no espaço tendem a cair no mesmo grupo;
- cada grupo representa um **polo territorial** de ocorrência;
- o centroide do grupo vira o marcador da “zona de calor” no mapa.

O K-Means **não** usa rótulos prévios (por isso é *não supervisionado*): ele descobre estrutura a partir da geometria dos pontos.

### 4.2 KDE (Kernel Density Estimation) — “quão denso é este lugar?”

A **Estimativa de Densidade por Kernel** modela a concentração espacial como uma superfície suave. Em termos simples:

- onde há muitos pontos próximos, a densidade estimada sobe;
- onde os pontos são esparsos, a densidade cai;
- a “largura de banda” (`bandwidth ≈ 0,008°`, da ordem de centenas de metros) controla o quão “espalhada” é essa suavização.

O KDE gera, para cada paciente, um valor de densidade. Esse valor é **normalizado** para a escala 0–1, para poder ser combinado com a vulnerabilidade.

---

## 5. O score final: `probabilidade_ia`

A IA não usa só densidade, nem só vulnerabilidade clínica. Ela calcula um **índice híbrido**:

\[
\text{probabilidade\_ia} = 0{,}65 \times \text{densidade\_normalizada} + 0{,}35 \times \left(\frac{\text{nível\_vulnerabilidade}}{5}\right)
\]

Interpretação dos pesos (versão atual do protótipo):

- **65%** — efeito da **concentração territorial** (KDE);
- **35%** — efeito da **vulnerabilidade** informada no cadastro (escala 1 a 5).

O resultado é limitado ao intervalo **[0, 1]**:

- valores próximos de **0** → menor prioridade relativa naquele ponto;
- valores próximos de **1** → maior prioridade relativa (mais “quente” no heatmap).

Esse nome (`probabilidade_ia`) deve ser lido, nesta fase, como **score preditivo de prioridade territorial**, e não como probabilidade clínica individual no sentido epidemiológico clássico. Quando houver dados reais e validação estatística, o significado poderá ser refinado (calibração, AUC, etc.).

---

## 6. Formação das “zonas de calor”

Depois do K-Means e do score:

1. Para cada cluster, o sistema agrega os pacientes do grupo.
2. Calcula a **intensidade média** (`média de probabilidade_ia`).
3. Calcula a **vulnerabilidade média**.
4. Monta um **polígono envelope** (área retangular expandida em torno dos pontos do cluster).
5. Calcula o **centroide** (ponto médio geográfico).
6. Grava tudo na tabela `zonas_calor_preditas`, com método rotulado como `KMEANS_KDE`.

No mapa:

- o **heatmap** usa os pontos com `probabilidade_ia` (manchas coloridas);
- os **círculos** marcam os centroides das zonas encontradas.

---

## 7. O que a IA **não** faz neste momento

Para evitar expectativas incorretas:

- não identifica pessoas (trabalha com IDs anonimizados);
- não diagnostica doenças;
- não otimiza rotas nem escalas (isso é Pesquisa Operacional, fases seguintes);
- não “conversa” nem gera texto;
- não substitui a decisão clínica ou a escuta do território — **apoia** a priorização espacial.

---

## 8. Como o resultado chega à tela

```text
Pontos (CSV ou sintéticos)
        │
        ▼
 K-Means  →  cluster_id (zonas)
 KDE      →  densidade
 Score    →  probabilidade_ia
        │
        ▼
   PostGIS (pacientes + zonas)
        │
        ▼
 API Spring Boot  /api/predicoes/heatmap
        │
        ▼
 Leaflet.heat (mapa no navegador)
```

O módulo Java **não treina** o modelo: ele apenas **lê** o que a IA já gravou e renderiza. A separação é deliberada: Python cuida da inteligência; Java cuida da aplicação e da visualização.

---

## 9. Importância científica e gerencial

Para a **tese**, esta IA:

- materializa a camada preditiva prometida no projeto (antecipar polos de vulnerabilidade);
- gera artefato demonstrável (MVP) para qualificação e para o **Artigo 1**;
- cria a entrada espacial que o **Artigo 2** (otimização NRP/VRP) consumirá.

Para a **gestão do CnR**, ela:

- torna visível, em minutos, onde a concentração relativa é maior;
- permite comparar cenários quando a base municipal for atualizada;
- reduz a dependência exclusiva do planejamento manual “no escuro”.

---

## 10. Limitações atuais (honestidade metodológica)

- Dados de demonstração ainda podem ser **sintéticos**.
- O número de clusters (K = 4) e os pesos 0,65 / 0,35 são **parametrizações iniciais**, sujeitas a calibração.
- O bounding box está configurado para **Bauru-SP**; outros municípios exigem ajuste.
- Validação com CadÚnico/IPEA/e-SUS e métricas formais de desempenho ainda farão parte da evolução da Fase 2.

---

## 11. Como executar de novo a IA

Com o PostGIS no ar:

```powershell
cd c:\java\doutorado\ZonasCalor\scripts
python modelo_preditivo_ia.py
```

Em seguida, no mapa (http://localhost:8081), use **Atualizar heatmap**.

---

## Referência de implementação

- Script: `scripts/modelo_preditivo_ia.py`
- Bibliotecas: `scikit-learn` (`KMeans`, `KernelDensity`), `numpy`, `pandas`, `SQLAlchemy`
- Persistência: tabelas `pacientes_psr` e `zonas_calor_preditas`
- Consumo visual: `GET /api/predicoes/heatmap`
