# Arquitetura do TrazoMob

Este documento descreve como o plugin está organizado atualmente e as decisões
que sustentam essa organização. Ele é a referência para novas contribuições:
onde colocar cada arquivo, quais camadas podem depender de quais e o que não
deve ser alterado sem necessidade.

## Estado atual

O ponto de entrada público é `__init__.py`. Ele expõe a API (`__all__`), as
classes de ferramenta descobertas pelo carregador do IngeTrazo (`TrazoMobTool`
e `CabinetInteractTool`) e o `setup(app)`.

O corpo do `setup` foi separado para manter o módulo-raiz enxuto:

- `bootstrap.py`: instala o plugin no host — painel lateral, barra de
  ferramentas, outliner, pickables, overlay, ação de menu e menu de contexto;
- `context_menu.py`: monta o menu de contexto do viewport.

O código restante está separado em subpacotes por responsabilidade. A raiz
contém apenas a entrada pública, documentação, assets, scripts de apoio e
testes.

## Fluxo de carregamento

1. O IngeTrazo descobre as subclasses de `Tool` cujo `__module__` é
   `ingetrazo_plugin_trazomob` (por isso `TrazoMobTool` e `CabinetInteractTool`
   vivem em `__init__.py`).
2. `setup(app)` delega para `bootstrap.install(app, TrazoMobTool,
   CabinetInteractTool)`.
3. `bootstrap.install` cria o `TrazoMobSidebarPanel`, registra o painel, a
   toolbar, o outliner, o overlay de luzes, os pickables e o menu de contexto.
4. `builders/registry.py` resolve o construtor de cada tipo de módulo; o
   `CabinetBuilder` apenas orquestra as delegações.

## Responsabilidades

| Área | Responsabilidade |
| --- | --- |
| `__init__.py` | Fachada pública: API, ferramentas descobertas pelo host e `setup`. |
| `bootstrap.py` | Instalação no host (painel, toolbar, outliner, overlay, menus). |
| `context_menu.py` | Menu de contexto do viewport. |
| `domain/` | Catálogo, geometria paramétrica, metadados, preferências, ambientes, ferragens e i18n. Sem dependência de UI. |
| `builders/` | Construção das malhas e peças dos módulos, esquadrias, chapas e ferragens 3D. |
| `wall/` | Paredes 2D/3D, planta baixa, seleção de faces, guias e pintura. |
| `interaction/` | Ferramentas interativas, arraste magnético, colisão, alinhamento e cinemática de portas/gavetas. |
| `production/` | Extração de peças, usinagem, nesting, etiquetas, exportações (CSV/JSON/DXF), precificação, relatórios e manual de montagem. |
| `render/` | Iluminação, PBR e renderização foto-realista. |
| `profiles/` | Biblioteca e editor de perfis de alumínio. |
| `ui/` | Sidebar, ribbons, galerias, ícones, estilos e diálogos. |
| `integrations/` | Camada anticorrupção e ganchos de runtime com o host IngeTrazo. |
| `assets/` | Catálogos, i18n, perfis, amostras, texturas e miniaturas. |
| `blender_scripts/` | Scripts executados dentro do Blender (render foto-realista). |
| `scripts/` | Utilitários de empacotamento e geração de cenas de demonstração. |
| `docs/` | Manuais e documentos de arquitetura. |
| `tests/` | Suíte de testes do plugin. |

## Estrutura atual

```text
trazomob/
├── __init__.py              # API pública, ferramentas e setup()
├── bootstrap.py             # instalação no host
├── context_menu.py          # menu de contexto
├── assets/
│   ├── components/          # biblioteca de componentes
│   ├── i18n/                # en.json, es.json
│   ├── profiles/            # perfis de alumínio
│   ├── samples/             # cenas .igz de exemplo
│   ├── textures/            # texturas PBR
│   └── thumbs/              # miniaturas
├── blender_scripts/
│   └── photoreal_render.py
├── builders/
├── domain/
├── docs/
├── integrations/
├── interaction/
├── production/
├── profiles/
├── render/
├── scripts/
├── tests/
├── ui/
└── wall/
```

`domain/` é usado no lugar de `core/` para não sombrear o pacote `core/` do
IngeTrazo quando o diretório do plugin está no caminho de importação do Python.

## Camada de domínio (`domain/`)

| Módulo | Responsabilidade |
| --- | --- |
| `catalog.py` | `MODULE_CATALOG` (catálogo estático) e catálogo pessoal do usuário. |
| `module_geometry.py` | Geometria dos módulos, alinhamento espacial e parâmetros padrão; reexporta os utilitários compartilhados. |
| `module_utils.py` | Contratos usados por builders, interação, UI e host: `is_esquadria`, `resolve_igz_path` e `shift_module_geometry`. |
| `param_mapper.py` | Coleta parâmetros da UI (`extract_ui_module_params`) e repopula o formulário (`populate_ui_from_module`). |
| `schema.py` | Fonte única de verdade dos metadados em `group.ext["trazomob"]`. |
| `entity.py` | Leitura/escrita padronizada desses metadados. |
| `hardware.py` | `HardwareItem`, `HARDWARE_CATALOG`, inferência, serialização e consolidação de ferragens. |
| `preferences.py` | Preferências persistentes (singleton) em JSON. |
| `ambiente.py` | Entidades **Ambiente** e **Pavimento**. |
| `assembly.py` | Agrupamento/desagrupamento seguro de módulos (assemblies). |
| `auto_layout.py` | Preenchimento automático de paredes. |
| `materials_catalog.py` | Catálogo de materiais e texturas de MDF e marmoraria. |
| `i18n.py` | Tradução do plugin, sincronizada com `core.i18n.current_language()`. |
| `migration.py` | Compatibilidade retroativa e auto-migração de metadados. |

Regra: `domain/` não importa `ui/`, `builders/` nem `wall/`.

## Builders e o Registry Pattern

`builders/registry.py` registra um construtor por tipo de módulo com
`@register_module_builder(...)`. O `CabinetBuilder` não contém mais cadeias
monolíticas de `if/elif`: ele resolve o construtor no registry e delega.

Os builders foram divididos por família. **Os módulos com nomes em inglês são a
fonte de verdade**; os arquivos antigos em português permanecem apenas como
*shims* de compatibilidade (reexportação de uma linha), para não quebrar
imports legados:

| Implementação (fonte de verdade) | Shim legado |
| --- | --- |
| `base_wall_cabinets.py` | `balcoes_aereos.py` |
| `wall_tall_cabinets.py` | `aereos_torres.py` |
| `wardrobes.py` | `armarios.py` |
| `corner_cabinets.py` | `cantos_especiais.py` |
| `beds.py` | `camas.py` |
| `countertops.py` | `bancadas.py` |
| `fillers.py` | `fechamento.py` |
| `fronts.py` | `frentes.py` |

Complementos:

- `cabinet.py` compõe `cabinet_transform.py` (transformações),
  `cabinet_caixa.py` (caixa), `cabinet_module_group.py` (grupo do módulo) e
  `cabinet_delegates.py` (fachadas dos builders especializados);
- `chapa_builder.py` / `chapa_spec.py`: chapa canônica e herança de material e
  fitamento;
- `hardware_geometry.py`: representação 3D esquemática das ferragens;
- `mesh_utils.py`, `mirror.py`, `parts.py` e `tamponamento_linha.py`:
  utilidades de malha, espelhamento, peças e tamponamento;
- `esquadrias.py`: fachada pública `EsquadriaBuilder`, com a implementação
  dividida em `esquadrias_parametric.py` (portas/janelas geradas por
  parâmetros), `esquadrias_native.py` (modelos `.igz` reais e cinemática) e
  `esquadrias_common.py` (paleta, cache e reexports). Nenhum chamador precisa
  mudar: os nomes públicos e as assinaturas permanecem idênticos.

## Esquadrias: manifesto único e modelos reais

Portas e janelas **não** são módulos de marcenaria: seus modelos vêm de `.igz`
reais, com malha e texturas preservadas. As regras abaixo são contrato:

- `assets/catalog/esquadrias.json` é a fonte única de verdade. O loader
  `assets/catalog/__init__.py` valida o manifesto na importação (schema, ids
  duplicados, subpastas, papéis de cinemática e índices de folha) e fornece
  catálogo, resolução de arquivo, folhas e cinemática. Nenhuma tabela é
  repetida em código.
- Os arquivos ficam em `assets/components/portas/` e
  `assets/components/janelas/`. A subpasta é decidida pelo prefixo do id e é
  definitiva: **não existe** busca em outras pastas, geometria procedural de
  fallback nem leitura manual alternativa.
- `domain/module_utils.resolve_igz_path` devolve sempre o caminho canônico.
  Se o arquivo não existir, `load_esquadria_igz` levanta `FileNotFoundError`
  com `Modelo .igz de esquadria não encontrado para '<id>': <caminho>`.
- `is_esquadria` (grupo **ou** id) e `shift_module_geometry` também vivem em
  `domain/module_utils`. `domain/module_geometry.py` e
  `interaction/magnetic_drag_snap.py` reexportam os mesmos objetos; o hook
  `integrations/host_calls.scale_factor_override` usa a função compartilhada.
- `integrations/host_calls.before_move_commit` é deliberadamente um no-op
  documentado: o `MoveTool` do host é o único dono do modo cópia (`on_key`,
  `on_key_release`/`ctrl_tapped` e `_reset`).

### Miniaturas

A galeria usa `assets/thumbs/esquadrias/<id>.png`; quando não há arquivo, cai
para a miniatura vetorial genérica em `ui/thumbnails.py`. A auditoria é
somente leitura:

```bash
python -m trazomob.scripts.audit_esquadria_thumbs
```

Os PNGs dos modelos que antes não tinham imagem própria foram gerados a partir
da geometria real de cada `.igz`, com o mesmo projetor vetorial da bandeja de
componentes, pelo comando abaixo. Ele **nunca sobrescreve** um PNG existente
(só regera com `--force`):

```bash
python -m trazomob.scripts.generate_esquadria_thumbs
```

Estado atual: 34 modelos no catálogo, **34 com miniatura própria**, nenhum com
ícone genérico e 5 PNGs legados com sufixo de largura (`porta_giro_80.png`,
`porta_aluminio_90.png`, ...) que não correspondem a nenhum id e portanto não
são usados. Nenhum PNG existente é alterado ou removido sem aprovação
explícita.

## UI e a sidebar

`ui/sidebar_panel.py` é uma fachada que compõe mixins. Assim como nos builders,
os controllers novos em inglês são a fonte de verdade e os antigos em português
são shims:

| Implementação (fonte de verdade) | Shim legado |
| --- | --- |
| `sidebar_adjustments_controller.py` | `sidebar_ajustes_controller.py` |
| `sidebar_dimensions_controller.py` | `sidebar_medidas_controller.py` |
| `sidebar_fronts_controller.py` | `sidebar_frentes_controller.py` |
| `sidebar_handles_controller.py` | `sidebar_puxadores_controller.py` |
| `sidebar_materials_controller.py` | `sidebar_materiais_controller.py` |

Outros controllers: `sidebar_actions`, `sidebar_apply`, `sidebar_scene`,
`sidebar_wall`, `sidebar_esquadria`, `sidebar_fit`, `sidebar_interact`,
`sidebar_light` e `sidebar_align`.

O diálogo de módulos segue a mesma divisão: `module_dialog.py` compõe
`module_dialog_build`, `sections`, `options`, `form`, `actions`, `style` e
`hardware`. A galeria (`module_gallery.py`) e o ribbon (`module_ribbon.py`)
consomem o catálogo estático e os módulos do usuário.

Diálogos e apoio: `pricing_dialog.py`, `proposal_dialog.py`,
`assembly_manual_dialog.py`, `material_editor_dialog.py`,
`ruler_editor_dialog.py`, `icons.py`, `styles.py` e `thumbnails.py`.

## Camada de produção (`production/`)

| Módulo | Responsabilidade |
| --- | --- |
| `parts.py` | Extrai e agrupa peças da cena; carrega `operacoes`, `_module_key`, `module_hardware`, `ambiente` e `pavimento`. |
| `machining.py` | Modelos de furação/usinagem (caneco, minifix, cavilha, rasgo de fundo, sistema 32). |
| `joint_resolver.py` | Detecta encontros entre peças e sincroniza as usinagens de junta. |
| `optimizer.py` | Nesting 2D (guilhotina/best-fit), kerf, refilo e sentido do veio; expõe `resumo_aproveitamento` (aproveitamento e sobras por material e totais). |
| `cut_plan_viewer.py` | Visualizador 2D interativo do plano de corte, com aproveitamento e sobras. |
| `labels.py` | Etiquetas técnicas prontas para impressão. |
| `barcode.py` | Code 128 nativo (conjuntos A/B/C, checksum módulo 103). Sem dependência externa. |
| `qr.py` | QR Code nativo (modo byte, correção M, versões 1–6). Sem dependência externa. |
| `export.py` | Exportação da cutlist em texto, CSV e JSON. |
| `dxf_cnc.py` | Exportação de usinagens e plano de corte em DXF R12 para CAM. |
| `pricing.py` | Motor de precificação/orçamento (custo direto, markup, impostos, desconto, frete). |
| `report.py` | Relatório de produção, orçamento técnico e proposta comercial (HTML/PDF). |
| `html_report.py` | Relatório executivo HTML com quebra por ambiente/pavimento. |
| `assembly_manual.py` | Manual de montagem em HTML, agrupado por módulo, com ferragens e usinagens. |
| `cutlist_tab.py` | Aba de lista de corte e ponto de entrada dos diálogos de produção. |

As etiquetas usam um payload estável (`label_payload`/`stable_piece_code`), de
modo que a mesma peça gera sempre o mesmo código de barras. O Code 128 e o QR
são implementados no próprio plugin: não adicionar `qrcode`, `segno`, `PIL` ou
leitor externo como dependência de runtime.

## Catálogo e preferências do usuário

- `MODULE_CATALOG` permanece estático e versionado.
- Os módulos pessoais ficam em `preferences["user_modules"]` e aparecem na
  categoria virtual `USER_MODULE_CATEGORY` ("⭐ Meus Módulos").
- Helpers em `domain/catalog.py`: `modulos_usuario()`, `iter_modulos_todos()`,
  `buscar_modulo()` e `build_user_module()` (gera `id` único em inglês/slug e
  preserva as flags do item de catálogo de origem).
- A UI oferece salvar o módulo atual em **Meus Módulos** pela sidebar, e a
  galeria/ribbon mesclam catálogo estático + módulos do usuário.

### Preferências persistentes

Arquivo JSON em `%LOCALAPPDATA%/IngeTrazo` (Windows) ou
`~/.config/ingetrazo` (Linux/macOS), via `get_preferences_file_path()`.
Seções:

| Seção | Conteúdo |
| --- | --- |
| `global` | Padrões de marcenaria (espessuras, materiais, fita, puxadores, fixação). |
| `module_defaults` | Dimensões padrão por categoria/tipo de módulo. |
| `wall_guides` | Presets, visibilidade e snap das réguas/linhas-guia. |
| `user_modules` | Catálogo pessoal do usuário. |
| `pricing` | Preços de chapas, markup, impostos e PIN (PBKDF2-HMAC-SHA256 com salt). |

`TrazoMobPreferencesManager` é singleton; os testes devem redirecionar
`get_preferences_file_path` para um arquivo temporário e zerar `_instance`.

## Internacionalização

`domain/i18n.py` carrega `assets/i18n/<lang>.json` (`en.json`, `es.json`) e
sincroniza com o idioma atual do IngeTrazo. Novos textos de UI devem usar `tr()`
e ter entrada nos catálogos.

## Integração com o host (`integrations/`)

- `platform.py`: camada anticorrupção. É o **único** lugar onde o plugin toca
  APIs do host que ainda não são públicas (geometria, histórico, viewport,
  `.igz`, catálogo de componentes);
- `hooks.py`: ganchos de runtime, sempre na ordem API oficial → adaptação →
  fallback defensivo.

## Qualidade de código e tooling

O plugin mantém repositório Git próprio
(`https://github.com/garciamauro01/trazomob`) e, por isso, tem tooling local:

- `pyproject.toml`: configuração do Ruff — `line-length = 120`, alvo `py311`,
  regras `E`, `F`, `W` e `I`. Algumas regras legadas são toleradas
  explicitamente ("ratchet": `E501`, `F401`, `I001`, `F811`, `F841`, `E701`,
  `E702`, `E402`, `E741`) e a intenção é removê-las aos poucos sem quebrar o CI;
  `tests/*` tem ignores próprios;
- `.pre-commit-config.yaml`: Ruff com `--fix`, remoção de espaços à direita,
  fim de arquivo, validação de YAML/TOML, conflito de merge e arquivos grandes;
- `.editorconfig`: UTF-8, LF, nova linha no fim, 4 espaços em Python e 2 em
  Markdown/JSON/TOML;
- `.gitignore`: ignora caches (`__pycache__`, `.pytest_cache`, `.ruff_cache`),
  `dist/`, `*.zip` e o ferramental local de agentes (`.agents/`,
  `.ag-kit-backups/`), que **não faz parte do plugin**.

Todo arquivo Python começa com o cabeçalho
`SPDX-License-Identifier: GPL-3.0-or-later` e a linha de copyright do projeto.

## Testes e validação

A suíte fica em `tests/` (50 arquivos). A partir da raiz do repositório:

```powershell
venv\Scripts\python.exe -m pytest trazomob/tests -q --no-header -p no:cacheprovider
```

Lint (a partir de `trazomob`):

```powershell
D:\projetos\ingetrazo\venv\Scripts\python.exe -m ruff check .
```

Os testes de UI criam o próprio `QApplication`; em CI usa-se
`QT_QPA_PLATFORM=offscreen`.

## Fases de reorganização

### Fase 1 — Limpeza de raiz (concluída)

- Move amostras `.igz` para `assets/samples/`.
- Move `perfis_biblioteca.json` para `assets/profiles/`.
- Move manuais para `docs/`.
- Corrige links e ignora `.pytest_cache/`.

### Fase 2 — Separação em subpacotes (concluída)

- Módulos Python agrupados em `domain/`, `builders/`, `wall/`, `interaction/`,
  `production/`, `render/`, `profiles/`, `ui/` e `integrations/`.
- Imports relativos atualizados dentro do plugin.
- Testes atualizados para os novos caminhos.
- Ressincronizados os caminhos absolutos de `assets/` e `blender_scripts/`.

### Fase 3 — Divisão dos monólitos (concluída)

Cada monólito foi dividido por responsabilidade em mixins de um nível, mantendo
a API pública:

- `ui/sidebar_panel.py` → `sidebar_*_controller.py`;
- `ui/module_dialog.py` → `module_dialog_*`;
- `wall/floorplan_canvas.py` → `mixin_navigation`, `mixin_history`,
  `mixin_input`, `mixin_drawing`, `mixin_measurement`, `mixin_dialogs` e
  `mixin_calibrate`;
- `builders/cabinet.py` → `cabinet_transform`, `cabinet_caixa`,
  `cabinet_module_group` e `cabinet_delegates`;
- `interaction/magnetic_drag.py` → `magnetic_drag_input`,
  `magnetic_drag_context` e `magnetic_drag_snap`.

### Fase 4 — Builders e controllers por família (concluída)

- Builders monolíticos divididos em módulos por família, com nomes em inglês:
  `base_wall_cabinets`, `wall_tall_cabinets`, `wardrobes`, `corner_cabinets`,
  `beds`, `countertops`, `fillers` e `fronts`.
- Controllers da sidebar divididos/renomeados para inglês:
  `sidebar_adjustments`, `sidebar_dimensions`, `sidebar_fronts`,
  `sidebar_handles` e `sidebar_materials`.
- Arquivos antigos mantidos como shims de reexportação para preservar imports.
- `bootstrap.py` e `context_menu.py` separados do `__init__.py`.

## Regras para novas contribuições

1. Não criar novos módulos Python na raiz, exceto `__init__.py` e os helpers de
   entrada `bootstrap.py` / `context_menu.py`.
2. Colocar o código na área de responsabilidade correspondente.
3. **Novos módulos, classes e funções devem usar nomes em inglês.** Nomes em
   português só são aceitos em shims de compatibilidade.
4. Shims devem ser mínimos: apenas reexportar a API antiga e declarar `__all__`.
   Não adicionar lógica neles.
5. Preservar a API pública exportada por `__init__.py`.
6. Manter `domain/` independente de `ui/`, `builders/`, `wall/` e `render/`.
7. Incluir o cabeçalho SPDX/copyright em todo arquivo Python novo.
8. Não adicionar dependências externas para Code 128/QR: usar `production/barcode.py`
   e `production/qr.py`.
9. Novos textos de UI devem usar `domain/i18n.tr()` e entrar em `assets/i18n/`.
10. Rodar pytest **e** ruff antes de concluir.
11. Usar `git mv` para mover arquivos, preservando o histórico.

## Decisões

- A organização usa subpacotes de um nível, e não subpacotes muito aninhados.
- `domain/` não se chama `core/` porque o IngeTrazo também usa o pacote `core/`.
- A Fase 3 divide os monólitos internamente, separada da mudança de caminhos.
- A partir da Fase 4, a nomenclatura de módulos novos é em inglês; os nomes em
  português ficam restritos a shims de compatibilidade.
- O catálogo pessoal do usuário vive nas preferências (`user_modules`), não em
  um segundo arquivo de catálogo.
- Code 128 e QR são implementados no plugin, sem dependências — as etiquetas
  precisam ser escaneáveis em qualquer instalação.
- A camada de ferragens separa descrição técnica (`domain/hardware.py`) de
  representação gráfica (`builders/hardware_geometry.py`); a cutlist e o
  orçamento usam apenas a descrição.
- `__init__.py` continua exportando a API do plugin e delega o restante aos
  subpacotes.
