# MANUAL DE OPERAÇÃO COMPLETO — TRAZOMOB
*Guia Operacional Técnico e Prático para Marcenaria, Modulação Paramétrica, Arquitetura de Interiores, Orçamentação e Produção 3D no IngeTrazo.*

---

## 📑 ÍNDICE GERAL
1. [Visão Geral do TrazoMob e Filosofia Operacional](#1-visão-geral-do-trazomob)
2. [Interface, Barras de Ferramentas e Painéis de Controle](#2-interface-e-barras-de-ferramentas)
3. [Estrutura do Projeto: Pavimentos, Ambientes e Hierarquia](#3-pavimentos-ambientes-e-hierarquia)
4. [Arquitetura de Alvenaria: Paredes 2D, Sólidos 3D, Pisos e Tetos](#4-arquitetura-de-alvenaria-paredes-pisos-e-tetos)
5. [Pintura e Revestimento de Paredes (Wall Paint)](#5-pintura-e-revestimento-de-paredes)
6. [Elevação Técnica 2D com Cotas Arquitetônicas](#6-elevação-técnica-2d-com-cotas)
7. [Esquadrias Paramétricas (Portas e Janelas com Recorte Automático)](#7-esquadrias-paramétricas)
8. [Réguas de Altura e Linhas-Guia Magnéticas](#8-réguas-de-altura-e-linhas-guia)
9. [Catálogo e Inserção de Módulos de Marcenaria](#9-catálogo-e-inserção-de-módulos)
10. [Edição Paramétrica Detalhada na Barra Lateral](#10-edição-paramétrica-na-barra-lateral)
11. [Biblioteca e Editor de Perfis de Alumínio / Puxadores](#11-perfis-e-puxadores-de-alumínio)
12. [Snapping Magnético, Cotas Projetadas e Posicionamento Inteligente](#12-snapping-magnético-e-posicionamento)
13. [Alinhamento, Centralização, Distribuição no Vão e Grupos (Assemblies)](#13-alinhamento-distribuição-e-grupos)
14. [Cinemática 3D: Abertura Dinâmica e Detecção de Colisões](#14-cinemática-3d-e-colisões)
15. [Luminotécnica Interativa e Spots Físicos (Fotometria IES)](#15-luminotécnica-e-spots-físicos)
16. [Editor de Materiais PBR e Render Foto-Realista (Blender Cycles / EEVEE)](#16-materiais-pbr-e-render-foto-realista)
17. [Lista de Peças (Cutlist), Fitamento, Junções e Furações](#17-cutlist-fitamento-e-furações)
18. [Otimizador de Corte de Chapas 2D (Nesting) e Sobras](#18-otimizador-de-corte-2d-nesting)
19. [Etiquetas Técnicas (Code 128 + QR Code) e Manual de Montagem](#19-etiquetas-técnicas-de-produção)
20. [Orçamentação Híbrida (PIN), Custos e Propostas Comerciais](#20-precificação-e-propostas-comerciais)
21. [Exportação (CSV, JSON, DXF CNC), Integrações e Tabela de Atalhos](#21-exportação-e-tabela-de-atalhos)
22. [Biblioteca de Componentes do Usuário (Eletrodomésticos e Modelos Próprios)](#22-biblioteca-de-componentes-do-usuário)

---

## 1. Visão Geral do TrazoMob

O **TrazoMob** é o ecossistema integrado para marcenaria sob medida, interiores e plano de corte do **IngeTrazo CAD 3D**. Ele une a facilidade do desenho paramétrico intuitivo à precisão milimétrica da indústria moveleira e fabril.

### Princípios Chave de Operação:
- **Geometria Paramétrica Real:** As alterações de medidas recalculam e reconstroem as chapas com espessuras constantes (15mm, 18mm, 25mm, etc.), sem deformar topos ou criar distorções de escala.
- **Sólidos Manifold Estanques (*Watertight*):** Paredes, pisos e peças são gerados como sólidos fechados, prontos para furações booleanas e renderização sem vazamento de luz.
- **Snapping Magnético, Alinhamento Notável e Cotas Dinâmicas:** Ao movimentar módulos próximos a paredes ou outros armários, o sistema alinha a face traseira, ajusta a rotação para 90° e exibe as folgas residuais em milímetros em tempo real (ocultando cotas redundantes nos lados já encostados). Além disso, a ferramenta **Alinhar & Apoiar (`Shift+A`)** permite alinhar ou apoiar objetos com precisão por quinas, centros, pontos médios e faces.
- **Produção e Orçamento Diretos:** Cada chapa mantém identificação de material, fita de borda nos 4 topos, veio da madeira, dispositivo de fixação, usinagens de dobradiças/minifix/VB 35/VB 36 e custo financeiro.
- **Suporte Multi-Documento (Abas Independentes):** Cada documento aberto no IngeTrazo preserva seu próprio contexto de seleção de parede, editor lateral, luzes e diálogo do TrazoMob, sincronizando automaticamente ao trocar de aba.

---

## 2. Interface e Barras de Ferramentas

Ao iniciar o IngeTrazo com o plugin TrazoMob ativo, você dispõe dos seguintes canais operacionais:

### 2.1 Barra de Ferramentas Superior (Toolbar TrazoMob)
Localizada no topo da área de trabalho:
- **TrazoMob (Ícone Principal):** Abre a janela central unificada com o catálogo de módulos e a tabela da Cutlist.
- **Editor Lateral:** Dá foco imediato ao painel acoplável direito de edição dinâmica.
- **Construir Paredes (Atalho: W):** Inicia a ferramenta interativa de desenho de alvenaria em planta baixa 2D.
- **Réguas de Altura:** Abre o editor e gerenciador de réguas padrão de montagem.
- **Módulos (Ribbon):** Alterna a barra de abas superiores com botões visuais diretos organizados por ambiente (Cozinha Baixos, Aéreos, Torres, Quartos, Banheiros, **⭐ Meus Módulos**, etc.).
- **Girar 90° (↺ / ↻):** Gira instantaneamente o móvel selecionado em passos ortogonais de 90° no eixo Z.
- **Interagir (Atalho: I):** Ativa a mãozinha de clique interativo para abrir e fechar portas e gavetas na viewport 3D.
- **Alinhar & Apoiar (Atalho: Shift+A):** Ferramenta interativa 3D em 2 cliques para alinhar centros, quinas ou apoiar objetos sobre superfícies, com trava de eixos (`X`, `Y`, `Z`, `A`) e alternância entre *Alinhar Posição* e *Alinhar e Mover* via `TAB`.
- **Lista de Peças:** Acesso direto à tabela de cutlist, fitamento, manual de montagem, orçamento e propostas.
- **Plano de Corte 2D:** Abre o visualizador gráfico do diagrama de corte de chapas otimizado (*nesting*) e exportação DXF CNC.
- **Estilos de Visualização (Paleta):** Menu rápido para alternar estilos de visualização de faces (Realista, Sombreado, Branco, Linhas Ocultas), exibir/ocultar arestas de contorno e modo Raio-X (**Alt+X**).
- **Snap Magnético (Atalho: Alt+S):** Ativa/desativa em tempo real a atração magnética a paredes, módulos e réguas de altura (modo livre para ajuste fino).
- **Materiais & Shaders PBR:** Abre o Editor de Materiais PBR com categorias físicas e captura direta via **Conta-gotas 3D**.
- **Iluminação e Spots Físicos:** Abre o gerenciador não-modal de spots, fitas LED, lâmpadas e pontos de luz.
- **Render Foto-Realista:** Abre o diálogo de exportação e renderização PBR integrada via Blender Cycles / EEVEE Next.

### 2.2 Painel de Encaixe Direito (Dock Lateral TrazoMob)
O painel lateral adapta-se de forma inteligente ao contexto do documento ativo:
1. **Modo Sem Seleção / Projeto Geral:** Apresenta ações rápidas para desenhar paredes, criar novos pavimentos e gerenciar a hierarquia do projeto (Pavimento Térreo, Superior, Ambientes Cozinha, Suíte, etc.).
2. **Modo Múltiplos Módulos Selecionados:** Apresenta botões para centralização (XY, X, Y, Z), distribuição equidistante de módulos em vãos e agrupamento em conjunto (*Assembly*).
3. **Modo Parede Selecionada:** Exibe seleção de segmentos, comprimento milimétrico, altura, espessura da alvenaria, alinhamento de face, régua/linhas-guia, pintura/texturização, vista de elevação 2D, preenchimento automático e comandos para ocultar/reexibir paredes.
4. **Modo Módulo Selecionado:** Ativa o formulário horizontal em **5 abas exclusivas** (visíveis apenas quando aplicável ao tipo de módulo selecionado):
   - **📏 Medidas:** Largura, altura, profundidade, rodapé, elevação Z, asas/cegos e folgas dimensionais; inclui também um botão de **💾 Salvar em Meus Módulos**.
   - **🚪 Estrutura:** Tipo/modo do fundo (ranhurado/sobreposto), **Esp. Fundo**, **Recuo Fundo**, **Rasgo**, portas, gavetas, prateleiras internas, divisórias e travessas superiores (frontal/traseira e orientação em pé/deitada).
   - **✨ Puxadores:** Modelo (Gola, Cava, Perfil Alumínio, Fecho-Toque, etc.), desconto de perfil, posicionamento e acabamento.
   - **🎨 Materiais:** Padrão e espessura de fita da caixa, frentes, tampos, fundo e travessas, além de botões globais para aplicar padrões em todo o projeto.
   - **⚙️ Avançado:** Dispositivos de fixação de caixa e prateleira (incluindo **VB 35** e **VB 36**), geração de furações/usinagens, **Folga das Frentes**, parâmetros de ferragens de gaveta, nichos/eletros e blocos de bancada.
5. **Modo Luz / Spot Selecionado:** Exibe potência, ângulo/facho, temperatura Kelvin, altura Z e mira 3D.

---

## 3. Pavimentos, Ambientes e Hierarquia

O TrazoMob possui um sistema hierárquico estruturado para gerenciar residências completas e edifícios de múltiplos pavimentos:

### 3.1 Níveis de Organização
- **Pavimento (Story / Level):** Define a cota vertical base (Z) e o pé-direito padrão (ex.: *Pavimento Térreo*, *1º Andar*).
- **Ambiente (Room):** Subdivisão arquitetônica do pavimento (ex.: *Cozinha*, *Suíte Master*, *Lavanderia*). Cada parede, módulo e bancada pertence a um ambiente específico.

### 3.2 Como Operar Pavimentos e Ambientes
1. No painel lateral, localize o cartão **Pavimentos & Ambientes**.
2. Clique em **➕ Pavimento** para adicionar um novo piso (ex.: "Piso Superior", Altura base = 2.80 m).
3. Clique em **➕ Ambiente** para criar um cômodo dentro do pavimento ativo.
4. Ao desenhar paredes ou inserir móveis, selecione o ambiente no menu dropdown: todas as peças inseridas herdam a classificação para orçamentos e relatórios seletivos por cômodo.
5. Use o botão **👁️ Visibilidade** ao lado do nome do ambiente para ocultar ou exibir todas as paredes e móveis daquele cômodo simultaneamente, facilitando o trabalho em projetos extensos.

---

## 4. Arquitetura de Alvenaria: Paredes, Pisos e Tetos

O TrazoMob inclui um motor dedicado para geração de alvenaria paramétrica 2D/3D com junções em esquadria (*miter joints*) automáticas.

### 4.1 Desenhando Paredes com a Planta Baixa 2D
1. Clique no botão **Construir Paredes** (ou pressione a tecla de atalho **W**).
2. A janela interativa da **Planta Baixa 2D** será exibida com grade milimétrica, controle de snap a ângulos ortogonais (0°, 90°, 180°, 270°) e guia de medidas.
3. Defina a **Espessura da Parede** (padrão: 15 cm) e a **Altura / Pé-Direito** (padrão: 2.60 m ou 2.80 m).
4. Clique no canvas com o botão esquerdo do mouse para marcar o ponto inicial e mova o cursor:
   - Digite o comprimento exato em milímetros ou centímetros no teclado numérico e pressione **Enter** para travar a distância.
   - Pressione **Shift** para forçar travamento estritamente ortogonal.
5. Continue clicando para formar as paredes consecutivas do ambiente.
6. Ao clicar sobre o primeiro vértice ou pressionar **C**, o contorno é fechado automaticamente.
7. Marque as opções:
   - **Gerar Laje de Piso:** Cria um piso 3D no contorno interno do cômodo.
   - **Gerar Teto / Forro:** Cria uma laje superior ou forro de gesso no teto.
8. Clique em **Concluir / Gerar 3D**: o modelo de alvenaria sólida hermética é inserido na viewport 3D instantaneamente.

### 4.2 Edição e Ocultação Seletiva de Paredes
- **Ocultar Paredes para Visão Interna:** Em perspectivas ou renders de cômodos fechados, clique com o botão direito sobre a parede que está na frente da câmera e selecione **👁️ Ocultar Parede**.
- **Seccionar em Paredes Individuais:** Se você desenhou o cômodo como um polígono contínuo e precisa alterar a cor ou remover apenas um segmento de parede, clique com o botão direito e escolha **✂️ Seccionar em Paredes Individuais**.
- **Reexibir Paredes:** No menu de contexto (botão direito no vazio da cena), selecione **👁️ Reexibir Todas as Paredes e Tetos**.
- **Trava de Segurança (Lock):** No painel lateral, alterne o botão **🔒 Trava: ATIVA** / **🔓 Trava: LIVRE** para impedir ou liberar o deslocamento das paredes e do piso ao movimentar os móveis.

---

## 5. Pintura e Revestimento de Paredes

A ferramenta **Wall Paint** permite aplicar cores e revestimentos de forma independente nas faces internas ou externas de cada parede.

### Como Operar:
1. No painel lateral (com uma parede selecionada) ou no menu de contexto, clique em **🎨 Pintar Parede / Revestimento**.
2. A paleta de cores e acabamentos será exibida com coleções pré-configuradas:
   - Cores neutras de alvenaria (Branco Neve, Cinza Urbano, Off-White, Grafite).
   - Revestimentos cerâmicos, porcelanatos e azulejos de cozinha/banheiro.
   - Painéis ripados e texturas decorativas.
3. Escolha se deseja aplicar a pintura na **Face Interna**, **Face Externa** ou na **Parede Inteira**.
4. Clique na cor desejada: a viewport 3D e o motor de materiais para o renderizador Cycles são atualizados imediatamente.

---

## 6. Elevação Técnica 2D com Cotas

Para conferência de projeto executivo, detalhamento de montagem e impressão para a equipe de marcenaria ou cliente, o TrazoMob oferece a ferramenta de **Elevação Técnica 2D**.

### Como Operar:
1. Selecione a parede de fundo desejada na viewport 3D.
2. Na barra lateral, na seção de paredes, clique em **📐 Elevação 2D**.
3. A janela de desenho ortogonal técnico abre exibindo:
   - A silhueta precisa da alvenaria e dos móveis fixados nela (balcões, rodapés, aéreos, torres).
   - Linhas horizontais e verticais com réguas milimétricas.
   - **Cotas Automáticas de Vãos:** Largura de cada módulo e espaço livre residual restante na parede.
   - **Cotas Verticais de Níveis:** Altura do rodapé, altura da caixa do balcão, espessura da pedra da bancada, vão livre entre bancada e aéreo, e fechamento até o teto.
4. **Controles:**
   - Role a roda do mouse para **Zoom** e arraste com o botão direito ou do meio para **Pan**.
   - Clique em **Salvar Imagem (PNG)** para exportar a elevação em alta definição.
   - Clique em **Imprimir / PDF** para enviar diretamente para a prancha do projeto executivo.

---

## 7. Esquadrias Paramétricas (Portas e Janelas)

As esquadrias no TrazoMob possuem recorte automático de alvenaria (*Boolean Hole Cutting*) totalmente dinâmico e reversível.

### 7.1 Modelos Disponíveis no Catálogo
- **Porta de Giro com Batente:** Folha de madeira com maçaneta e guarnição.
- **Porta de Alumínio e Vidro:** Perfil metálico contemporâneo para varandas e lavanderias.
- **Porta Pivotante de Vidro:** Ideal para halls e entradas sociais.
- **Porta Balcão de Correr (Vidro 170x215 cm):** Folhas de correr para sacadas e áreas gourmet.
- **Janelas de Correr (2 Folhas 130x120 cm / 4 Folhas 190x120 cm):** Para salas e cozinhas.
- **Janelas Maxim-Ar e Basculantes:** Para lavabos, banheiros e lavanderias.

### 7.2 Inserção e Funcionamento do Recorte
1. Na aba **Portas & Janelas** do catálogo ou da ribbon bar, clique na esquadria desejada.
2. Posicione o mouse sobre a parede hospedeira no 3D: a esquadria alinha-se automaticamente à rotação da alvenaria.
3. Ao soltar com o clique, o TrazoMob **fura a parede na hora**, gerando as faces internas da boneca e do vão sem quebras de malha.
4. **Reposicionamento:** Ao mover a esquadria com a ferramenta Mover (**M**), o furo na parede acompanha a posição em tempo real.
5. **Ajuste de Peitoril e Medidas:** Com a janela selecionada, altere a largura, altura ou a altura do **Peitoril (mm)** na barra lateral: a abertura na alvenaria se reajusta instantaneamente.
6. **Desfazer (Ctrl+Z):** Totalmente integrado ao histórico — desfazer a colocação ou movimentação restaura a parede sólida original sem resíduos.

---

## 8. Réguas de Altura e Linhas-Guia Magnéticas

Para manter o alinhamento arquitetônico impecável entre módulos distintos (ex.: alinhar o topo de uma torre quente ao topo de um armário aéreo), o TrazoMob utiliza **Réguas de Altura Inteligentes**.

### 8.1 Presets Padrão do Sistema
- **Nível Rodapé:** 100 mm a 150 mm do piso acabado.
- **Nível Balcão (Corpo):** 820 mm a 850 mm.
- **Nível Bancada Acabada (Tampo de Pedra):** 900 mm.
- **Nível Inferior do Aéreo (Vão Backsplash):** 1.500 mm (geralmente 600 mm acima da bancada).
- **Nível Superior do Aéreo / Torre:** 2.100 mm a 2.300 mm.
- **Nível Fechamento / Teto:** Conforme o pé-direito do ambiente (ex.: 2.600 mm).

### 8.2 Personalização de Réguas
1. Clique no botão **Réguas de Altura** na barra superior.
2. No diálogo de configuração:
   - Adicione, edite ou remova níveis milimétricos.
   - Crie novos presets (ex.: *Linha Cozinha Baixa 85cm*, *Linha Gourmet Alta 92cm*).
3. Ao arrastar um módulo no eixo Z próximo a um desses níveis, o objeto atrai magneticamente para a linha-guia correspondente.

---

## 9. Catálogo e Inserção de Módulos

O TrazoMob possui uma biblioteca completa de módulos paramétricos organizados por tipologias:

### 9.1 Tipos de Módulos Disponíveis
- **Cozinha — Inferiores:**
  - *Balcão com Portas:* portas de giro em regra de 400 mm; largura e divisórias ajustadas automaticamente a partir da 3ª porta.
  - *Balcão Gaveteiro:* 2, 3 ou 4 gavetas com laterais rebaixadas e desconto técnico real de 26 mm para corrediças telescópicas ou invisíveis.
  - *Balcão Misto:* Gaveteiro acoplado + vão com portas.
  - *Balcão de Canto Reto (Cego / L Cego):* Montante frontal cego para junções perpendiculares.
  - *Balcão Canto L (90°):* Duas portas articuladas em ângulo, sobrepostas às laterais; opcionalmente, **batente de quina interna** com a espessura das frentes. Medida padrão: 1000 × 1000 mm.
  - *Porta-Tempero / Toalheiro:* Módulo estreito deslizante de 150 mm a 250 mm.
  - *Balcão Forno Embutido:* Vão ventilado para forno e gavetão inferior.
- **Cozinha — Aéreos:**
  - *Aéreo com Portas:* Portas de giro tradicionais.
  - *Aéreo Portas de Correr (`aereo_correr`):* Armário aéreo suspenso para portas de correr de 2 a 4 vãos com divisórias estruturais internas e trilhos duplos.
  - *Aéreo Basculante Simples:* Porta única com pistão a gás.
  - *Aéreo Basculante Duplo:* 2 portas sobrepostas basculantes.
  - *Aéreo Nicho Micro-ondas:* Vão frontal aberto com prateleira de apoio e opções configuráveis de portas no maleiro.
- **Cozinha — Torres de Eletrodomésticos:**
  - *Torre Quente:* Nichos para forno elétrico, micro-ondas e despensas superior e inferior.
  - *Caixa para Geladeira:* Nicho aéreo com fechamento lateral para embutir geladeiras side-by-side.
- **Dormitórios, Camas & Armários (Roupeiros):**
  - *Roupeiro Portas de Correr (2 e 3 Vãos):* Trilho superior e inferior embutidos com rodízios.
  - *Armário Maleiro com Tamponamento e Rodapé (`armario_maleiro_tamponado`):* Armário com base de rodapé fechado estruturado, caixarias superiores com divisórias de maleiro (2 a 4 caixas isoladas ou única), tamponamento lateral (padrão 18 mm) e recuo configurável de 70 mm para portas de correr.
  - *Armários Cabideiros e Prateleiros:* Opções de 1, 2 e 3 portas de giro com divisórias internas.
  - *Camas e Estruturas de Dormitório:* **Cama Box com Baú Articulado** (`cama_bau`), Cama com Gaveteiros (`cama_gaveteiros`), Cabeceira (`cama_cabeceira`), **Bicama Solteiro com Auxiliar Deslizante** (`bicama`) e **Beliche Planejado com Escada** (`beliche`) com guarda-corpo superior.
- **Banheiro:**
  - *Gabinete Suspenso:* Sem rodapé, gavetão com recorte para sifão e toalheiro.
- **Marmoraria, Bancadas e Tampos:**
  - *Bancada Reta de Pedra:* Com saia frontal e frontispício (rodabanca).
  - *Bancada de Pia com Cuba:* Cuba de inox ou louça esculpida embutida no granito.
  - *Bancada Canto em L:* Bancada inteiriça para cantos de cozinha.
  - *Ilha / Bancada Gourmet:* Balcão em balanço com apoio para banquetas.
- **Peças Avulsas, Estruturais e Componentes:**
  - Laterais e bases/tampos avulsos (incluindo *Tampo Engrossado*), réguas de travamento, tamponamento vertical, **Tamponamento Contínuo de Linha (Envoltório)** (`peca_tamponamento_linha`), **Rodapé Fechado (Base)** (`rodape_fechado`) e kit avulso de **Portas de Correr** (`peca_portas_correr`).

### 9.2 Como Inserir na Cena
1. Abra a janela principal do TrazoMob ou ative a **Ribbon Bar de Módulos**.
2. Navegue até a categoria desejada e dê um duplo clique no card do módulo (ou clique em **Inserir no Projeto**).
3. O móvel surgirá na viewport 3D na coordenada da câmera ou na parede ativa.

### 9.3 Preenchimento Automático de Parede
Cria uma fileira de módulos contíguos que fecha exatamente um vão da parede selecionada.

1. Selecione uma **face de parede** no 3D.
2. Na seção **🧱 Construtor de Paredes**, ajuste o campo **Comprimento**.
   - Ele já vem preenchido com o comprimento do segmento selecionado.
   - Se você informar um vão menor, o preenchimento fica centralizado na face.
3. Em **Preenchimento Automático**, para os inferiores escolha a composição:
   - **Balcões com portas**
   - **Balcões + gaveteiros**
   - **Somente gaveteiros**
4. Clique em **⬇️ Inferiores** ou **⬆️ Aéreos**.
5. Os módulos são gerados encostados na parede, contíguos e com a sobra distribuída entre eles, sem ultrapassar os limites técnicos.
6. Todo o preenchimento entra como **um único passo de Desfazer (Ctrl+Z)**.

Observações:
- Inferiores usam balcões de até 4 portas, com divisórias automáticas a partir da 3ª porta.
- Aéreos usam sempre armários com portas (até 2 portas por módulo).
- A composição mista e gaveteiros valem apenas para os inferiores.
- O comando não remove nem desloca móveis já existentes na parede; se ela já estiver ocupada, os novos módulos podem sobrepor os anteriores. Desfaça com **Ctrl+Z** se necessário.

### 9.4 ⭐ Meus Módulos (Presets Personalizados)
Permite salvar móveis já parametrizados para reutilização rápida em projetos futuros:
1. Selecione um módulo no 3D e configure medidas, estrutura, materiais, puxadores e folgas na barra lateral.
2. Na aba **📏 Medidas** (ou barra de ações da lateral), clique em **💾 Salvar em Meus Módulos**.
3. O módulo passa a ficar disponível na categoria/aba **⭐ Meus Módulos**, mantendo suas medidas, acabamentos e ferragens prontas para reinserção.

---

## 10. Edição Paramétrica na Barra Lateral

Ao clicar em qualquer armário da cena, a barra lateral direita ativa um **QTabWidget horizontal com 5 abas** (`📏 Medidas`, `🚪 Estrutura`, `✨ Puxadores`, `🎨 Materiais`, `⚙️ Avançado`), respeitando o contrato de separação de controles:

```
┌────────────────────────────────────────────────────┐
│  🪵 TrazoMob — Balcão com Portas                   │
├────────────────────────────────────────────────────┤
│ [📏 Medidas] [🚪 Estrutura] [✨ Puxadores]          │
│ [🎨 Materiais] [⚙️ Avançado]                        │
├────────────────────────────────────────────────────┤
│ Largura (mm):      [  800  ] [ -50 ] [ +50 ]       │
│ Altura (mm):       [  720  ] [ -50 ] [ +50 ]       │
│ Profundidade (mm): [  550  ] [ -50 ] [ +50 ]       │
│ Elevação (Z):      [    0  ]                       │
└────────────────────────────────────────────────────┘
```

### 10.1 Aba 1: 📏 Medidas
- **Largura, Altura e Profundidade (mm):** Controle milimétrico com botões de incremento rápido.
- **Elevação Z (mm):** Altura da base do móvel em relação ao piso (padrão `0 mm` para inferiores).
- **Dimensões Específicas:** Largura de vão cego/canto, asas esquerda/direita em L e espaçamento/recuos de réguas de canto quando aplicáveis ao módulo.

### 10.2 Aba 2: 🚪 Estrutura
- **Tipo, Espessura e Usinagem de Fundo:** Escolha entre fundo ranurado/encaixado ou sobreposto, com **Esp. Fundo** (`6 mm`, `3 mm`, `15 mm`), **Recuo Fundo** (padrão `10 mm`) e profundidade do **Rasgo** (padrão `5 mm`).
- **Controle de Portas & Gavetas:** Quantidade de portas/gavetas, sentido de abertura da porta única e divisórias internas.
- **Prateleiras Internas e Rodapé:** Número de prateleiras internas, altura de rodapé estrutural (ou suspensão).
- **Travessas Superiores (Cozinha Inferiores):** **Frontal (larg.)**, **Traseira (larg.)**, checkboxes de orientação vertical (**Frontal em pé** / **Traseira em pé**) e **Rebaixo Portas** (padrão `50 mm` quando a travessa frontal está em pé).

### 10.3 Aba 3: ✨ Puxadores
- Escolha entre puxadores convencionais ou sistemas sem puxador aparente (Perfil Gola de alumínio, Cava usinada a 45°, Puxador de Alça Metálica, Concha ou Sistema Fecho-Toque / Tip-on), além de **Desconto de Perfil**, acabamento e posição.

### 10.4 Aba 4: 🎨 Materiais
- **Caixa e Espessura da Caixa:** Padrão de MDF e espessura (`15 mm`, `18 mm`, `20 mm`, `25 mm`, `40 mm`), além de fitamento da caixa (**Fita Caixa** e **Padrão Fita Cx**).
- **Frentes e Espessura das Frentes:** Acabamento e espessura exclusivos para portas e frentes de gavetas.
- **Acabamento das Travessas e Fundo:** **Padrão Trav.** e **Esp. Trav.**, bem como padrão do fundo.
- **Aplicação Global:** Botões **🎨 Aplicar Padrão de Frentes em Todo o Projeto** e **🪵 Aplicar Padrão de Caixaria em Todo o Projeto**.

### 10.5 Aba 5: ⚙️ Avançado
- **Furações e Dispositivos de Fixação:** Checkbox **Gerar furações e usinagens**, seletor **Fixação Caixa** (*Minifix + Cavilha*, *Cavilha + Parafuso*, *Apenas Parafuso*, *Apenas Cavilhas*) e **Fixação Prateleira** (*Cavilhas de Topo Ø8mm*, **Conector Häfele VB 35 (Ø20mm)** e **Conector Häfele VB 36 com Aba (Ø20mm)**).
- **Folga das Frentes (`sp_folga_frentes`):** Folga perimetral e entre portas/gavetas configurável de `0 mm` a `15 mm` (padrão: `3 mm`).
- **Parâmetros Específicos:** Caixa de gaveta (montagem do fundo e **Folga Corrediças** padrão `26 mm`), **Nicho de Geladeira & Maleiro**, **Portas do Micro-ondas**, **Marmoraria & Bancada** (pedra, saias, rodabanca, cuba e área molhada) e **Tampo Engrossado** (camadas e fechamento inferior).

---

## 11. Perfis e Puxadores de Alumínio

O TrazoMob possui um **Motor de Extrusão Paramétrica de Perfis de Alumínio** (definido em `perfis.py` e `perfis_editor.py`), permitindo detalhamento milimétrico de perfis Gola, perfis puxadores lineares e cavas.

### Como Operar a Biblioteca de Perfis:
1. Na barra lateral (Aba *Puxadores & Perfis*), clique em **📂 Biblioteca de Perfis...**.
2. O diálogo abre a biblioteca gráfica vetorial dos perfis:
   - **Perfil Gola Superior (L):** Para balcões logo abaixo do tampo.
   - **Perfil Gola Central (C / Duplo):** Entre gavetas para abertura dupla.
   - **Perfil Cava J:** Puxador de alumínio fixado no topo da chapa de 18mm.
   - **Perfil Alça / Concha Embutida:** Usinagens rentes à face.
3. Cada perfil exibe o desenho técnico de corte transversal (seção paramétrica milimétrica), espessura de encaixe e peso por metro linear.
4. Clique em **Aplicar ao Módulo Selecionado** para reconstruir o armário com os descontos exatos nas travessas e laterais para alojar o alumínio.

---

## 12. Snapping Magnético e Posicionamento

A movimentação de módulos no TrazoMob utiliza um algoritmo de colisão e atração vetorial em tempo real (`interaction/magnetic_drag.py`, `magnetic_drag_input.py` e `magnetic_drag_snap.py`).

### 12.1 Aderência a Paredes (Wall Snapping) e Quadro 3D
- **Frame 3D de Próxima Inserção:** Ao clicar diretamente em uma face de parede, as linhas-guia e o contorno de seleção âmbar indicam a face ativa e um quadro 3D ciano marca a próxima posição de encaixe; ambos respeitam a oclusão por sólidos em primeiro plano e o quadro 3D desaparece automaticamente ao clicar em qualquer móvel ou outro objeto.
- Ao arrastar um balcão ou aéreo em direção a uma parede, o módulo **gira automaticamente** para alinhar suas costas com a superfície da parede.
- O móvel desliza paralelo à parede sem atravessar a alvenaria, podendo ser solto livremente com o botão **Snap Magnético (`Alt+S`)** desativado quando precisar de ajuste fino livre.

### 12.2 Encaixe Módulo a Módulo (Edge Snapping)
- Aproxime um balcão da lateral de outro balcão já posicionado: ao se aproximar da borda ou das réguas de altura, o sistema gera uma **atração magnética**, encostando perfeitamente as laterais e alinhando alturas de base/topo.
- **Snap também no clique da parede:** ao clicar na parede a até 12 cm da borda de um móvel já inserido (mesma parede e mesma faixa vertical), o quadro 3D de próxima inserção é ancorado automaticamente à lateral do móvel — o próximo módulo já entra encostado. A ancoragem é mantida ao trocar a largura no catálogo. Clicar diretamente sobre o móvel continua limpando o quadro e abrindo sua edição.

### 12.3 Cotas Dinâmicas Projetadas
- Durante a seleção ou arraste, linhas pontilhadas de cota aparecem na viewport 3D exibindo em tempo real as folgas livres em milímetros até a parede mais próxima ou até o móvel vizinho (além da elevação Z quando suspenso).
- **Supressão Inteligente quando Encostado:** Quando a lateral ou o fundo do módulo já estão fisicamente encostados em uma parede, outro armário ou superfície, a cota daquele lado é automaticamente suprimida para evitar poluição visual e leituras redundantes.

### 12.4 Rotação Rápida
- Pressione os botões **↺ Girar 90° Anti-horário** ou **↻ Girar 90° Horário** na barra de ferramentas para rotacionar o armário ortogonalmente em torno do seu centro de massa sem perder o alinhamento.

### 12.5 Diagnóstico de performance do botão Aplicar
- O catálogo de texturas (`assets/textures/*/catalog.json`) é lido uma vez por versão do arquivo (caminho + data/hora + tamanho), não uma vez por peça. Editar o catálogo invalida o cache automaticamente.
- A varredura de recortes de parede (`WallMeshBuilder.sync_scene_wall_openings`) roda no máximo uma vez por mudança relevante da cena: sidebar e bootstrap disparam o mesmo sinal, mas o segundo disparo é ignorado pela assinatura da cena.
- **Invalidação seletiva de render:** ao reconstruir um módulo (por exemplo, ao trocar a textura da marmoraria), só os chunks daquele módulo — grupo, peças filhas e proxies — são descartados. Os caches `_group_chunks`/`_inst_chunks` do resto da cena são preservados e revalidados em O(1) pelo viewport, sem rebake de VBOs de paredes ou importações grandes. Vale para o **Aplicar** individual e para o **Aplicar a todos da mesma classe**.
- Para medir o custo do Aplicar, inicie o IngeTrazo com `INGETRAZO_PERF=1`. As linhas `trazomob.apply.*` (leitura de parâmetros, reconstrução, histórico e invalidação de cache) e `trazomob.wall_sync` são gravadas no mesmo log do host (`~/ingetrazo-perf.log`, ou `$INGETRAZO_PERF_LOG`). A pintura do viewport é assíncrona e aparece na telemetria do próprio viewport.

---

## 13. Alinhamento, Distribuição e Grupos (Assemblies)

Além das ferramentas da barra lateral para seleção múltipla (`ui/sidebar_align_controller.py` e `domain/assembly.py`), o TrazoMob conta com a ferramenta interativa **Alinhar & Apoiar Objetos (`Shift+A`)**.

### 13.1 Ferramenta Interativa Alinhar & Apoiar (`Shift+A`)
Permite alinhar ou encostar qualquer objeto 3D por seus pontos notáveis (Centro XYZ, centros de faces, pontos médios de arestas e 8 quinas) em apenas 2 cliques:
1. Ative na barra superior (**Alinhar & Apoiar**) ou tecle **`Shift+A`**.
2. **1º Clique (Origem):** Passe o cursor sobre o objeto que deseja mover e clique no ponto/quina/centro de referência.
3. **2º Clique (Destino):** Clique no ponto notável ou face de destino em outro objeto ou parede.
4. **Teclas e Modificadores durante o uso:**
   - **`TAB` (ou `Shift+TAB`):** Alterna entre **Alinhar e Mover (Snap Total)** e **Apenas Alinhar Posição**.
   - **`X` / `Y` / `Z`:** Trava ou destrava o alinhamento exclusivamente em um eixo específico.
   - **`A`:** Libera todos os eixos (`XYZ`).
   - **Segurar `Ctrl` (ou `Alt`):** Ativa modo de cópia ao alinhar.
   - **`Esc`:** Cancela o alinhamento em andamento.

### 13.2 Centralização Automática (Seleção Múltipla)
Quando 2 ou mais módulos são selecionados com **`Ctrl` + Clique**:
- **✛ Centro (XY):** Centraliza o módulo secundário perfeitamente no centro de largura e profundidade do móvel base (ex.: centralizar um cooktop ou uma cuba sobre um balcão).
- **↔ Largura (X):** Centraliza no eixo horizontal.
- **↕ Profundidade (Y):** Centraliza no sentido frente-fundo.
- **⬍ Altura (Z):** Alinha os centros verticais.

### 13.3 Distribuir Módulos no Vão
- Selecione 3 ou mais módulos colocados entre duas paredes ou extremidades:
- Clique em **↔ Distribuir Módulos no Vão**: o TrazoMob calcula o vão residual livre e divide os módulos com espaçamento rigorosamente uniforme ou preenche o vão contiguamente com ajustes de arremate/fechamento.

### 13.4 Agrupamento Inteligente (Assembly)
- **📦 Agrupar Módulos Selecionados:** Transforma vários módulos avulsos (ex.: bancada + 3 balcões + torre) em um conjunto único coeso (*Assembly*).
  - O grupo pode ser movido ou duplicado como um único bloco.
  - Os módulos internos continuam **100% paramétricos** (dê duplo clique para editar um armário interno).
- **📤 Desagrupar:** Dissolve o grupo devolvendo os móveis soltos ao modelo sem perder nenhuma medida ou acabamento.

---

## 14. Cinemática 3D e Detecção de Colisões

O TrazoMob possui cinemática real de ferragens para verificar interferências antes da fabricação (`interact.py` e `collision.py`).

### 14.1 Interação Dinâmica
- **Atalho no Teclado (Tecla I):** Ativa a ferramenta interativa de clique. Clique diretamente na porta ou gaveta na viewport 3D para abri-la ou fechá-la.
- **Slider Contínuo (0% a 100%):** No painel lateral (cartão *Abertura Dinâmica 3D*), deslize a barra para abrir progressivamente todas as portas e gavetas em conjunto.
- **Botões Rápidos:** Clique em **Fechar (0%)**, **50%** ou **100%** para conferência visual rápida da cena.

### 14.2 Teste Automático de Colisões
- Com as portas ou gavetas abertas, clique no botão **⚠️ Testar Colisões**:
- O algoritmo calcula as caixas delimitadoras colidentes (AABB / OBB) entre:
  - Frentes de gavetas abertas e puxadores de armários vizinhos em L.
  - Portas basculantes abertas batendo no teto ou luminárias pendentes.
  - Portas de canto batendo na alvenaria ou bancadas.
- Caso haja interferência, um banner vermelho alerta o usuário e destaca as peças colidentes na tela.

---

## 15. Luminotécnica e Spots Físicos

O sistema luminotécnico do TrazoMob (`light_tools.py`) simula física real de luz para projetos de interiores e marcenaria de alto padrão.

### 15.1 Inserção de Luminárias
1. Clique no botão de **Iluminação** na barra superior para abrir o gerenciador.
2. Escolha o tipo de fonte de luz:
   - **Spot Direcionável:** Emite cone de luz cônico para iluminação pontual de bancadas, nichos ou quadros.
   - **Fita LED Linear:** Perfil retangular de iluminação contínua (ex.: sob armários aéreos ou painéis ripados).
   - **Ponto Omni (360°):** Lâmpada esférica para plafons, pendentes e arandelas.
3. Clique na cena 3D para posicionar a luminária.

### 15.2 Ajustes Fotométricos e Mira 3D
- **Temperatura de Cor (Kelvin):**
  - *2400K - 2700K:* Branco Muito Quente / Âmbar (dormitórios e cabeceiras).
  - *3000K:* Branco Quente (salas e aconchego).
  - *4000K:* Branco Neutro (cozinhas, bancadas e áreas de corte).
  - *6500K:* Luz Fria do Dia (corporativo).
- **Potência (Watts / Lúmens):** Ajuste de intensidade de emissão.
- **🎯 Mirar Spot no 3D:** Clique neste botão e em seguida clique sobre o ponto exato da bancada, pia ou fogão onde o centro do facho luminoso deve atingir. O spot orienta seu vetor angular automaticamente.
- **Fotometria IES:** Carregue arquivos `.ies` de fabricantes (Stella, Brilia, Philips) para reproduzir curvas reais de emissão ótica no renderizador.

---

## 16. Materiais PBR e Render Foto-Realista

O TrazoMob possui integração nativa com o **Blender Cycles / EEVEE Next** (`render/` e `ui/material_editor_dialog.py`) para renderizar imagens de catálogo foto-realistas diretamente do projeto. Para detalhes avançados de luzes, filtros de emissivos e vidro fino, consulte também o [`MANUAL_ILUMINACAO.md`](file:///d:/projetos/ingetrazo/trazomob/docs/MANUAL_ILUMINACAO.md).

### 16.1 Editor de Materiais PBR (`ui/material_editor_dialog.py`)
1. Na barra do TrazoMob ou no botão **🎨 Configurar Materiais PBR...** do diálogo de render, abra o **Editor de Materiais PBR**.
2. Use a lista de materiais do projeto (com miniaturas de cor/textura) ou clique em **🔍 Capturar do Modelo 3D (Conta-gotas)** (`MaterialPickerTool`) para clicar diretamente em qualquer face do 3D e selecionar o material correspondente. Ao selecionar um material na lista, suas faces são destacadas em **ciano (`#00D4FF`)** na viewport.
3. Escolha entre **12 categorias PBR** (`Auto-Detectar`, `Madeira / MDF / Marcenaria`, `Mármore / Granito / Porcelanato / Piso`, `Cromado / Inox Polido`, `Metal / Alumínio`, `Plástico / Acrílico`, `Vidro / Espelho / Reflecta`, `Tecido / Estofado / Cortina`, `Couro / Couro Ecológico`, `Tinta de Parede / Drywall / Cimento`, `Cerâmica / Louça / Azulejo` e `Luz Emissiva / Neon / Fita LED`) e seu respectivo **Acabamento** (subtipo).
4. Ajuste com os 3 controles deslizantes:
   - **Rugosidade:** Do acabamento espelhado/alto brilho ao fosco acetinado.
   - **Refletividade:** Intensidade de reflexão e camada especular/verniz (*Clearcoat*).
   - **Relevo Tátil (Bump):** Profundidade de veios de madeira, poros de pedra ou textura de tecidos.
5. Utilize **Restaurar Padrão Deste Material**, **💾 Salvar como Padrão Global** (para reutilizar automaticamente em novos projetos) ou **Aplicar ao Projeto**.

### 16.2 Executando o Render Foto-Realista (`render/dialog.py`)
1. Posicione a câmera do IngeTrazo no ângulo desejado (ou configure Cenas/Páginas no projeto).
2. Clique em **Render Foto-Realista (TrazoMob)** na barra superior.
3. No painel esquerdo de configuração:
   - **Iluminação do Ambiente:** 5 presets disponíveis — **☀️ Dia Claro (Luz Solar + Céu Físico)**, **🌅 Entardecer / Golden Hour**, **🛋️ Noturno Aconchegante (Fitas LED + Luz Suave)**, **🏢 Estúdio Comercial** e **🌑 Totalmente Escuro / Breu (Apenas Luzes Internas)**.
   - **Motor:** **Cycles (Máximo Foto-Realismo)** ou **EEVEE Next (Ultra-Rápido)**.
   - **Amostras e Resolução:** 4 níveis (*Rápido (Prévia)*, *Média*, *Alta Definição (Cliente)*, *Ultra / 4K*) e resolução selecionável entre **`Aspecto da Janela 3D (Idêntico ao Viewport)`**, HD, Full HD, 2K ou 4K.
   - **Recursos Especiais:** **Corrigir Verticais (Perspectiva 2 Pontos)**, **🏛️ Maquete Branca / Clay Render** (estudo volumétrico em gesso fosco), **🎯 Renderizar Apenas Seleção** e **Sombra do Sol** ajustável de `0.5 °` (dura) a `15.0 °` (suave).
4. Clique em **🚀 Iniciar Render Foto-Realista** (vista atual) ou **📸 Renderizar Todas as Cenas (Lote)** (Batch Render de todas as Cenas/Páginas do projeto).
5. No visualizador à direita, inspecione o resultado com **Zoom (Scroll/Botões)**, **Pan**, **🔍 100% (1:1)** e **⛶ Ajustar à Tela**, e depois utilize **💾 Salvar Imagem...** ou **🟠 Abrir no Blender...**.

---

## 17. Cutlist, Fitamento, Junções e Furações

O motor de fabricação (`production/cutlist_tab.py`, `production/parts.py`, `production/machining.py` e `production/joint_resolver.py`) analisa toda a montagem para extrair a lista completa de produção.

### 17.1 Extração Automática de Peças
A lista de peças identifica automaticamente cada componente, agrupável por módulo ou por ambiente:
- Laterais (esquerda e direita)
- Base inferior e Tampo superior
- Prateleiras móveis e fixas
- Travessas de sustentação (deitadas e em pé)
- Divisórias internas
- Fundo do armário
- Frentes de gavetas e caixas internas
- Portas de giro, basculantes ou de correr

### 17.2 Controle de Fitamento de Borda
Para cada peça, é exibido o mapa de fitas nos 4 lados:
- **C1 e C2:** Bordas dos dois comprimentos da chapa.
- **L1 e L2:** Bordas das duas larguras da chapa.
- **Botões de Aplicação Rápida:**
  - *4 Lados:* Aplica fita em todo o contorno (padrão para frentes e portas).
  - *1 Comp.:* Aplica fita apenas na face frontal aparente (padrão para prateleiras e laterais).
  - *2 Comp.:* Aplica nas duas bordas longitudinais.
  - *Limpar:* Remove fitamento da peça selecionada.
- **Espessura da Fita:** Alterne com um clique entre 0.45 mm, 1.0 mm ou 2.0 mm.

### 17.3 Veio da Madeira, JointResolver e Furações Técnicas
- **Sentido do Veio:** Marque a caixa de seleção de veio para garantir que as portas e painéis amadeirados sejam cortados com as fibras alinhadas vertical ou horizontalmente.
- **Sincronização de Juntas (`JointResolver` + `machining.py`):** Analisa os encontros face a face entre as chapas do módulo para alinhar furações correspondentes sem furar faces livres:
  - Dobradiças caneco **Ø35 mm** (profundidade padrão `12 mm`, afastamento de `100 mm`) e seus calços;
  - Corrediças no padrão **Sistema 32 mm**;
  - Dispositivos de caixa (**Minifix + Cavilha**, **Cavilha + Parafuso**, **Parafuso**, **Cavilhas**);
  - Suportes de prateleira em **Cavilhas de Topo (Ø8 mm)** ou conectores **Häfele VB 35 / VB 36 (Ø20 mm)** com pino de aço **Ø5 × 11,5 mm**.

---

## 18. Otimizador de Corte 2D (Nesting) e Sobras

O módulo `production/optimizer.py` e `production/cut_plan_viewer.py` realiza o aproveitamento otimizado de chapas de MDF.

### Como Gerar e Analisar o Plano de Corte:
1. Na barra superior ou no diálogo principal, clique em **📐 Plano de Corte 2D**.
2. O otimizador calcula o arranjo das peças considerando:
   - Tamanho bruto da chapa (padrão: `2.750 × 1.830 mm` ou personalizável).
   - Espessura de corte do disco da serra (*Kerf*, padrão: `4 mm`).
   - Refilo perimetral de limpeza das bordas (padrão: `10` a `15 mm`).
   - Respeito obrigatório ao sentido do veio da madeira.
3. O visualizador gráfico exibe cada chapa numerada com cores distintas por módulo e destaca **sobras reaproveitáveis** (retalhos `>= 200 × 200 mm`).
4. **Métricas de Eficiência e CNC:** Exibe a porcentagem de aproveitamento útil da chapa, metragem linear de corte e o botão **📐 Exportar DXF CNC** diretamente sobre a chapa exibida.

---

## 19. Etiquetas Técnicas (Code 128 + QR Code) e Manual de Montagem

Para uso na marcenaria ou fábrica de corte, o TrazoMob gera **Etiquetas Técnicas** (`production/labels.py`, `barcode.py`, `qr.py`) e **Manuais de Montagem** (`production/assembly_manual.py`).

### 19.1 Recursos das Etiquetas (`🏷️ Etiquetas de Produção`)
- **Tamanho Padrão:** Compatível com impressoras térmicas (ex.: Zebra, Argox, Elgin nos formatos 100×60 mm ou folhas A4), renderizadas em alta resolução (`3x`) para nitidez máxima na impressão.
- **Conteúdo da Etiqueta:**
  - Nome da Peça e Nome do Armário Pai.
  - Medida final acabada (Comprimento × Largura × Espessura em mm) e medida de corte bruto.
  - Indicadores gráficos das 4 bordas para fitamento (C1, C2, L1, L2) e padrão de acabamento do MDF.
  - **Código de Barras Code 128 nativo + QR Code nativo:** Gerados internamente com o identificador/carga da peça para leitura ótica por leitores convencionais ou câmera/coletor na linha de montagem.
- **Operação:** Na aba de Cutlist, clique em **🏷️ Etiquetas de Produção** e escolha entre imprimir a lista completa ou apenas as peças do módulo selecionado.

### 19.2 Manual de Montagem (`🛠️ Manual de Montagem`)
- Na aba de Cutlist, clique em **🛠️ Manual de Montagem** para exportar um **documento HTML interativo/imprimível** (`Manual_Montagem_<projeto>.html`).
- O manual agrupa automaticamente todas as peças por módulo, consolida a lista de ferragens necessária e detalha medidas e instruções de usinagem para a equipe de montagem em obra.

---

## 20. Orçamentação Híbrida (PIN), Custos e Propostas Comerciais

O TrazoMob opera com um sistema de **Precificação Híbrida em 2 Camadas** (`ui/pricing_dialog.py`, `ui/proposal_dialog.py` e `production/pricing.py`), separando a tela de venda ao cliente da tabela confidencial de custos e margens da marcenaria.

### 20.1 Modo Apresentação — Visão do Cliente (`💼 Orçamento & Preços`)
Aberto na aba Cutlist pelo botão **💼 Orçamento & Preços** (exibindo **apenas valores finais de venda**, sem expor custos de compra ou markup na frente do cliente):
- **Seletor Instantâneo de Ferragens:** Alterne ao vivo entre **🌱 Linha Econômica**, **⭐ Linha Standard (Com Amortecedores)** e **💎 Linha Premium (Corrediças Ocultas / Blum)** para recalcular os valores na hora.
- **Resumo por Ambiente e Pagamento:** Tabela consolidada por cômodo/ambiente (com quantidade de peças e m²) e cartões com valores **À Vista** e **À Prazo / Parcelamento**.
- **Proposta Comercial (HTML / PDF):** Botão **📄 Gerar Proposta Comercial (HTML/PDF)** para emitir documento formal com dados da empresa, cliente, ambientes e condições comerciais.

### 20.2 Painel Administrativo Protegido por PIN (`🔐 Custos & Tabela de Preços`)
Acessado pelo botão **🔐 Custos & Tabela de Preços** (protegido por **PIN de 4 dígitos** via `PinInputDialog` quando configurado), reunindo 5 abas de calibração:
- **🪵 Chapas & Fitas:** Valores de MDF e fitas (`0.45mm`, `1.0mm`, `2.0mm`), alternando o método de cálculo entre **Área Líquida (m²) + % de perda** ou **Chapas Inteiras compradas (Plano de Corte)**.
- **🔩 Ferragens & Linhas:** Custos por peça e multiplicadores/valores das linhas Econômica, Standard e Premium.
- **🏭 Serviços & Montagem:** Mão de obra, terceirização de corte/fitamento, frete e montagem.
- **📈 Formação de Preço:** Escolha entre **Composição Detalhada (Custos + Montagem + Markup % + Impostos %)** ou **Fator Multiplicador Rápido sobre Materiais**.
- **🏢 Empresa & Segurança:** Cadastro da marcenaria para cabeçalho de propostas e definição/alteração do **PIN de 4 dígitos**.

---

## 21. Exportação, Integrações Externas e Tabela de Atalhos

### 21.1 Exportação e Integrações
- **Exportar DXF CNC (`📐 Exportar DXF CNC`):** Exporta peças individuais ou o plano completo da chapa em **DXF R12 (ASCII, escala 1:1 em mm)** com camadas padronizadas de contorno, furações, rasgos e textos para máquinas Router/CNC e softwares CAM (`production/dxf_cnc.py`).
- **Copiar p/ TrazoMob (`📋 Copiar p/ TrazoMob`):** Copia os dados da cutlist para a área de transferência em formato estruturado.
- **Exportar CSV (`💾 CSV`):** Gera arquivo de planilha compatível com planilhas eletrônicas e otimizadores externos.
- **Exportar JSON (`💾 JSON`):** Exporta toda a árvore de dados paramétricos e usinagens para automações e ERPs industriais.
- **📄 Relatório Executivo HTML:** Documento técnico completo com tabela de materiais, área em m², metragem de fita e lista analítica de peças.

### 21.2 Tabela Resumida de Teclas de Atalho

| Atalho | Função | Descrição |
| :---: | :--- | :--- |
| **W** | **Construir Paredes** | Abre o editor de Planta Baixa 2D para alvenaria |
| **I** | **Interagir** | Ativa o cursor para abrir e fechar portas e gavetas no 3D |
| **Shift + A** | **Alinhar & Apoiar** | Alinha ou apoia objetos em 2 cliques pelos pontos notáveis (`TAB`, `X/Y/Z/A`, `Ctrl`) |
| **Alt + S** | **Snap Magnético** | Alterna entre snapping magnético e ajuste fino livre |
| **M** | **Mover** | Movimenta objetos/grupos no 3D com a ferramenta nativa do IngeTrazo |
| **R** | **Rotacionar** | Rotaciona objetos manualmente |
| **Alt + X** | **Modo Raio-X** | Alterna transparência para visualização de interiores |
| **Ctrl + Z** | **Desfazer** | Desfaz a última ação (incluindo recortes de alvenaria e preenchimentos) |
| **Ctrl + Y** | **Refazer** | Refaz a ação desfeita no histórico |
| **Ctrl + Clique** | **Seleção Múltipla** | Seleciona vários armários para alinhamento ou agrupamento |
| **Delete** | **Excluir** | Remove o módulo, parede ou luminária selecionada |

---

## 22. Biblioteca de Componentes do Usuário

O TrazoMob não hospeda, baixa nem redistribui modelos de terceiros. O que
existe aqui é um **índice dos arquivos que o próprio usuário já possui** —
uma geladeira baixada da internet, o catálogo de um fabricante, um
modelo comprado de um artista. O aplicativo apenas registra onde o arquivo
está, o que ele é e como deve ser lido; a coleção continua sendo do usuário.

### 22.1 Onde a biblioteca aparece
- **Painel Componentes → Minha biblioteca…:** grade com busca e filtros por
  categoria, tipo e marca; inserir, editar e remover.
- **Painel Componentes → Importar componente…:** abre a ficha de importação
  de um arquivo e, ao confirmar, já o coloca na cena.
- **Aba Decoração → ⭐ Meus Componentes:** um botão por marca, com a
  quantidade (`Brastemp (4)`); o clique abre a biblioteca já filtrada por
  aquela marca. Há também `Todos`, `Importar…` e `Gerenciar…`.

### 22.2 Ficha de importação
Preencha o que ajuda a achar o modelo depois: **nome, categoria, tipo**
(geladeira, fogão, sofá…), **marca, modelo, tags, fonte, licença, autor** e
**notas**. As medidas **L × P × A** podem ser tiradas do próprio arquivo
(botão *Medir*) e são usadas para ajustar o modelo ao tamanho real.

Como o formato não declara unidade nem eixo vertical, informe a **unidade do
arquivo** (m, cm, mm, in, ft) e o **eixo vertical**: *Z up* (padrão IngeTrazo)
ou *Y up* (comum em arquivos GLB/OBJ). A escolha fica
gravada com o componente, então as próximas inserções não perguntam nada.

### 22.3 Gerenciado ou referência
- **Copiar para a biblioteca (gerenciado):** o arquivo e seus anexos (MTL,
  texturas, `.bin`) são copiados para dentro da biblioteca. Mover ou apagar o
  original não quebra o componente. É o modo de um arquivo avulso.
- **Apenas indexar (referência):** só o caminho é guardado; nada é copiado.
  É o modo de **Adicionar pasta…**, que percorre a pasta (e as subpastas) e
  transforma os nomes das pastas em tags. Se o arquivo sumir, a ficha avisa
  *(missing)* e continua lá para ser relocalizada ou removida — o original
  nunca é apagado.

### 22.4 Formatos e onde ficam os arquivos
Formatos lidos: **OBJ, GLB, DAE, STL, SKP e IGZ**. As miniaturas são
desenhadas a partir da geometria, uma por vez, conforme você rola a grade.

A biblioteca é global (compartilhada por todos os documentos) e fica em:

| Sistema | Pasta |
| :--- | :--- |
| Windows | `%LOCALAPPDATA%\IngeTrazo\components` |
| macOS | `~/Library/Application Support/IngeTrazo/components` |
| Linux | `~/.local/share/ingetrazo/components` |

A variável de ambiente `INGETRAZO_COMPONENTS` aponta para outra pasta (outro
disco, uma pasta de rede). O botão **Abrir pasta** leva direto ao local.

### 22.5 Licenças
O aplicativo apenas indexa o que já é seu. A licença de origem continua
valendo: modelos de catálogos online, por exemplo, podem ser usados em projetos,
mas não podem ser agregados, redistribuídos nem revendidos como catálogo.
Registre a licença e o autor na ficha — é o que permite provar a procedência
depois.

---

*Manual elaborado para o TrazoMob — IngeTrazo CAD 3D.*

