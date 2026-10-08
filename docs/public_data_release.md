# Data availability and source provenance / Disponibilidade dos dados e proveniência

## English

This repository is a **public portfolio release**, not a complete mirror of the private documentary research archive. It contains the author's processing code, derived analytical datasets, notebooks, SQL scripts, Power BI project, quality checks, visualizations and documentation. The underlying analytical results and sample definitions have not been altered for this release.

### Included

- `data/staging/financial_data_staging.xlsx`: structured extraction with original account labels, amounts, units, fiscal years and source filenames; **does not contain the original PDFs**.
- `data/processed/core_financials.csv`, `financial_fragility_scores.csv`, and `fragility_reference.csv`: harmonized financial CORE and retrospective fragility outputs.
- `data/processed/financial_sporting_data.csv`, `modeling_data_v1.csv`, and `modeling_data_v2.csv`: club-year-level analytical integration and labeled predictive datasets, including derived sporting features for the relevant clubs.
- `src/`, `notebooks/`, `tests/`, `sql/`, `scripts/`, `powerbi/`, `images/` and financial methodology documentation in `docs/`.

### Not redistributed

- **328 original third-party financial-statement PDFs** under `data/raw/clubs/` in the private research archive.
- `data/staging/sporting_data_staging.csv` and `data/processed/sporting_data.csv`, comprising the **complete 1,256-row competition-level sporting collection** in the private research archive.
- The private repository's commit history and its Git LFS objects.

The `source_file` values in the financial staging workbook identify source documents; those filenames are documentary references, not downloadable repository paths. Financial statements must be obtained independently from the clubs' or other authorized publishers' public disclosures where available.

The sporting inputs were collected from **CBF, RSSSF Brasil and UOL Esporte** (the last for Série B 2016), with source labels and URLs retained in the included integrated datasets where applicable. The full sporting tables are not mirrored here. Users seeking to recollect them should consult each provider's terms and attribution requirements. The code in `src/collect_sporting_data.py` does not grant rights to third-party content.

### Reproducibility

- The accepted financial staging, CORE build, financial EDA, fragility analysis and experiments from the integrated/modeling snapshots can be reproduced with the included files and stated software dependencies.
- `notebooks/04_build_sporting_dataset.ipynb` and `05_merge_financial_sporting.ipynb` require the omitted full competition-level sporting inputs to reproduce the **original source-to-merge pipeline**. Downstream notebooks use the included analytical datasets.
- A fresh manual audit of source-level financial extraction requires the original third-party statements, which are not included. Exact historical website responses and third-party content availability are not guaranteed.
- SQL Server and Power BI Desktop are needed to recreate the dashboard. The public Power BI project references a local SQL Server instance, which must be configured by the user.

This release does not claim ownership of the underlying third-party publications, original competition tables, publisher branding or content. No general reuse license is granted for those third-party materials by this repository.

## Português

Este repositório é a **versão pública de portfólio**, e não uma cópia integral do arquivo documental privado. Inclui código, bases analíticas derivadas, notebooks, scripts SQL, Power BI, testes, gráficos e documentação, sem alterar os resultados apresentados.

### Incluído

- `data/staging/financial_data_staging.xlsx`: extrações estruturadas com contas originais, valores, unidades e nomes dos documentos de origem, **sem os próprios PDFs**.
- `data/processed/core_financials.csv`, `financial_fragility_scores.csv` e `fragility_reference.csv`: CORE financeiro harmonizado e resultados de fragilidade.
- `data/processed/financial_sporting_data.csv`, `modeling_data_v1.csv` e `modeling_data_v2.csv`: integração analítica por clube-ano e bases preditivas, incluindo variáveis esportivas utilizadas nos experimentos.
- Código-fonte, notebooks, testes, SQL, Power BI, imagens e documentação metodológica.

### Não redistribuído

- **328 PDFs originais** de demonstrações financeiras de terceiros armazenados em `data/raw/clubs/` no arquivo privado.
- `data/staging/sporting_data_staging.csv` e `data/processed/sporting_data.csv`, correspondentes à coleção esportiva completa de **1.256 registros**.
- Histórico de commits e objetos Git LFS do repositório privado.

O campo `source_file` identifica o documento que fundamentou cada extração; o nome do arquivo não é um link para baixá-lo nesta versão. Para auditar diretamente as contas publicadas, é necessário obter os demonstrativos junto às fontes originais.

Os dados esportivos foram coletados de **CBF, RSSSF Brasil e UOL Esporte** (este último para a Série B de 2016). A proveniência é mantida nos registros analíticos distribuídos quando aplicável. Para uma nova coleta, devem ser observadas as condições de uso e atribuição de cada provedor; o código de coleta não concede direitos sobre o conteúdo externo.

### Reprodutibilidade

- É possível refazer o processamento desde o staging financeiro disponibilizado e executar as análises a partir das bases integradas e de modelagem incluídas.
- Os notebooks `04` e `05` exigem as tabelas esportivas completas que não são redistribuídas, para reproduzir **toda a sequência original de coleta e integração**. Os notebooks posteriores utilizam as bases analíticas disponibilizadas.
- A auditoria documental dos lançamentos depende do acesso às demonstrações de terceiros. A disponibilidade futura das páginas e arquivos externos não é garantida.
- A reprodução do dashboard exige SQL Server e Power BI Desktop, com configuração do ambiente local.

A versão pública não reivindica direitos sobre publicações, tabelas esportivas originais, marcas ou conteúdo de terceiros. Não se concede licença geral para redistribuição desses materiais por meio deste repositório.
