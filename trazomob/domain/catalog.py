# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Catálogo de módulos paramétricos de marcenaria para TrazoMob."""
from __future__ import annotations

import re
import unicodedata

MODULE_CATALOG = {
    "Cozinha — Inferiores": [
        {
            "id": "balcao",
            "nome": "Balcão com Portas",
            "desc": "Balcão inferior padrão de chão. Laterais, base, travessas superiores, prateleira e portas.",
            "largura": 800, "altura": 720, "profundidade": 550, "rodape": 100,
            "has_portas": True, "num_portas": 2, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 1, "has_fundo": True, "has_rodape": True,
            "travessa_frontal_em_pe": False,
            "larg_travessa_frontal_mm": 70, "larg_travessa_traseira_mm": 70,
            "recuo_porta_topo_mm": 50,
            "default_z": 0.0,
        },
        {
            "id": "gaveteiro",
            "nome": "Balcão Gaveteiro",
            "desc": "Módulo gaveteiro completo. Caixas de gaveta internas com desconto real de 26mm para corrediças.",
            "largura": 450, "altura": 720, "profundidade": 550, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": True, "num_gavetas": 4,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": True, "has_rodape": True,
            "travessa_frontal_em_pe": False,
            "larg_travessa_frontal_mm": 70, "larg_travessa_traseira_mm": 70,
            "recuo_porta_topo_mm": 50,
            "default_z": 0.0,
        },
        {
            "id": "balcao_misto",
            "nome": "Balcão Misto (Gaveteiro + Portas)",
            "desc": "Balcão inferior misto com gaveteiro de 4 gavetas à esquerda e vão com 2 portas e prateleira à direita.",
            "largura": 1200, "altura": 720, "profundidade": 550, "rodape": 0,
            "has_portas": True, "num_portas": 2, "has_gavetas": True, "num_gavetas": 4,
            "has_prateleiras": True, "num_prateleiras": 1, "has_fundo": True, "has_rodape": True,
            "largura_gaveteiro": 450,
            "lado_gaveteiro": "esquerda",
            "travessa_frontal_em_pe": False,
            "larg_travessa_frontal_mm": 70, "larg_travessa_traseira_mm": 70,
            "recuo_porta_topo_mm": 50,
            "default_z": 0.0,
        },
        {
            "id": "balcao_canto",
            "nome": "Balcão de Canto Reto (L Cego)",
            "desc": "Balcão de canto com montante cego frontal para junção perpendicular e 1 porta de acesso ao fundo.",
            "largura": 1000, "altura": 720, "profundidade": 550, "rodape": 0,
            "has_portas": True, "num_portas": 1, "fixed_portas": True, "has_gavetas": False, "num_gavetas": 0,
            "lado_cego": "esquerda",
            "has_prateleiras": True, "num_prateleiras": 1, "has_fundo": True, "has_rodape": True,
            "travessa_frontal_em_pe": False,
            "larg_travessa_frontal_mm": 70, "larg_travessa_traseira_mm": 70,
            "recuo_porta_topo_mm": 50,
            "default_z": 0.0,
        },
        {
            "id": "balcao_canto_l",
            "nome": "Balcão Canto L (2 Portas 90°)",
            "desc": "Balcão de canto em L autêntico com duas faces frontais abertas, batente/coluna de quina 90°, duas portas articuladas e vão contínuo.",
            "largura": 1000, "altura": 720, "profundidade": 1000, "rodape": 0,
            "has_portas": True, "num_portas": 2, "fixed_portas": True, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 1, "has_fundo": True, "has_rodape": True,
            "travessa_frontal_em_pe": False,
            "larg_travessa_frontal_mm": 70, "larg_travessa_traseira_mm": 70,
            "recuo_porta_topo_mm": 50,
            "larg_asa_esq": 550, "larg_asa_dir": 550,
            "tem_batente_canto": False,
            "default_z": 0.0,
        },
        {
            "id": "porta_tempero",
            "nome": "Balcão Porta-Tempero / Toalheiro",
            "desc": "Módulo estreito para temperos e garrafas com frente única deslizante e opção 100% MDF ou Kit Aramado.",
            "largura": 200, "altura": 720, "profundidade": 550, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": True, "num_gavetas": 1,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": True, "has_rodape": True,
            "tipo_estrutura_tempero": "mdf",
            "cor_aramado": "cromado",
            "travessa_frontal_em_pe": False,
            "larg_travessa_frontal_mm": 70, "larg_travessa_traseira_mm": 70,
            "recuo_porta_topo_mm": 50,
            "default_z": 0.0,
        },
        {
            "id": "balcao_forno",
            "nome": "Balcão Forno Embutido",
            "desc": "Caixa padrão de balcão com frente cega para embutimento do forno e opção de gaveta inferior com altura configurável.",
            "largura": 700, "altura": 720, "profundidade": 550, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": True, "num_gavetas": 1,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": True,
            "travessa_frontal_em_pe": True,
            "larg_travessa_frontal_mm": 70, "larg_travessa_traseira_mm": 70,
            "recuo_porta_topo_mm": 50,
            "tem_gaveta": True,
            "alt_gaveta_mm": 150,
            "default_z": 0.0,
        },
    ],
    "Cozinha — Aéreos": [
        {
            "id": "aereo",
            "nome": "Aéreo com Portas",
            "desc": "Armário aéreo padrão para fixação superior na parede com portas de abrir e prateleira interna.",
            "largura": 800, "altura": 600, "profundidade": 350, "rodape": 0,
            "has_portas": True, "num_portas": 2, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 1, "has_fundo": True, "has_rodape": False,
            "default_z": 1.4,
        },
        {
            "id": "aereo_basculante",
            "nome": "Aéreo Basculante (1 Porta)",
            "desc": "Aéreo horizontal com porta basculante única com abertura vertical por pistão a gás.",
            "largura": 800, "altura": 400, "profundidade": 350, "rodape": 0,
            "has_portas": True, "num_portas": 1, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": True, "has_rodape": False,
            "default_z": 1.5,
        },
        {
            "id": "aereo_basculante_duplo",
            "nome": "Aéreo Basculante Duplo (2 Portas)",
            "desc": "Aéreo alto com 2 portas basculantes horizontais sobrepostas e divisória central.",
            "largura": 800, "altura": 720, "profundidade": 350, "rodape": 0,
            "has_portas": True, "num_portas": 2, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 1, "has_fundo": True, "has_rodape": False,
            "default_z": 1.4,
        },
        {
            "id": "aereo_correr",
            "nome": "Aéreo Portas de Correr",
            "desc": "Armário aéreo suspenso para portas de correr de 2 a 4 vãos com divisórias estruturais internas e trilhos duplos.",
            "largura": 1500, "altura": 600, "profundidade": 350, "rodape": 0,
            "has_portas": True, "num_portas": 3, "num_vaos": 3, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 0, "has_fundo": True, "has_rodape": False,
            "default_z": 1.4,
        },
        {
            "id": "aereo_microondas",
            "nome": "Aéreo Nicho Micro-ondas",
            "desc": "Módulo aéreo com nicho aberto para micro-ondas e compartimento superior fechado com porta.",
            "largura": 600, "altura": 720, "profundidade": 400, "rodape": 0,
            "has_portas": True, "num_portas": 1, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 1, "has_fundo": True, "has_rodape": False,
            "default_z": 1.4,
        },
    ],
    "Cozinha — Torres": [
        {
            "id": "torre_quente",
            "nome": "Torre Quente (Forno + Micro + Despensa)",
            "desc": "Torre completa de eletros embutidos. 2 gavetões inferiores, nicho para forno de embutir, nicho para micro-ondas e despenseiro superior.",
            "largura": 650, "altura": 2200, "profundidade": 580, "rodape": 100,
            "has_portas": True, "num_portas": 2, "has_gavetas": True, "num_gavetas": 2,
            "has_prateleiras": True, "num_prateleiras": 3, "has_fundo": True, "has_rodape": True,
            "default_z": 0.0,
        },
        {
            "id": "caixa_geladeira",
            "nome": "Torre para Geladeira",
            "desc": "Módulo torre com vão livre inferior para geladeira (sem base) e armário maleiro superior com portas e fundo.",
            "largura": 850, "altura": 2200, "profundidade": 600, "rodape": 0,
            "has_portas": True, "num_portas": 2, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": True, "has_rodape": False,
            "alt_nicho_geladeira_mm": 1800,
            "tipo_porta_superior": "duas_portas",
            "default_z": 0.0,
        },
    ],
    "Armários": [
                {
            "id": "roupeiro_correr",
            "nome": "Roupeiro Correr (2 ou 3 V?os)",
            "desc": "Arm?rio roupeiro base para portas de correr. Estrutura com maleiro superior cont?nuo, divis?rias verticais estruturais, 2 ou 3 v?os com cabideiros e prateleiras, e trilhos duplos de alum?nio.",
            "largura": 1800, "altura": 2200, "profundidade": 600, "rodape": 100,
            "has_portas": True, "num_portas": 2, "num_vaos": 2, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 5, "has_fundo": True, "has_rodape": True,
            "default_z": 0.0,
        },
        {
            "id": "roupeiro_correr_3p",
            "nome": "Roupeiro Correr (3 V?os)",
            "desc": "Arm?rio roupeiro de 3 v?os com maleiro cont?nuo, cabideiro longo, torre central de prateleiras, cabideiro duplo ? direita e 3 portas de correr sobrepostas.",
            "largura": 2400, "altura": 2200, "profundidade": 600, "rodape": 100,
            "has_portas": True, "num_portas": 3, "num_vaos": 3, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 7, "has_fundo": True, "has_rodape": True,
            "default_z": 0.0,
        },
        {
            "id": "roupeiro",
            "nome": "Armário Cabideiro",
            "desc": "Módulo roupeiro com maleiro superior, varão cabideiro e sapateira inferior. Portas e medidas totalmente configuráveis.",
            "largura": 900, "altura": 2200, "profundidade": 580, "rodape": 100,
            "has_portas": True, "num_portas": 2, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 2, "has_fundo": True, "has_rodape": True,
            "default_z": 0.0,
        },
        {
            "id": "armario_prateleiras",
            "nome": "Armário com Prateleiras",
            "desc": "Módulo vertical multiuso / sapateira / despenseiro com prateleiras internas. Número de portas (1, 2, 3...) e prateleiras totalmente configuráveis.",
            "largura": 800, "altura": 2200, "profundidade": 550, "rodape": 100,
            "has_portas": True, "num_portas": 2, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 4, "has_fundo": True, "has_rodape": True,
            "default_z": 0.0,
        },
        {
            "id": "armario_1p_prat",
            "nome": "Armário 1 Porta com Prateleiras",
            "desc": "Módulo estreito multiuso / despensa com 1 porta e 4 prateleiras internas.",
            "largura": 450, "altura": 2200, "profundidade": 550, "rodape": 100,
            "has_portas": True, "num_portas": 1, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 4, "has_fundo": True, "has_rodape": True,
            "default_z": 0.0,
        },
        {
            "id": "armario_1p_cabide",
            "nome": "Armário 1 Porta Cabideiro",
            "desc": "Módulo roupeiro estreito com 1 porta, maleiro superior e varão cabideiro.",
            "largura": 500, "altura": 2200, "profundidade": 580, "rodape": 100,
            "has_portas": True, "num_portas": 1, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 2, "has_fundo": True, "has_rodape": True,
            "default_z": 0.0,
        },
        {
            "id": "armario_2p_divisao",
            "nome": "Armário 2P com Divisória",
            "desc": "Armário com divisória vertical central, vão esquerdo com prateleiras e vão direito com cabideiro.",
            "largura": 1000, "altura": 2200, "profundidade": 580, "rodape": 100,
            "has_portas": True, "num_portas": 2, "fixed_portas": True, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 4, "has_fundo": True, "has_rodape": True,
            "default_z": 0.0,
        },
        {
            "id": "armario_3p_divisao",
            "nome": "Armário 3 Portas Misto",
            "desc": "Roupeiro de 3 portas com 2 divisórias verticais, maleiro amplo, gavetas internas e cabideiro.",
            "largura": 1500, "altura": 2200, "profundidade": 580, "rodape": 100,
            "has_portas": True, "num_portas": 3, "fixed_portas": True, "has_gavetas": True, "num_gavetas": 2,
            "has_prateleiras": True, "num_prateleiras": 4, "has_fundo": True, "has_rodape": True,
            "default_z": 0.0,
        },
        {
            "id": "armario_maleiro_tamponado",
            "nome": "Armário Maleiro com Tamponamento e Rodapé",
            "desc": "Armário com base de rodapé fechado estruturado, caixarias superiores com divisórias de maleiro (2 a 4 caixas isoladas ou única), tamponamento lateral e recuo de 70 mm para portas de correr.",
            "largura": 2000, "altura": 2400, "profundidade": 650, "rodape": 100,
            "num_caixas": 2, "modo_caixaria": "isoladas",
            "esp_tamponamento_mm": 18, "recuo_portas_correr_mm": 70, "alt_maleiro_mm": 400,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 2, "has_fundo": True, "has_rodape": True,
            "default_z": 0.0,
        },
    ],
    "Banheiro": [
        {
            "id": "gabinete_banheiro",
            "nome": "Gabinete Suspenso de Banheiro",
            "desc": "Gabinete moderno suspenso sem rodapé com 2 gavetões e recorte para cuba/sifão.",
            "largura": 800, "altura": 550, "profundidade": 450, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": True, "num_gavetas": 2,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": True, "has_rodape": False,
            "default_z": 0.25,
        },
    ],
    "Nichos & Estantes": [
        {
            "id": "nicho",
            "nome": "Nicho Aberto Decorativo",
            "desc": "Nicho ou estante aberta sem portas com moldura perimetral e divisórias internas configuráveis.",
            "largura": 600, "altura": 400, "profundidade": 300, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 1, "has_fundo": False, "has_rodape": False,
            "default_z": 1.4,
        },
    ],
    "Marmoraria & Pias": [
        {
            "id": "bancada_reta",
            "nome": "Bancada Reta de Pedra",
            "desc": "Tampo de pedra maciça com saia/testeira frontal e rodabanca traseiro para balcões e bancadas retas.",
            "largura": 1200, "altura": 40, "profundidade": 600, "rodape": 0,
            "esp_pedra": 20, "altura_saia": 40, "altura_frontao": 100,
            "has_cuba": False, "tipo_cuba": "sem_cuba",
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.82,
        },
        {
            "id": "bancada_pia",
            "nome": "Bancada de Pia com Cuba",
            "desc": "Bancada completa de pia com cuba de inox embutida, válvula/ralo, torneira, frontão e área molhada.",
            "largura": 1200, "altura": 40, "profundidade": 600, "rodape": 0,
            "esp_pedra": 20, "altura_saia": 40, "altura_frontao": 100,
            "has_cuba": True, "tipo_cuba": "inox_simples",
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.82,
        },
        {
            "id": "bancada_canto_l",
            "nome": "Bancada de Canto em L",
            "desc": "Bancada de pedra em L para cozinhas de canto, com frontões nas paredes e saia frontal contínua.",
            "largura": 1200, "altura": 40, "profundidade": 1200, "rodape": 0,
            "larg_asa": 600,
            "esp_pedra": 20, "altura_saia": 40, "altura_frontao": 100,
            "has_cuba": False, "tipo_cuba": "sem_cuba",
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.82,
        },
        {
            "id": "bancada_ilha",
            "nome": "Ilha / Bancada Gourmet",
            "desc": "Bancada gourmet ampla com saias nos 4 lados e balanço para banquetas.",
            "largura": 1600, "altura": 60, "profundidade": 900, "rodape": 0,
            "esp_pedra": 20, "altura_saia": 60, "altura_frontao": 0,
            "has_cuba": False, "tipo_cuba": "sem_cuba",
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.82,
        },
        {
            "id": "bancada_tampao_engrossado",
            "nome": "Tampão Engrossado de Pedra",
            "desc": "Tampão / painel engrossado de marmoraria em bloco único com largura, altura, espessura e tipo de pedra configuráveis.",
            "largura": 600, "altura": 860, "profundidade": 40, "rodape": 0,
            "esp_pedra": 20,
            "snap_parede": "nenhum",
            "has_cuba": False, "tipo_cuba": "sem_cuba",
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
    ],
    "Portas & Janelas": [
        # ── 6 PORTAS REAIS DO SKP ──
        {
            "id": "porta_giro",
            "nome": "Porta Giro",
            "desc": "Porta de giro branca com marco de 18cm, guarnições nos 2 lados, folha de 35mm e fechadura alavanca (70, 80 ou 90 cm).",
            "largura": 800, "altura": 2150, "profundidade": 180, "rodape": 0,
            "largura_options": [
                {"label": "70 cm", "largura": 700},
                {"label": "80 cm", "largura": 800},
                {"label": "90 cm", "largura": 900},
            ],
            "has_portas": True, "num_portas": 1, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "porta_aluminio",
            "nome": "Porta Alumínio",
            "desc": "Porta de alumínio anodizado claro 215cm com 3 dobradiças de inox mecânicas e fechadura completa com tambor e espelho (70, 80 ou 90 cm).",
            "largura": 800, "altura": 2150, "profundidade": 180, "rodape": 0,
            "largura_options": [
                {"label": "70 cm", "largura": 700},
                {"label": "80 cm", "largura": 800},
                {"label": "90 cm", "largura": 900},
            ],
            "has_portas": True, "num_portas": 1, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "porta_pivotante_vidro",
            "nome": "Porta Pivotante Vidro",
            "desc": "Porta de vidro temperado puro com pivô de piso e teto, mola hidráulica e puxador inox (80, 90 ou 100 cm).",
            "largura": 800, "altura": 2100, "profundidade": 95, "rodape": 0,
            "largura_options": [
                {"label": "80 cm", "largura": 800},
                {"label": "90 cm", "largura": 900},
                {"label": "100 cm", "largura": 1000},
            ],
            "has_portas": True, "num_portas": 1, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "porta_correr_vidro_170",
            "nome": "Porta Balcão Vidro 170x215 cm",
            "desc": "Porta de correr de vidro 2 folhas para sacada/varanda 170x215cm com trilhos de alumínio e fecho concha com trava vermelha.",
            "largura": 1700, "altura": 2145, "profundidade": 180, "rodape": 0,
            "has_portas": True, "num_portas": 2, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "porta_correr_vidro_4f_287",
            "nome": "Porta Vidro 4 Folhas",
            "desc": "Porta de vidro blindex 4 folhas de correr (2 fixas laterais e 2 móveis centrais) com trilho e fecho concha/fechadura.",
            "largura": 2870, "altura": 2100, "profundidade": 180, "rodape": 0,
            "largura_options": [
                {"label": "200 cm (4x50cm)", "largura": 2000},
                {"label": "240 cm (4x60cm)", "largura": 2400},
                {"label": "287 cm (Original Blindex)", "largura": 2870},
                {"label": "300 cm (4x75cm)", "largura": 3000},
                {"label": "320 cm (4x80cm)", "largura": 3200},
                {"label": "360 cm (4x90cm)", "largura": 3600},
                {"label": "400 cm (4x100cm)", "largura": 4000},
            ],
            "has_portas": True, "num_portas": 4, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },

        # ── 6 JANELAS REAIS DO SKP ──
        {
            "id": "janela_correr_2f_130",
            "nome": "Janela Correr 2F 130x120 cm",
            "desc": "Janela de correr 2 folhas 130x120cm em alumínio com vidro translúcido temperado e fechos laterais embutidos.",
            "largura": 1300, "altura": 1200, "profundidade": 180, "rodape": 0,
            "largura_options": [
                {"label": "100 cm", "largura": 1000},
                {"label": "120 cm", "largura": 1200},
                {"label": "130 cm", "largura": 1300},
                {"label": "150 cm", "largura": 1500},
            ],
            "peitoril_mm": 1000,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 1.00,
        },
        {
            "id": "janela_correr_4f_190",
            "nome": "Janela Correr 4F 190x120 cm",
            "desc": "Janela panorâmica 4 folhas 190x120cm (2 fixas laterais + 2 móveis centrais) com caixilho e vidro temperado.",
            "largura": 1900, "altura": 1200, "profundidade": 180, "rodape": 0,
            "largura_options": [
                {"label": "160 cm", "largura": 1600},
                {"label": "180 cm", "largura": 1800},
                {"label": "190 cm", "largura": 1900},
                {"label": "200 cm", "largura": 2000},
            ],
            "peitoril_mm": 1000,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 1.00,
        },
        {
            "id": "janela_vertical_50",
            "nome": "Janela Vertical 50x120 cm",
            "desc": "Janela vertical estreita 50x120cm com caixilho de alumínio branco, bandeira fixa e folha basculante inferior com braço.",
            "largura": 500, "altura": 1200, "profundidade": 180, "rodape": 0,
            "peitoril_mm": 900,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.90,
        },
        {
            "id": "janela_maximar_70",
            "nome": "Janela Maxim-Ar 70x60 cm",
            "desc": "Janela basculante projetante 70x60cm para banheiros com caixilho de alumínio, alavanca e vidro fosco.",
            "largura": 700, "altura": 600, "profundidade": 180, "rodape": 0,
            "peitoril_mm": 1600,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 1.60,
        },
        {
            "id": "janela_basculante_sup_170",
            "nome": "Janela Basculante Sup 170x60 cm",
            "desc": "Janela basculante superior 170x60cm de 3 módulos basculantes em linha com armação de alumínio e vidros.",
            "largura": 1700, "altura": 600, "profundidade": 180, "rodape": 0,
            "peitoril_mm": 1600,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 1.60,
        },
        {
            "id": "janela_basculante_inf_170",
            "nome": "Janela Basculante Inf 170x60 cm",
            "desc": "Janela basculante inferior 170x60cm com 3 folhas móveis articuladas projetantes e caixilho de sobrepor.",
            "largura": 1700, "altura": 600, "profundidade": 180, "rodape": 0,
            "peitoril_mm": 1000,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 1.00,
        },
    ],
    "Peças Avulsas / Componentes": [
        {
            "id": "peca_tamponamento",
            "nome": "Tamponamento Vertical",
            "desc": "Painel vertical de fechamento/acabamento externo (plano YZ, espessura em X) com configuração de bordas e materiais.",
            "largura": 18, "altura": 720, "profundidade": 570, "rodape": 0,
            "fita_caixa_modo": "4L",
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "peca_lateral_esquerda",
            "nome": "Lateral Esquerda",
            "desc": "Chapa vertical lateral esquerda canônica para caixaria (plano YZ, espessura em X).",
            "largura": 15, "altura": 720, "profundidade": 550, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "peca_lateral_direita",
            "nome": "Lateral Direita",
            "desc": "Chapa vertical lateral direita canônica para caixaria (plano YZ, espessura em X).",
            "largura": 15, "altura": 720, "profundidade": 550, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "peca_base",
            "nome": "Base Inferior",
            "desc": "Chapa horizontal canônica para base inferior de móvel (plano XY, espessura em Z).",
            "largura": 800, "altura": 15, "profundidade": 550, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "peca_tampo_superior",
            "nome": "Tampo Superior",
            "desc": "Chapa horizontal canônica para tampo superior fechado (plano XY, espessura em Z).",
            "largura": 800, "altura": 15, "profundidade": 550, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.705,
        },
        {
            "id": "peca_tampo_engrossado",
            "nome": "Tampo Engrossado",
            "desc": "Tampo de marcenaria com réguas inferiores de engrosso (camadas empilhadas) e fechamento inferior opcional.",
            "largura": 1200, "altura": 36, "profundidade": 600, "rodape": 0,
            "esp_chapa": 18, "qtd_engrosso": 1, "larg_engrosso": 70, "tipo_engrosso": "3_lados",
            "fechar_embaixo": False, "snap_parede": "auto",
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.82,
        },
        {
            "id": "peca_divisoria_vertical",
            "nome": "Divisória Vertical",
            "desc": "Divisória vertical intermediária interna para caixaria (plano YZ, espessura em X).",
            "largura": 15, "altura": 690, "profundidade": 530, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "cavilha_topo_superior": True, "cavilha_topo_inferior": True,
            "default_z": 0.015,
        },
        {
            "id": "peca_divisoria_horizontal",
            "nome": "Divisória Horizontal",
            "desc": "Divisória horizontal intermediária fixa de separação entre nichos e vãos (plano XY, espessura em Z).",
            "largura": 770, "altura": 15, "profundidade": 530, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.35,
        },
        {
            "id": "peca_prateleira",
            "nome": "Prateleira Interna",
            "desc": "Prateleira horizontal com recuo frontal e folgas de montagem (plano XY, espessura em Z).",
            "largura": 770, "altura": 15, "profundidade": 505, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.35,
        },
        {
            "id": "peca_prateleiras_avulsas",
            "nome": "Prateleiras Avulsas (Conjunto)",
            "desc": "Conjunto de prateleiras avulsas distribuídas uniformemente na altura total escolhida (padrão 2 intermediárias, com opção de primeira e última prateleira).",
            "largura": 800, "altura": 600, "profundidade": 300, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": True, "num_prateleiras": 2, "has_primeira": False, "has_ultima": False,
            "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "peca_porta_esquerda",
            "nome": "Porta de Abrir Esquerda",
            "desc": "Porta de abrir com dobradiças na esquerda e puxador na direita (plano XZ, espessura em Y).",
            "largura": 395, "altura": 715, "profundidade": 15, "rodape": 0,
            "has_portas": True, "num_portas": 1, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.003,
        },
        {
            "id": "peca_porta_direita",
            "nome": "Porta de Abrir Direita",
            "desc": "Porta de abrir com dobradiças na direita e puxador na esquerda (plano XZ, espessura em Y).",
            "largura": 395, "altura": 715, "profundidade": 15, "rodape": 0,
            "has_portas": True, "num_portas": 1, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.003,
        },
        {
            "id": "peca_porta_basculante",
            "nome": "Porta Basculante",
            "desc": "Porta basculante articulada no topo com abertura para cima (plano XZ, espessura em Y).",
            "largura": 795, "altura": 355, "profundidade": 15, "rodape": 0,
            "has_portas": True, "num_portas": 1, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.003,
        },
        {
            "id": "peca_frente_gaveta",
            "nome": "Frente de Gaveta",
            "desc": "Frente de gaveta externa aparente com fita 4L (plano XZ, espessura em Y).",
            "largura": 795, "altura": 160, "profundidade": 15, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": True, "num_gavetas": 1,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.003,
        },
        {
            "id": "peca_travessa_deitada",
            "nome": "Travessa Deitada (Horizontal)",
            "desc": "Régua/travessa de travamento deitada (largura em Y, espessura em Z).",
            "largura": 770, "altura": 15, "profundidade": 70, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.705,
        },
        {
            "id": "peca_travessa_em_pe",
            "nome": "Travessa em Pé (Vertical)",
            "desc": "Régua/travessa de travamento em pé frontal ou traseira (altura em Z, espessura em Y).",
            "largura": 770, "altura": 70, "profundidade": 15, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.65,
        },
        {
            "id": "peca_pilar_quina",
            "nome": "Pilar / Batente de Quina",
            "desc": "Régua vertical para junções de canto L ou travamento de coluna.",
            "largura": 50, "altura": 720, "profundidade": 15, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "peca_fundo",
            "nome": "Fundo Avulso",
            "desc": "Chapa de fundo vertical traseira (plano XZ, espessura ao longo de Y).",
            "largura": 800, "altura": 720, "profundidade": 6, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "peca_portas_correr",
            "nome": "Conjunto Portas de Correr (2 a 4 Portas)",
            "desc": "Conjunto avulso de portas de correr (2 a 4 folhas) com trilhos duplos de alumínio superior e inferior e cálculo automático de transpasse.",
            "largura": 1800, "altura": 2200, "profundidade": 65, "rodape": 0,
            "has_portas": True, "num_portas": 2, "transpasse_mm": 30,
            "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
                {
            "id": "rodape_fechado",
            "nome": "Rodapé Fechado (Base)",
            "desc": "Base de rodapé fechado independente com frente recuada, laterais e travessa de reforço.",
            "largura": 800, "altura": 100, "profundidade": 550, "rodape": 0,
            "has_portas": False, "num_portas": 0,
            "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "recuo_frontal_mm": 30, "larg_travessa_topo_mm": 70,
            "default_z": 0.0,
        },
        {
            "id": "peca_tamponamento_linha",
            "nome": "Tamponamento Contínuo de Linha (Envoltório)",
            "desc": "Envoltório contínuo (topo e/ou laterais engrossadas) para envolver um ou vários módulos adjacentes.",
            "largura": 1600, "altura": 720, "profundidade": 570, "rodape": 0,
            "has_portas": False, "num_portas": 0,
            "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "espessura_tampo_mm": 18, "espessura_lateral_mm": 18,
            "tipo_envoltorio": "u_completo", "sobra_frontal_mm": 20,
            "default_z": 0.0,
        },
    ],
    "Dormitório — Camas": [
        {
            "id": "cama_gaveteiros",
            "nome": "Cama Box Plataforma com Gaveteiros",
            "desc": "Cama plataforma com caixaria reforçada, divisória central longitudinal e gavetões laterais embutidos.",
            "largura": 1400, "altura": 400, "profundidade": 1950, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": True, "num_gavetas": 4,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "cama_bau",
            "nome": "Cama Box com Baú Articulado",
            "desc": "Cama box com baú fechado para armazenamento de malas e roupas de cama com estrado basculante superior.",
            "largura": 1400, "altura": 420, "profundidade": 1950, "rodape": 0,
            "has_portas": True, "num_portas": 1, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": True, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "cama_cabeceira",
            "nome": "Cama com Cabeceira Estendida e Mesinhas",
            "desc": "Cama plataforma integrada com grande painel de cabeceira de parede e 2 mesinhas suspensas laterais.",
            "largura": 2400, "altura": 1100, "profundidade": 2050, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "bicama",
            "nome": "Bicama Solteiro com Auxiliar Deslizante",
            "desc": "Cama solteiro com cabeceira, peseira, painel traseiro e cama auxiliar inferior com rodízios embutidos.",
            "largura": 950, "altura": 500, "profundidade": 1950, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": True, "num_gavetas": 1,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "beliche",
            "nome": "Beliche Planejado com Escada",
            "desc": "Beliche estruturado em MDF com leito inferior, leito superior com guarda-corpo de proteção e escada frontal.",
            "largura": 950, "altura": 1600, "profundidade": 2000, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
        {
            "id": "cama_colmeia",
            "nome": "Cama Colmeia Estrutural com Rodapé Recuado",
            "desc": "Cama plataforma estruturada com grade interna tipo colmeia em MDF, rodapé recuado e estrado superior bipartido.",
            "largura": 1400, "altura": 400, "profundidade": 1950, "rodape": 0,
            "has_portas": False, "num_portas": 0, "has_gavetas": False, "num_gavetas": 0,
            "has_prateleiras": False, "num_prateleiras": 0, "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
    ],
    "Racks": [
        {
            "id": "rack_nicho_gaveta",
            "nome": "Rack Nicho com Gaveta",
            "desc": "Módulo de rack estruturado tipo nicho com tampo e base passando por cima/baixo das laterais e gaveta com lado e largura configuráveis.",
            "largura": 1600, "altura": 500, "profundidade": 450, "rodape": 0,
            "has_portas": False, "num_portas": 0,
            "has_gavetas": True, "num_gavetas": 1,
            "largura_gaveteiro": 600,
            "lado_gaveteiro": "esquerda",
            "has_prateleiras": False, "num_prateleiras": 0,
            "has_fundo": False, "has_rodape": False,
            "default_z": 0.0,
        },
    ],
}


#: Categoria virtual onde os módulos salvos pelo usuário aparecem.
USER_MODULE_CATEGORY = "⭐ Meus Módulos"


def modulos_usuario() -> list[dict]:
    """Módulos salvos pelo usuário (lidos das preferências persistentes)."""
    from .preferences import TrazoMobPreferencesManager

    return TrazoMobPreferencesManager.get_instance().get_user_modules()


def iter_modulos_todos():
    """Itera o catálogo estático e os módulos do usuário, marcando a origem.

    Cada item recebe ``usuario`` (bool) e ``categoria`` (a categoria do
    catálogo, ou ``USER_MODULE_CATEGORY`` para os módulos pessoais). A galeria
    e o ribbon usam esses campos para exibir a seção "Meus Módulos".
    """
    for categoria, itens in MODULE_CATALOG.items():
        for item in itens:
            yield dict(item, usuario=False, categoria=categoria)
    for item in modulos_usuario():
        yield dict(item, usuario=True, categoria=USER_MODULE_CATEGORY)


def buscar_modulo(module_id: str, incluir_usuario: bool = True) -> dict | None:
    """Busca um módulo pelo ``id`` no catálogo estático e (opcional) no usuário."""
    for categoria, itens in MODULE_CATALOG.items():
        for item in itens:
            if item.get("id") == module_id:
                return dict(item, usuario=False, categoria=categoria)
    if incluir_usuario:
        for item in modulos_usuario():
            if item.get("id") == module_id:
                return dict(item, usuario=True, categoria=USER_MODULE_CATEGORY)
    return None


def _novo_id_usuario(nome: str, existentes: set[str]) -> str:
    """Gera um ``id`` único e legível (slug) para um módulo do usuário."""
    texto = unicodedata.normalize("NFKD", nome or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_") or "modulo"
    candidato = f"user_{slug}"
    indice = 2
    while candidato in existentes:
        candidato = f"user_{slug}_{indice}"
        indice += 1
    return candidato


def build_user_module(
    base: dict,
    params: dict,
    nome: str,
    existentes: set[str] | None = None,
) -> dict:
    """Monta um módulo pessoal a partir de um item do catálogo e dos parâmetros do formulário.

    ``base`` é o item de catálogo de origem (fornece flags como ``has_portas``),
    ``params`` são os parâmetros coletados da UI e ``nome`` é o nome escolhido
    pelo usuário. O ``id`` resultante é único dentro de ``existentes``.
    """
    novo = dict(base)
    nome_base = str(novo.get("nome") or novo.get("id") or "módulo")

    for chave in ("largura", "altura", "profundidade", "rodape"):
        if chave in params:
            try:
                novo[chave] = int(round(float(params[chave])))
            except (TypeError, ValueError):
                pass
    for chave in ("num_prateleiras", "num_portas", "num_gavetas"):
        if chave in params:
            try:
                novo[chave] = int(params[chave])
            except (TypeError, ValueError):
                pass
    for chave in ("material", "material_frentes", "puxador_tipo", "puxador_cor",
                  "puxador_pos", "tipo_fundo", "espessura", "espessura_frentes"):
        if chave in params and params[chave] is not None:
            novo[chave] = params[chave]

    novo["nome"] = (nome or "").strip() or nome_base
    novo["desc"] = f"Módulo pessoal salvo por você (base: {nome_base})."
    novo["id"] = _novo_id_usuario(novo["nome"], existentes or set())
    novo["usuario"] = True
    novo["categoria"] = USER_MODULE_CATEGORY
    return novo
