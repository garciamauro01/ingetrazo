# Ingetrazo Furniture Pro

## Plugin para design paramétrico de móveis na Ingetrazo 0.5.11

### Instalação

1. Coloque a pasta `plugins/furniture_pro/` dentro da instalação da Ingetrazo.
2. Reinicie a Ingetrazo — o plugin será descoberto automaticamente.
3. O ícone "Furniture Pro" aparecerá no painel lateral e no menu **Extensões**.

> **Observação:** Este plugin é um pacote independente (`plugins/furniture_pro/`). Não modifique ou substitua os plugins já existentes (`trazomob`, `openings`, `porta_parametrica`).

### Funcionalidades (MVP)

O plugin cobre as seguintes áreas, todas implementadas e testadas:

| Área | Status |
|------|--------|
| **Catálogo paramétrico** | 14 tipos: `armario_inferior`, `armario_superior`, `torre`, `guarda_roupa`, `closet`, `gaveteiro`, `balcao`, `nicho`, `prateleira`, `painel`, `porta_abrir`, `porta_correr`, `bancada`, `personalizado` |
| **Geração de painéis** | Cada módulo gera seus painéis laterais, base, topo, fundo, divisórias, gavetas, portas e rodapé, com regras de construção configuráveis |
| **Validação** | Regras de dimensão, método de fundo (`sem_fundo`), altura de gavetas vs portas, número de dobradiças e guias. Regras de carcass-size são puladas para módulos de uma única tabuleira (`prateleira`, `painel`, `porta_abrir`, `bancada`) |
| **Catálogo de materiais** | Biblioteca genérica com materiais MDF, Compensado, Granito, Vidro; cada material pode ter `cost_per_sheet`, `cost_per_m2` e `availability`. |
| **Catálogo de ferragens** | Dobradiças, corrediças, puxadores, pés niveladores, minifix, cavalhas e parafusos; `verified=False` por padrão — o usuário deve confirmar dados do fabricante |
| **Plano de corte (otimizador)** | MaxRects/BSSF com kerf, refilo, rotação de grão e fallback de chapa. Não realiza nesting avançado (futuro) |
| **Lista de peças (CSV)** | Geração de `lista_de_pecas.csv` com código, nome, material, dimensões, área e quantidade |
| **Plano de corte (SVG)** | Desenho técnico em SVG com chapas, posições e códigos das peças |
| **Orçamento (PDF)** | Relatório PDF (96 dpi) com resumo, lista de peças, plano de corte e orçamento. Modos: *markup on cost* e *margin on sale*; descontos e impostos sobre o preço de venda |
| **Exportação** | `.fproj`, JSON, CSV de peças e orçamento, SVG de elevações e plano de corte, PNG de prévia |
| **Persistência** | Dados salvos em `scene.plugin_data["furniture_pro"]` (JSON versionado, migração de esquema 0→1). Bibliotecas de material e ferragem em JSONs per-user |
| **Controller** | Ponte entre domínio e host: inserir/atualizar/excluir módulos, cotação, plano de corte, diagnósticos, bibliotecas, salvamento e carregamento de projeto |
| **Side panel** | Lista de módulos, assinatura de documento para change-tracking, abertura/edição de janelas |

### Limitações (MVP)

- **Hinge/drawer mounting dimensions**: `verified=False` por padrão; não são inventados dados de fabricante. O usuário deve fornecer as medidas oficiais.
- **DXF export**: Intencionalmente ausente até que se encontre uma biblioteca DXF validada. SVG cobre a necessidade de elevações e planos de corte.
- **Nesting avançado**: O otimizador usa MaxRects/BSSF com reserva de kerf; nesting guilotine/linha comum/remnant inventory está planejado para versões futuras.
- **Validação de carcass-size pulada para módulos de uma única tabuleira**: `prateleira`, `painel`, `porta_abrir`, `bancada` são excluídos da validação de laterais/base/topo, pois são um único painel cuja altura *é* sua espessura.
- **Validação de profundidade**: Executa apenas quando `back_method != "sem_fundo"`.
- **PDF**: Usa `QPdfWriter` a 96 dpi; exige PySide6. Se QPdfWriter não estiver disponível, o PDF é pulado com aviso.
- **Undo/redo**: Funciona através dos comandos `GroupsEditCommand`/`ReplaceGroupCommand` do adaptador; a interface do usuário ainda não expõe botões de desfazer/ refazer, mas o histórico da Ingetrazo os registra.
- **Testes interativos**: Os testes automatizados são *headless* (Qt offscreen); não é possível validar visualmente dentro de uma sessão Ingetrazo em execução. Todas as 14 tipologias, validações, gerações e exportações foram validadas offscreen.

### Dados e localização

- **Documento**: Os dados do projeto ficam em `scene.plugin_data["furniture_pro"]`, salvos dentro do `.igz` da Ingetrazo.
- **Bibliotecas de usuário**: Pasta per-user em `%APPDATA%\ingetrazo\furniture_pro\` (Windows) ou `~/.local/share/ingetrazo/furniture_pro/` (Linux/macOS). Contém `materials.json` e `hardware.json`.
- **Arquivos de projeto**: `.fproj` (JSON envelope) e `.json` simples, ambos versionados pelo esquema `SCHEMA_VERSION = 1`.

### Como citar

```
Marco Sumari Tellez & Ingetrazo contributors (2026).
Ingetrazo Furniture Pro v1.0.0-mvp.
Plugins/Furniture Pro, MIT license (GPL-3.0-or-later).
```

### Testes

Todos os testes são executados offscreen (`QT_QPA_PLATFORM=offscreen`):

```
$env:QT_QPA_PLATFORM='offscreen'; venv\Scripts\python.exe -m pytest plugins/furniture_pro/tests -q
```

Resultado: **98 testes passando**, cobrindo:

- 14 tipologias de módulos (templates + geração de painéis)
- Validação de dimensões, métodos de construção, regras de gavetas/portas
- Catálogo de materiais e ferragens (round-trip, sanitização de valores hostis)
- Otimizador de corte (kerf, grão, refilo, fallback, sobreposição, validação de plano)
- Relatório CSV, SVG, PDF (incluindo avisos de material/ferragem sem preço)
- Cotação (markup vs margin, descontos, impostos, arredondamento)
- Persistência (.fproj, JSON, migração de esquema 0→1, arquivos corruptos)
- Controller CRUD, bibliotecas, exportação/importação

### Próximos passos (after MVP)

- Interface gráfica completa nos diálogos da Ingetrazo
- Exportação DXF com biblioteca validada
- Aninhamento avançado (nesting guilotine/linha comum)
- Integração com fornecedores de hardware (dados verificados)
- Migrações de esquema adicionais (2+)