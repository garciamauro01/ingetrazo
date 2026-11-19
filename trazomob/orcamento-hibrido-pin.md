# Sistema Híbrido de Precificação e Orçamento TrazoMob

## Visão Geral
Implementação do sistema completo de orçamentos e precificação com arquitetura em duas camadas:
1. **Modo Apresentação (Visão Cliente)**: Exibição limpa de valores por ambiente, seletor de linhas de ferragens, simulação de pagamento e geração de proposta (zero exibição de custos/margens).
2. **Painel Administrativo de Custos (Retaguarda com Proteção por PIN)**: Tabela de preços de chapas inteiras ou m², fitas, serviços de corte/colagem, mão de obra, montagem, formação de preço (multiplicador ou composição) e alerta automático de itens sem preço.

---

## Fases de Execução

- [x] **Fase 1: Modelo de Dados e Preferências** (`domain/preferences.py`)
  - [x] Hash e validação de PIN de 4 dígitos.
  - [x] Estrutura de configuração para modo de chapa (`inteira` vs `m2_perda`), modo de fechamento (`multiplicador` vs `detalhado`), linhas de ferragens, serviços de central de corte e montagem.
  - [x] Métodos auxiliares de leitura/gravação persistente no JSON de preferências.

- [x] **Fase 2: Motor de Cálculo Aprimorado** (`production/pricing.py`)
  - [x] Suporte a cálculo por chapa inteira (integração ou estimativa compatível com otimizador) ou m² + fator de perda.
  - [x] Suporte a linhas de ferragens (Econômica, Standard/Amortecedor, Premium).
  - [x] Adição de serviços terceirizados (corte por chapa, colagem de fita/metro) e montagem.
  - [x] Detecção e lista de itens com preço zerado (`itens_sem_preco`).
  - [x] Cálculo de condições de pagamento (à vista com desconto e parcelamento).

- [x] **Fase 3: Interface Gráfica — Apresentação e Painel Administrativo** (`ui/pricing_dialog.py`)
  - [x] Janela principal em Modo Apresentação (Visão Cliente):
    - [x] Cards de valores de venda por ambiente.
    - [x] Seletor rápido de padrão de ferragens com recálculo instantâneo.
    - [x] Simulador de pagamento (à vista / parcelas).
    - [x] Alerta discreto quando houver itens sem preço cadastrado.
    - [x] Botão de Proposta Comercial (HTML/PDF).
    - [x] Botão de desbloqueio com cadeado (`🔐 Custos & Tabela de Preços`).
  - [x] Diálogo de Validação / Definição de PIN de 4 dígitos.
  - [x] Janela Administrativa de Custos (com Abas):
    - [x] Aba Chapas & Fitas (preço chapa cheia vs m², destaque de itens zerados).
    - [x] Aba Ferragens & Linhas (preços por linha de ferragens).
    - [x] Aba Serviços & Montagem (corte/chapa, fita/m, taxa de montagem).
    - [x] Aba Formação de Preço (seletor Multiplicador vs Detalhado).
    - [x] Aba Empresa & Segurança (dados cadastrais, logo, alterar/remover PIN).

- [x] **Fase 4: Integração na UI e Testes Automatizados**
  - [x] Conectar botão na barra da Lista de Corte (`production/cutlist_tab.py`).
  - [x] Suíte de testes automatizados (`tests/test_pricing_system.py`).
  - [x] Validação completa de testes regressivos.

