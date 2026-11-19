# Manual do Sistema de Iluminação e Render Foto-Realista (TrazoMob)
*Guia técnico oficial do sistema profissional de iluminação e renderização PBR para marcenaria.*

---

## 1. Visão Geral da Arquitetura
O sistema de iluminação do **TrazoMob** opera em duas camadas coordenadas:
1. **Camada Interativa (IngeTrazo 3D):**
   - Lâmpadas, spots e fitas de LED possuem representação física volumétrica (`Group` atômico).
   - Podem ser visualizados, selecionados com o mouse, movidos com a ferramenta de movimentação (`M`), elevados no eixo Z e rotacionados/mirados (`Alvo 3D`).
2. **Camada de Render Foto-Realista (Blender Cycles / EEVEE):**
   - **Exclusão Automática de Oclusão:** Durante a exportação, a casca geométrica do gizmo indicador é automaticamente descartada no renderizador. Assim, a fonte de luz nunca fica presa dentro da sua própria malha e ilumina 100% o ambiente.
   - Cálculo físico real de fótons, sombras suaves e reflexos indiretos em madeiras, mármores, vidros e metais.

---

## 2. Tipos de Fontes de Luz

### 2.1 Spot Direcionável (Dicroica / Trilho)
- **Abertura do Facho (Spot Angle):** Controle de 10° (facho concentrado para destacar quadros ou adornos) até 120° (abertura ampla de iluminação geral).
- **Suavidade / Falloff (Transição de Borda):**
  - `0.0`: Borda dura e nítida (estilo holofote ou teatro).
  - `0.35` (Padrão): Borda suave clássica de lâmpada dicroica/PAR em gesso.
  - `1.0`: Gradiente ultra suave sem recorte visual aparente.
- **Mira 3D (Alvo):** Clique no botão *🎯 Mirar Spot no 3D* e clique diretamente na bancada, armário ou chão onde o centro da luz deve incidir.

### 2.2 Fotometria Real IES (Perfis dos Fabricantes)
- Permite carregar arquivos `.ies` fornecidos por fabricantes de iluminação (Stella, Osram, Philips, Brilia).
- **Como usar:** No painel de propriedades do spot, clique em **📂 Carregar Fotometria IES...** e aponte o arquivo `.ies`.
- O renderizador Cycles aplicará a curva física real de emissão (incluindo desenhos de asas de morcego, recortes e flares óticos).

### 2.3 Luz Omni / Ponto (Lâmpadas Bulbo, Arandelas e Pendentes)
- Emite luz esférica uniforme para todas as direções.
- Ideal para o interior de luminárias decorativas, arandelas de parede e globos de vidro.

### 2.4 Fita LED / Iluminação Linear de Nichos
- Luz física tipo `AREA` com largura de perfil de marcenaria (20mm) e comprimento exato marcado no 3D.
- Perfeita para sob armários aéreos, painéis ripados e prateleiras iluminadas.

---

## 3. Temperatura de Cor (Kelvin) e Potência

| Kelvin | Nome / Sensação | Aplicação Recomendada |
| :--- | :--- | :--- |
| **2400K - 2700K** | Branco Muito Quente (Âmbar) | Cabeceiras, nichos decorativos, iluminação noturna intimista. |
| **3000K** | Branco Quente | Salas de estar, jantar e dormitórios (aconchego com fidelidade de cor). |
| **4000K** | Branco Neutro | Cozinhas, lavanderias, bancadas de trabalho e marcenaria corporativa. |
| **6500K** | Branco Frio (Luz do Dia) | Escritórios técnicos e consultórios. |

---

## 4. Vidro Fino Arquitetônico (Thin Glass)
Em softwares CAD de marcenaria, modelamos portas de vidro, prateleiras e janelas como uma **única face simples** (sem espessura de 4mm) para manter o projeto leve:
- O motor de render do TrazoMob detecta automaticamente materiais de vidro (`vidro`, `reflecta`, `canelado`) e aplica o shader **Thin Glass**.
- Ele desativa a refração volumétrica dupla infinita (que deixaria a imagem preta ou distorcida) e aplica:
  - Transmissão pura e límpida de luz.
  - Reflexo de Fresnel superficial (Coat) de alto brilho.
  - Versão **Reflecta Bronze / Fumê** com efeito espelhado metálico suave.
  - Versão **Canelado / Fluted** com ondulado de relevo procedural automático.

---

## 5. Render em Lote de Cenas (Batch Render)
- **Localização:** Caixa de diálogo de Render do TrazoMob -> **📸 Renderizar Todas as Cenas (Lote)**.
- **Como funciona:**
  1. Crie e salve seus pontos de vista e câmeras na bandeja lateral de **Scenes** (ex: *01_Perspectiva_Geral*, *02_Ilha_Cozinha*, *03_Detalhe_Nicho*).
  2. Clique em **📸 Renderizar Todas as Cenas (Lote)**.
  3. O TrazoMob processa e renderiza automaticamente cada uma das cenas salvas em sequência, gerando toda a apresentação para o cliente sem que você precise aguardar entre uma imagem e outra.

---

## 6. Renderizar Apenas a Seleção (Render Ultrarrápido de Detalhes)
- **Localização:** Caixa de diálogo de Render do TrazoMob -> **🎯 Renderizar Apenas Seleção**.
- **Como funciona:**
  - Selecione no 3D apenas o móvel, bancada ou puxador que você está ajustando no momento.
  - O motor ignora o resto da casa e processa a imagem em **pouquíssimos segundos**, ideal para validar acabamentos de MDF, puxadores e fitas de LED pontuais com agilidade máxima.

---

## 7. Controle de Sombras do Sol e Luz Natural
- **Controle:** `Sombra do Sol` (Ângulo em Graus) na janela de render.
- **Como calibrar:**
  - `0.5°` a `1.0°`: Sol de meio-dia a céu aberto (sombras nítidas e recortadas).
  - `2.5°` a `5.0°` (Padrão Recomendado): Luz natural de janela com penumbra suave e difusa, criando um clima acolhedor nos móveis.
  - `10.0°`: Dia nublado com sombras totalmente difusas e suaves.

---

## 8. Sistema de Proxies Automáticos (Objetos Leves no 3D, Alta Definição no Render)
- Para manter a viewport do IngeTrazo leve e rápida mesmo com sofás capitonê, vasos de plantas ou lustres pesados:
  - Nomeie o objeto como `NomeObjeto_PROXY` (ou coloque o arquivo `NomeObjeto_HIGHPOLY.glb` ou `NomeObjeto_HIGHPOLY.obj` na mesma pasta).
  - Na tela do IngeTrazo você enxerga uma caixa/malha leve.
  - No momento do render, o motor substitui a caixa pela geometria de alta fidelidade automaticamente.

---

## 9. Materiais Emissores Práticos: `Emit[...]` e `EmitFake`
Se você não quiser criar uma lâmpada ou spot manual, você pode nomear ou aplicar materiais diretamente:
- **`Emit[potência]` (Ex: `Emit[80]` ou `Emit[150]`):**  
  Converte a face ou objeto numa superfície luminosa física real que projeta luz nos móveis ao redor.
- **`EmitFake`:**  
  Faz o material brilhar como tela de TV ligada, visor de eletrodoméstico ou botão iluminado, sem gerar ruído excessivo de sombras na cena.

---

## 10. Modo "Maquete Branca" (Clay Render)
- **Localização:** Caixa de diálogo de Render do TrazoMob (`Renderizar Projeto (Blender)` -> `🏛️ Maquete Branca / Clay Render`).
- **Função:** Substitui temporariamente todas as texturas e cores por uma resina fosca branca neutra.
- **Benefício:**
  - Estudo puro e despoluído de volumetria, sombra e iluminação.
  - Tempo de render até 3x mais rápido.
  - Perfeito para validação inicial de pontos de luz com arquitetos e clientes antes de produzir o render final colorido.

---

## 11. Boas Práticas para Marcenaria
1. **Evite luzes coladas em superfícies:** Ao posicionar spots de embutir no gesso, mantenha o centro da luz cerca de 2cm a 5cm abaixo do teto para que o facho se espalhe naturalmente.
2. **Potência Realista:**
   - Fitas LED decorativas: 50W a 150W.
   - Spots individuais de destaque: 200W a 400W.
   - Plafons ou luminárias gerais de centro de sala: 800W a 1500W.
3. **Câmera Arquitetônica:** Mantenha sempre marcado **Corrigir Verticais (Perspectiva 2 Pontos)** para garantir que as linhas de armários verticais fiquem 100% paralelas, padrão de fotografia de revista de arquitetura.
