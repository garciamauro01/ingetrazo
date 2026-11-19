# Especificação do Contrato de Interface Visual — TrazoMob

Este documento formaliza o contrato estrutural, funcional e de padrões das **5 abas** do painel lateral de propriedades de módulo (`TrazoMobSidebarPanel`). As invariantes aqui descritas são validadas automaticamente por [`domain/ui_contract.py`](file:///D:/projetos/ingetrazo/trazomob/domain/ui_contract.py) e [`tests/test_ui_contract.py`](file:///D:/projetos/ingetrazo/trazomob/tests/test_ui_contract.py) para impedir regressões.

---

## Visão Geral das 5 Abas

| Índice | Aba | Seção (`attr`) | Foco |
| :--- | :--- | :--- | :--- |
| `0` | 📏 **Medidas** | `sec_dimensoes` | Dimensões externas universais, troca de tipo e elevação do piso |
| `1` | 🚪 **Estrutura** | `sec_frentes` | Portas/Gavetas, lado de abertura, internos, rodapé, fundo e geometria das travessas |
| `2` | ✨ **Puxadores** | `sec_puxadores` | Tipo de puxador, perfil Gola e descontos visuais limpos |
| `3` | 🎨 **Materiais** | `sec_materiais` | MDF/fitas de Caixa, Frentes e Travessas, aplicação global |
| `4` | ⚙️ **Avançado** | `sec_ajustes` | Folga das frentes, corrediças, furação/dispositivos, nichos, tampo/pedra |

---

## Aba 1 — 📏 Medidas (`sec_dimensoes`)

- **5 campos universais sempre visíveis em módulos padrão**:
  1. `cb_trocar_tipo` — Tipo Módulo
  2. `sp_largura` — Largura (mm, com botões `-50` / `+50`)
  3. `sp_altura` — Altura (mm, com botões `-50` / `+50`)
  4. `sp_prof` — Profundidade (mm, com botões `-50` / `+50`)
  5. `sp_elevacao` — Elevação do Piso (mm, faixa `0..5000 mm`, botões `-50` / `+50`), lida da cota inferior da caixaria (`Z_min * 1000`) / `elevacao_mm` e aplicada à elevação Z do módulo (exceto esquadrias, que usam peitoril próprio).
- **Campos condicionais de canto**: `sp_larg_asa_esq`, `sp_larg_asa_dir`, `chk_batente_canto`, `sp_largura_cego_canto` (ocultos fora de módulos de canto).
- **Proibido nesta aba**: `sp_qtd_elem` e `cb_lado_porta_armario` (pertencem à aba **Estrutura**).

---

## Aba 2 — 🚪 Estrutura (`sec_frentes`)

- **Portas / Balcão Misto / Lado da Porta**:
  - `sp_qtd_elem` (`Portas / Gavetas:`) movido de *Medidas* para *Estrutura*.
  - `cb_lado_porta_armario` (`Lado Porta Única/Isolada:`) movido de *Medidas* para *Estrutura*.
  - **Regra de visibilidade de `cb_lado_porta_armario`** (`should_show_lado_porta_armario`):
    - Visível para `balcao_canto` (para inverter o lado cego);
    - Visível para módulos com porta de giro (`has_porta_arm=True`) **apenas quando `num_portas` for ímpar** (ex.: `1` ou `3`);
    - Oculto quando `num_portas` for par (`0`, `2`, `4`, ...) e atualizado reativamente em `sp_qtd_elem.valueChanged`.
  - `sp_largura_gaveteiro` e `cb_lado_gaveteiro` condicionais a `balcao_misto`.
- **Internos & Rodapé**:
  - `sp_prateleiras` (condicional a `has_prateleiras`), `sp_divisoes`, `sp_rodape` (condicional a `has_rodape`).
- **Fundo do Módulo**:
  - `cb_tipo_fundo`, `cb_esp_fundo`, `sp_recuo_fundo`, `sp_prof_rasgo`.
  - Padrões oficiais: **`prof_rasgo = 5 mm`** (alterado de 7 mm) e **`recuo_fundo = 10 mm`**.
- **Travessas Superiores (Geometria — exclusivas para `_IDS_COZINHA_INFERIORES`)**:
  - `lbl_travessa_section`, `sp_larg_travessa_frontal`, `sp_larg_travessa_traseira`, `chk_travessa_frontal_em_pe`, `chk_travessa_traseira_em_pe`, `sp_recuo_porta_topo`.
  - `sp_recuo_porta_topo` fica visível apenas quando `chk_travessa_frontal_em_pe` estiver marcado.
  - Quando `cb_tipo_fundo` estiver em Canal/Rasgo (`idx == 0`) e `chk_travessa_traseira_em_pe` estiver marcado, `sp_recuo_fundo` é sincronizado e travado na espessura da travessa traseira (ex.: `15 mm`); quando desmarcado, volta a ficar editável com o valor anterior (ex.: `10 mm`), e os builders só aplicam o recuo pela espessura da travessa quando `travessa_traseira_em_pe=True`.

---

## Aba 3 — ✨ Puxadores (`sec_puxadores`)

- Padronização visual limpa: remoção do cartão destacado (`#F8FAFC` com borda) e da caixa preta (`115x80`) em `self.frame_perfil`.
- `self.frame_perfil` utiliza layout transparente (`QFormLayout`) alinhado às demais abas, preservando todos os atributos (`frame_perfil`, `cb_perfil_modelo`, `btn_gerenciar_perfis`, `cb_altura_perfil`, `sp_desconto_perfil`, `lbl_perfil_diagram`).

---

## Aba 4 — 🎨 Materiais (`sec_materiais`)

- Mantém acabamento de **Caixa** e **Frentes** + ações em massa.
- Recebe os controles de acabamento de **Travessas** (condicionais a `_IDS_COZINHA_INFERIORES`):
  - `lbl_travessa_mat_section`, `cb_material_travessas`, `cb_espessura_travessas`, `cb_fita_travessas`, `cb_material_fita_travessas`, `btn_aplicar_travessas_todos`.

---

## Aba 5 — ⚙️ Avançado (`sec_ajustes`)

- Não contém widgets de travessas.
- Novo campo **`sp_folga_frentes`** (`lbl_folga_frentes`, faixa `0..15 mm`, padrão **`3 mm`**, mapeado para `params["folga_frentes_mm"]`), destravando a folga fixa anterior de 3 mm para permitir valores como `2 mm` com rebuild 3D real das portas e frentes de gaveta via `ModuloMaterialContext` e `FrentesKitBuilder`.
- Mantém corrediças, furação/dispositivos (`chk_gerar_furacao`, `cb_dispositivo_fixacao`, `cb_dispositivo_prateleira`), ajustes específicos de eletros, tampo, pedra, divisória e prateleiras avulsas.
