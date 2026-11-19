# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez, IngeTrazo contributors and Pair Programmer.
"""Construtor especializado para peças avulsas e tampos engrossados de marcenaria."""
from __future__ import annotations

from typing import Any, Optional, List, Tuple
from core.group import Group
from ..builders.mesh_utils import create_board_group
from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, PapelChapa, ModuloMaterialContext
from ..domain.materials_catalog import ALL_BOX_MATERIALS, MDF_MATERIALS


def _chapa(
    name: str,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    material: str,
    fita_c1: bool = False,
    fita_c2: bool = False,
    fita_l1: bool = False,
    fita_l2: bool = False,
    color: tuple[float, float, float] | None = None,
    papel: PapelChapa = PapelChapa.PECA_AVULSA,
    material_fita: str | None = None,
    operacoes: Optional[list[dict[str, Any]]] = None,
    **kwargs: Any,
) -> Group:
    """Cria uma peça avulsa pela API canônica de chapa (material explícito)."""
    spec = ChapaSpec.resolve(
        nome=name,
        papel=papel,
        ctx=ModuloMaterialContext(material_caixa=material),
        material_override=material,
        fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
        material_fita_override=material_fita,
        operacoes=operacoes,
    )
    if color is not None:
        kwargs["color"] = color
    return build_chapa(spec, origin, size, **kwargs)


def _chapa_frente(
    name: str,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    ctx: ModuloMaterialContext,
    papel: PapelChapa = PapelChapa.PORTA,
    **kwargs: Any,
) -> Group:
    """Cria porta/frente avulsa herdando material e fita de frentes do contexto."""
    spec = ChapaSpec.resolve(nome=name, papel=papel, ctx=ctx)
    return build_chapa(spec, origin, size, **kwargs)


class CustomPartsBuilder:
    """Construtor desacoplado para tampos engrossados e peças avulsas individuais."""

    @staticmethod
    def get_material_color(material: str) -> tuple[float, float, float]:
        from ..domain.materials_catalog import get_material_color
        return get_material_color(material)

    @staticmethod
    def build_lateral_esquerda(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_lateral_esquerda(*args, **kwargs)

    @staticmethod
    def build_lateral_direita(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_lateral_direita(*args, **kwargs)

    @staticmethod
    def build_base_inferior(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_base_inferior(*args, **kwargs)

    @staticmethod
    def build_tampo_superior(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_tampo_superior(*args, **kwargs)

    @staticmethod
    def build_prateleira(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_prateleira(*args, **kwargs)

    @staticmethod
    def build_divisoria(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_divisoria(*args, **kwargs)

    @staticmethod
    def build_divisoria_horizontal(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_divisoria_horizontal(*args, **kwargs)

    @staticmethod
    def build_travessa_peca(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_travessa_peca(*args, **kwargs)

    @staticmethod
    def build_fundo(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_fundo(*args, **kwargs)

    @staticmethod
    def build_porta_esquerda(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_porta_esquerda(*args, **kwargs)

    @staticmethod
    def build_porta_direita(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_porta_direita(*args, **kwargs)

    @staticmethod
    def build_porta_basculante(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_porta_basculante(*args, **kwargs)

    @staticmethod
    def build_frente_gaveta(*args, **kwargs):
        from ..builders.cabinet import CabinetBuilder
        return CabinetBuilder.build_frente_gaveta(*args, **kwargs)

    @classmethod
    def build_peca_avulsa(
        cls,
        subtipo: str,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_mm: float = 15.0,
        material: str = "MDF Branco TX 15mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        material_fita: str | None = None,
        puxador_tipo: str = "alca",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        cavilha_topo_superior: bool = True,
        cavilha_topo_inferior: bool = True,
        afastamento_cavilha_frontal_mm: float = 50.0,
        afastamento_cavilha_traseiro_mm: float = 50.0,
        fita_borda_modo: str = "4L",
        lado_abertura_porta: str = "esquerda",
    ) -> list[Group]:
        """Gera uma peça avulsa individual (lateral, base, travessa, fundo, porta, etc.)."""
        ox, oy, oz = offset
        L = largura_mm / 1000.0
        A = altura_mm / 1000.0
        P = prof_mm / 1000.0
        E = esp_mm / 1000.0

        cor = cls.get_material_color(material)
        cor_fita = cls.get_material_color(material_fita) if material_fita else None

        groups: list[Group] = []

        if subtipo in ("tamponamento", "tamponamento_vertical"):
            # Tamponamento vertical externo canonico em YZ (espessura ao longo de X = E, profundidade = P, altura = A)
            modo_f = (fita_borda_modo or "4L").lower()
            fc1 = modo_f in ("frontal_1l", "2l", "4l")
            fc2 = modo_f in ("2l", "4l")
            fl1 = modo_f in ("4l",)
            fl2 = modo_f in ("4l",)
            groups.append(cls.build_lateral_esquerda(
                name="Tamponamento Vertical Avulso",
                origin=(ox, oy, oz),
                size=(L, P, A),
                material=material,
                fita_c1=fc1, fita_c2=fc2, fita_l1=fl1, fita_l2=fl2,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo in ("lateral", "lateral_esquerda"):
            # Lateral vertical esquerda canônica em YZ (espessura ao longo de X = E, profundidade = P, altura = A)
            groups.append(cls.build_lateral_esquerda(
                name="Lateral Esquerda Avulsa",
                origin=(ox, oy, oz),
                size=(E, P, A),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "lateral_direita":
            # Lateral vertical direita canônica em YZ
            groups.append(cls.build_lateral_direita(
                name="Lateral Direita Avulsa",
                origin=(ox, oy, oz),
                size=(E, P, A),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "base":
            # Chapa horizontal canônica: Base Inferior (largura = L, profundidade = P, espessura ao longo de Z = E)
            groups.append(cls.build_base_inferior(
                name="Base Avulsa",
                origin=(ox, oy, oz),
                size=(L, P, E),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "tampo_superior":
            # Chapa horizontal canônica: Tampo Superior
            groups.append(cls.build_tampo_superior(
                name="Tampo Superior Avulso",
                origin=(ox, oy, oz),
                size=(L, P, E),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "prateleira":
            # Prateleira canônica horizontal
            groups.append(cls.build_prateleira(
                name="Prateleira Avulsa",
                origin=(ox, oy, oz),
                size=(L, P, E),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo in ("divisoria", "divisoria_vertical"):
            # Divisória canônica vertical (espessura ao longo de X = E, profundidade = P, altura = A)
            groups.append(cls.build_divisoria(
                name="Divisória Vertical Avulsa",
                origin=(ox, oy, oz),
                size=(E, P, A),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                cavilha_topo_superior=cavilha_topo_superior,
                cavilha_topo_inferior=cavilha_topo_inferior,
                afastamento_cavilha_frontal_mm=afastamento_cavilha_frontal_mm,
                afastamento_cavilha_traseiro_mm=afastamento_cavilha_traseiro_mm,
            ))
        elif subtipo == "divisoria_horizontal":
            # Divisória canônica horizontal (largura = L, profundidade = P, espessura ao longo de Z = E)
            groups.append(cls.build_divisoria_horizontal(
                name="Divisória Horizontal Avulsa",
                origin=(ox, oy, oz),
                size=(L, P, E),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo in ("travessa_deitada", "travessa"):
            # Régua deitada horizontal canônica (largura = L, profundidade = P, espessura ao longo de Z = E)
            groups.append(cls.build_travessa_peca(
                name="Travessa Deitada Avulsa",
                origin=(ox, oy, oz),
                size=(L, P, E),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "travessa_em_pe":
            # Régua em pé vertical canônica (largura = L, espessura ao longo de Y = E, altura = A)
            groups.append(cls.build_travessa_peca(
                name="Travessa em Pe Avulsa",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "pilar_quina":
            # Régua de coluna vertical (largura = L, espessura ao longo de Y = E, altura = A)
            groups.append(cls.build_travessa_peca(
                name="Pilar de Quina Avulso",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
            ))
        elif subtipo == "fundo":
            # Fundo canônico vertical traseiro (largura = L, espessura ao longo de Y = E ou fundo, altura = A)
            esp_f = E if E <= 0.010 else 0.006
            groups.append(cls.build_fundo(
                name="Fundo Avulso",
                origin=(ox, oy, oz),
                size=(L, esp_f, A),
                material=material,
                color=cor,
            ))
        elif subtipo == "porta":
            lado_str = str(lado_abertura_porta or "esquerda").strip().lower()
            is_dir = lado_str.startswith(("dir", "right"))
            if is_dir:
                groups.append(cls.build_porta_direita(
                    name="Porta Direita Avulsa",
                    origin=(ox, oy, oz),
                    size=(L, E, A),
                    material=material,
                    color=cor,
                    material_fita=material_fita, cor_fita=cor_fita,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    is_upper=False,
                ))
            else:
                groups.append(cls.build_porta_esquerda(
                    name="Porta Esquerda Avulsa",
                    origin=(ox, oy, oz),
                    size=(L, E, A),
                    material=material,
                    color=cor,
                    material_fita=material_fita, cor_fita=cor_fita,
                    puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                    desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                    is_upper=False,
                ))
        elif subtipo == "porta_esquerda":
            # Porta de abrir canônica esquerda
            groups.append(cls.build_porta_esquerda(
                name="Porta Esquerda Avulsa",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                color=cor,
                material_fita=material_fita, cor_fita=cor_fita,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
            ))
        elif subtipo == "porta_direita":
            # Porta de abrir canônica direita
            groups.append(cls.build_porta_direita(
                name="Porta Direita Avulsa",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                color=cor,
                material_fita=material_fita, cor_fita=cor_fita,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=False,
            ))
        elif subtipo == "porta_basculante":
            # Porta basculante canônica (abertura superior, puxador na base)
            groups.append(cls.build_porta_basculante(
                name="Porta Basculante Avulsa",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                color=cor,
                material_fita=material_fita, cor_fita=cor_fita,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                is_upper=True,
            ))
        elif subtipo == "frente_gaveta":
            # Frente de gaveta canônica externa
            groups.append(cls.build_frente_gaveta(
                name="Frente Gaveta Avulsa",
                origin=(ox, oy, oz),
                size=(L, E, A),
                material=material,
                color=cor,
                material_fita=material_fita, cor_fita=cor_fita,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=puxador_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
            ))

        else:
            groups.append(_chapa(
                f"Peca {subtipo}",
                (ox, oy, oz),
                (L, P, A),
                material, fita_c1=True, color=cor,
            ))

        return groups

    @classmethod
    def build_rodape_fechado(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_mm: float = 15.0,
        larg_travessa_topo_mm: float = 70.0,
        recuo_frontal_mm: float = 30.0,
        material: str = "MDF Branco TX 15mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        material_fita: str | None = None,
    ) -> List[Group]:
        """Gera uma base de rodapé fechado estruturada para marcenaria.

        Composição:
        1. Frente recuada (plano XZ, espessura em Y, em pé).
        2. Laterais esquerda e direita (plano YZ, espessura em X, em pé).
        3. Travessa traseira em pé (plano XZ, espessura em Y, fecha o fundo).
        4. Travessas horizontais de fixação/topo (plano XY, espessura em Z, deitadas):
           - Travessa frontal deitada no topo (logo atrás da frente).
           - Travessa traseira deitada no topo (logo à frente do fechamento traseiro).
        5. Travessas intermediárias de reforço vertical/apoio quando a largura for grande (L > 600mm).
        """
        ox, oy, oz = offset
        L = largura_mm / 1000.0
        A = altura_mm / 1000.0
        P = prof_mm / 1000.0
        E = esp_mm / 1000.0

        recuo = max(0.0, recuo_frontal_mm / 1000.0)
        larg_trav = min(max(0.0, larg_travessa_topo_mm / 1000.0), max(0.0, P - recuo))
        prof_lateral = max(0.0, P - recuo - E)

        cor = cls.get_material_color(material)
        cor_fita = cls.get_material_color(material_fita) if material_fita else None

        groups: List[Group] = []

        # 1. Frente recuada (plano XZ, espessura em Y)
        if L > 0 and A > 0 and E > 0:
            groups.append(_chapa(
                "Rodapé Fechado - Frente",
                (ox, oy + recuo, oz),
                (L, E, A),
                material,
                fita_c1=True, fita_c2=False, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.RODAPE,
            ))

        # 2. Travessa do fundo em pé (plano XZ, espessura em Y, na traseira total oy + P - E)
        if L > 0 and A > 0 and E > 0 and P > (recuo + 2 * E):
            larg_fundo_util = max(0.0, L - 2 * E) if L > 2 * E else L
            x_fundo = (ox + E) if L > 2 * E else ox
            groups.append(_chapa(
                "Rodapé Fechado - Travessa Fundo em Pé",
                (x_fundo, oy + P - E, oz),
                (larg_fundo_util, E, A),
                material,
                fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=False,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.TRAVESSA,
            ))

        # 3. Laterais de fechamento (plano YZ, espessura em X)
        # Partem de trás da frente recuada (oy + recuo + E) até a traseira total (oy + P)
        prof_lateral = max(0.0, P - recuo - E)
        if prof_lateral > 0 and A > 0 and E > 0:
            groups.append(_chapa(
                "Rodapé Fechado - Lateral Esquerda",
                (ox, oy + recuo + E, oz),
                (E, prof_lateral, A),
                material,
                fita_c1=True, fita_c2=True, fita_l1=False, fita_l2=False,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.LATERAL_ESQUERDA,
            ))
            groups.append(_chapa(
                "Rodapé Fechado - Lateral Direita",
                (ox + L - E, oy + recuo + E, oz),
                (E, prof_lateral, A),
                material,
                fita_c1=True, fita_c2=True, fita_l1=False, fita_l2=False,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.LATERAL_DIREITA,
            ))

        # 4. Travessa deitada frontal no topo (plano XY, espessura em Z)
        # Posicionada no topo do rodapé (oz + A - E), logo atrás da frente recuada
        largura_util_trav = max(0.0, L - 2 * E) if L > 2 * E else L
        x_trav = (ox + E) if L > 2 * E else ox

        if larg_trav > 0 and L > 0 and E > 0:
            groups.append(_chapa(
                "Rodapé Fechado - Travessa Superior Frontal",
                (x_trav, oy + recuo + E, oz + A - E),
                (largura_util_trav, larg_trav, E),
                material,
                fita_c1=True, fita_c2=False, fita_l1=True, fita_l2=False,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.TRAVESSA,
            ))

        # 5. Travessa deitada do fundo no topo (plano XY, espessura em Z)
        # Posicionada no topo do rodapé (oz + A - E), encostada na traseira
        if larg_trav > 0 and L > 0 and E > 0 and P > (recuo + larg_trav + E):
            y_trav_fundo = max(oy + recuo + E + larg_trav, oy + P - E - larg_trav)
            groups.append(_chapa(
                "Rodapé Fechado - Travessa Deitada do Fundo",
                (x_trav, y_trav_fundo, oz + A - E),
                (largura_util_trav, larg_trav, E),
                material,
                fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=False,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.TRAVESSA,
            ))

        # 6. Travessas de reforço internas (nervuras/apoios intermediários no sentido Y - profundidade)
        # Para vãos largos (L >= 600 mm), distribui travessas de reforço intermediárias.
        # A altura da intermediária fica logo abaixo das travessas deitadas do topo (A - E),
        # servindo de apoio contínuo inferior para as travessas deitadas sem sobrepô-las.
        prof_reforco = max(0.0, P - recuo - 2 * E)
        alt_reforco = max(0.0, A - E) if (larg_trav > 0) else A
        if L > 0.6 and prof_reforco > 0 and alt_reforco > 0 and E > 0:
            num_espacos = max(2, int(round(L / 0.5)))
            passo_x = (L - 2 * E) / num_espacos
            for i in range(1, num_espacos):
                rx = (ox + E) + i * passo_x - (E / 2.0)
                groups.append(_chapa(
                    f"Rodapé Fechado - Reforço Central {i}",
                    (rx, oy + recuo + E, oz),
                    (E, prof_reforco, alt_reforco),
                    material,
                    fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=False,
                    color=cor, material_fita=material_fita, cor_fita=cor_fita,
                    papel=PapelChapa.TRAVESSA,
                ))

        return groups

    @classmethod
    def build_tampo_engrossado(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        esp_chapa_mm: float = 18.0,
        larg_engrosso_mm: float = 70.0,
        tipo_engrosso: str = "3_lados",
        qtd_engrosso: int = 1,
        fechar_embaixo: bool = False,
        snap_parede: str = "auto",
        material: str = "MDF Branco TX",
        material_fita: Optional[str] = None,
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> List[Group]:
        """Gera um tampo engrossado de marcenaria com réguas perimetrais na espessura real da chapa.

        ``snap_parede`` é metadado de encaixe (não altera a geometria): define
        qual face adere à parede no arraste magnético e permite desligar o snap.
        """
        ox, oy, oz = offset
        L = largura_mm / 1000.0
        P = prof_mm / 1000.0

        # Espessura nominal da madeira
        e_chapa = (esp_chapa_mm if esp_chapa_mm > 0 else 18.0) / 1000.0

        # Determina a quantidade de camadas de réguas de engrosso no meio:
        # Se qtd_engrosso for passado explicitamente (> 0), usa-o diretamente.
        n_camadas = int(qtd_engrosso) if qtd_engrosso and int(qtd_engrosso) >= 1 else 1

        w_regua = (larg_engrosso_mm if larg_engrosso_mm > 0 else 70.0) / 1000.0
        w_regua = min(w_regua, min(L, P) * 0.45)

        cor = cls.get_material_color(material)
        cor_fita = cls.get_material_color(material_fita) if material_fita else None

        groups: List[Group] = []

        # ── ESTRUTURA VERTICAL DE BAIXO PARA CIMA: ──────────────────
        # Nível inferior do módulo completo começa em oz:
        # 1. Se 'fechar_embaixo' estiver ativo:
        #    - A chapa de fechamento inferior fica na base: z = oz até oz + e_chapa.
        #    - As réguas de engrosso ficam sobre ela: z = oz + e_chapa + (idx * e_chapa).
        #    - A chapa superior fica no topo de tudo: z = oz + e_chapa + (n_camadas * e_chapa).
        # 2. Se NÃO houver fechamento inferior:
        #    - As réguas de engrosso ficam na base: z = oz + (idx * e_chapa).
        #    - A chapa superior fica no topo: z = oz + (n_camadas * e_chapa).

        z_base_reguas = oz + (e_chapa if fechar_embaixo else 0.0)
        z_tampo_topo = z_base_reguas + n_camadas * e_chapa

        # 1. Chapa Superior Principal (Fica no topo em z_tampo_topo)
        grp_tampo = _chapa(
            "Tampo Superior",
            (ox, oy, z_tampo_topo),
            (L, P, e_chapa),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
            color=cor, material_fita=material_fita, cor_fita=cor_fita,
            papel=PapelChapa.TAMPO_SUPERIOR,
        )
        groups.append(grp_tampo)

        # 2. Réguas Intermediárias de Engrosso em Fatias/Camadas Discretas
        # Cada camada tem espessura exatamente igual a 'e_chapa' da madeira
        for camada_idx in range(n_camadas):
            z_layer = z_base_reguas + camada_idx * e_chapa
            sufixo_camada = f" Camada {camada_idx + 1}" if n_camadas > 1 else ""

            # Régua Frontal (ao longo de X)
            grp_regua_front = _chapa(
                f"Régua Engrosso Frontal{sufixo_camada}",
                (ox, oy, z_layer),
                (L, w_regua, e_chapa),
                material, fita_c1=True, fita_c2=False, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.TRAVESSA,
            )
            groups.append(grp_regua_front)

            # Réguas Laterais (ao longo de Y)
            if tipo_engrosso in ("3_lados", "4_lados", "laterais"):
                y_lat_inicio = oy + w_regua
                comp_lat = P - w_regua - (w_regua if tipo_engrosso == "4_lados" else 0.0)
                if comp_lat > 0.02:
                    # Lateral Esquerda
                    grp_lat_esq = _chapa(
                        f"Régua Engrosso Lateral Esquerda{sufixo_camada}",
                        (ox, y_lat_inicio, z_layer),
                        (w_regua, comp_lat, e_chapa),
                        material, fita_c1=False, fita_c2=False, fita_l1=True, fita_l2=False,
                        color=cor, material_fita=material_fita, cor_fita=cor_fita,
                        papel=PapelChapa.TRAVESSA,
                    )
                    groups.append(grp_lat_esq)

                    # Lateral Direita
                    grp_lat_dir = _chapa(
                        f"Régua Engrosso Lateral Direita{sufixo_camada}",
                        (ox + L - w_regua, y_lat_inicio, z_layer),
                        (w_regua, comp_lat, e_chapa),
                        material, fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=True,
                        color=cor, material_fita=material_fita, cor_fita=cor_fita,
                        papel=PapelChapa.TRAVESSA,
                    )
                    groups.append(grp_lat_dir)

            # Régua Traseira (ao longo de X, se 4 lados)
            if tipo_engrosso == "4_lados":
                grp_regua_tras = _chapa(
                    f"Régua Engrosso Traseira{sufixo_camada}",
                    (ox, oy + P - w_regua, z_layer),
                    (L, w_regua, e_chapa),
                    material, fita_c1=False, fita_c2=True, fita_l1=True, fita_l2=True,
                    color=cor, material_fita=material_fita, cor_fita=cor_fita,
                    papel=PapelChapa.TRAVESSA,
                )
                groups.append(grp_regua_tras)

            # Travessa Central de Apoio (se vão livre L > 900 mm)
            if L > 0.90:
                y_centro_inicio = oy + w_regua
                comp_centro = P - w_regua - (w_regua if tipo_engrosso == "4_lados" else 0.0)
                if comp_centro > 0.05:
                    x_centro = ox + (L - w_regua) * 0.5
                    grp_centro = _chapa(
                        f"Régua Reforço Central{sufixo_camada}",
                        (x_centro, y_centro_inicio, z_layer),
                        (w_regua, comp_centro, e_chapa),
                        material, fita_c1=False, fita_c2=False, fita_l1=False, fita_l2=False,
                        color=cor, material_fita=material_fita, cor_fita=cor_fita,
                        papel=PapelChapa.TRAVESSA,
                    )
                    groups.append(grp_centro)

        # 3. Chapa de Fechamento Inferior (Tampo Sanduíche / Tamburato)
        if fechar_embaixo:
            # Chapa inferior inteiriça na base absoluta (oz)
            grp_fechamento = _chapa(
                "Chapa Fechamento Inferior",
                (ox, oy, oz),
                (L, P, e_chapa),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True,
                color=cor, material_fita=material_fita, cor_fita=cor_fita,
                papel=PapelChapa.BASE_INFERIOR,
            )
            groups.append(grp_fechamento)

        return groups

    @classmethod
    def build_portas_correr_avulsas(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float = 65.0,
        num_portas: int = 2,
        esp_mm: float = 15.0,
        transpasse_mm: float = 30.0,
        material: str = "MDF Branco TX 15mm",
        material_fita: Optional[str] = None,
        offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        puxador_tipo: str = "perfil",
        puxador_cor: str = "preto",
        puxador_pos: str = "padrao",
        desconto_perfil_mm: float = 35.0,
        perfil_modelo: str = "gola",
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> List[Group]:
        """Gera um conjunto avulso de portas de correr (2 a 4 portas) com trilhos duplos de alumínio."""
        from PySide6.QtGui import QVector3D
        if mat_ctx is None:
            mat_ctx = ModuloMaterialContext(
                material_caixa=material,
                material_frentes=material,
            )

        ox, oy, oz = offset
        L = max(0.40, float(largura_mm) / 1000.0)
        A = max(0.30, float(altura_mm) / 1000.0)
        P = max(0.045, float(prof_mm) / 1000.0)
        E_frente = max(0.006, float(esp_mm) / 1000.0)
        n_portas = max(2, min(4, int(num_portas)))
        transpasse = max(0.0, float(transpasse_mm) / 1000.0)

        cor_frente = cls.get_material_color(material)
        cor_fita = cls.get_material_color(material_fita) if material_fita else None

        groups: List[Group] = []

        # 1. Trilhos Duplos de Alumínio (Inferior e Superior)
        prof_trilho = min(0.045, P)
        groups.append(create_board_group(
            "Portas Correr - Trilho Inferior",
            (ox, oy, oz),
            (L, prof_trilho, 0.008),
            "Alumínio Anodizado", color=(0.75, 0.77, 0.80),
        ))
        groups.append(create_board_group(
            "Portas Correr - Trilho Superior",
            (ox, oy, oz + A - 0.035),
            (L, prof_trilho, 0.035),
            "Alumínio Anodizado", color=(0.75, 0.77, 0.80),
        ))

        # 2. Cálculo de corte das folhas (2, 3 ou 4 portas)
        # Em portas de correr, quando puxador_pos é "padrao"/"auto"/"superior" e puxador_tipo é "perfil" ou "alca",
        # o puxador/perfil de porta de correr fica na lateral/extensão vertical da folha.
        eff_pux_pos = puxador_pos
        if str(eff_pux_pos or "padrao").lower() in ("padrao", "auto", "superior", "topo"):
            eff_pux_pos = "extensao"
        # Desconto vertical padrão de 15mm para sistema de correr/roldanas
        alt_porta = max(0.10, A - 0.015)
        z_porta = oz + 0.008
        # No sistema de coordenadas do TrazoMob, a frente do móvel aponta para -Y e o fundo para +Y.
        # Logo, o trilho externo (frontal) fica em menor Y e o trilho interno (traseiro) em maior Y.
        y_trilho_frontal = oy + 0.004
        y_trilho_traseiro = oy + 0.004 + E_frente + 0.012

        if n_portas == 2:
            # 2 Portas: 1 transpasse central (30mm)
            larg_porta = (L + transpasse) / 2.0
            slide_dist = max(0.05, larg_porta - transpasse)

            # Folha 1: Esquerda (Trilho Traseiro/Interno) -> corre para a direita (+X)
            # Puxador na borda esquerda externa (door_side="right" coloca o puxador em ox)
            p1 = _chapa_frente(
                "Porta Correr 1 - Esq (Interna)",
                (ox, y_trilho_traseiro, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="right",
            )
            if getattr(p1, "ext", None) is None:
                p1.ext = {}
            p1.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
            p1.ext["slide_distance"] = float(slide_dist)
            groups.append(p1)

            # Folha 2: Direita (Trilho Frontal/Externo) -> corre para a esquerda (-X)
            # Puxador na borda direita externa (door_side="left" coloca o puxador em ox + larg_porta)
            x_p2 = ox + L - larg_porta
            p2 = _chapa_frente(
                "Porta Correr 2 - Dir (Externa)",
                (x_p2, y_trilho_frontal, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="left",
            )
            if getattr(p2, "ext", None) is None:
                p2.ext = {}
            p2.ext["slide_axis"] = QVector3D(-1.0, 0.0, 0.0)
            p2.ext["slide_distance"] = float(slide_dist)
            groups.append(p2)

        elif n_portas == 3:
            # 3 Portas: 2 transpasses (30mm entre F1-F2 e 30mm entre F2-F3)
            larg_porta = (L + (2.0 * transpasse)) / 3.0
            slide_dist = max(0.05, larg_porta - transpasse)

            # Folha 1: Esquerda (Trilho Traseiro/Interno) -> corre para a direita (+X), puxador na esquerda
            p1 = _chapa_frente(
                "Porta Correr 1 - Esq (Interna)",
                (ox, y_trilho_traseiro, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="right",
            )
            if getattr(p1, "ext", None) is None:
                p1.ext = {}
            p1.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
            p1.ext["slide_distance"] = float(slide_dist)
            groups.append(p1)

            # Folha 2: Centro (Trilho Frontal/Externo) -> corre para os dois lados, puxador nos dois lados ("both")
            x_p2 = ox + (L * 0.5) - (larg_porta * 0.5)
            p2 = _chapa_frente(
                "Porta Correr 2 - Centro (Externa)",
                (x_p2, y_trilho_frontal, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="both",
            )
            if getattr(p2, "ext", None) is None:
                p2.ext = {}
            p2.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
            p2.ext["slide_distance"] = float(slide_dist)
            groups.append(p2)

            # Folha 3: Direita (Trilho Traseiro/Interno) -> corre para a esquerda (-X), puxador na direita
            x_p3 = ox + L - larg_porta
            p3 = _chapa_frente(
                "Porta Correr 3 - Dir (Interna)",
                (x_p3, y_trilho_traseiro, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="left",
            )
            if getattr(p3, "ext", None) is None:
                p3.ext = {}
            p3.ext["slide_axis"] = QVector3D(-1.0, 0.0, 0.0)
            p3.ext["slide_distance"] = float(slide_dist)
            groups.append(p3)

        else:
            # 4 Portas: sistema simétrico (2 laterais internas no trilho traseiro + 2 centrais externas no trilho frontal)
            larg_porta = (L + (2.0 * transpasse)) / 4.0
            slide_dist = max(0.05, larg_porta - transpasse)

            # Folha 1: Canto Esquerdo (Traseira/Interna) -> corre para a direita (+X), puxador na esquerda
            x_p1 = ox
            p1 = _chapa_frente(
                "Porta Correr 1 - Esq (Interna)",
                (x_p1, y_trilho_traseiro, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="right",
            )
            if getattr(p1, "ext", None) is None:
                p1.ext = {}
            p1.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
            p1.ext["slide_distance"] = float(slide_dist)
            groups.append(p1)

            # Folha 2: Centro-Esquerda (Frontal/Externa) -> corre para a esquerda (-X), puxador no encontro central (direita)
            x_p2 = ox + (L * 0.5) - larg_porta
            p2 = _chapa_frente(
                "Porta Correr 2 - Centro Esq (Externa)",
                (x_p2, y_trilho_frontal, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="left",
            )
            if getattr(p2, "ext", None) is None:
                p2.ext = {}
            p2.ext["slide_axis"] = QVector3D(-1.0, 0.0, 0.0)
            p2.ext["slide_distance"] = float(slide_dist)
            groups.append(p2)

            # Folha 3: Centro-Direita (Frontal/Externa) -> corre para a direita (+X), puxador no encontro central (esquerda)
            x_p3 = ox + (L * 0.5)
            p3 = _chapa_frente(
                "Porta Correr 3 - Centro Dir (Externa)",
                (x_p3, y_trilho_frontal, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="right",
            )
            if getattr(p3, "ext", None) is None:
                p3.ext = {}
            p3.ext["slide_axis"] = QVector3D(1.0, 0.0, 0.0)
            p3.ext["slide_distance"] = float(slide_dist)
            groups.append(p3)

            # Folha 4: Canto Direito (Traseira/Interna) -> corre para a esquerda (-X), puxador na direita
            x_p4 = ox + L - larg_porta
            p4 = _chapa_frente(
                "Porta Correr 4 - Dir (Interna)",
                (x_p4, y_trilho_traseiro, z_porta),
                (larg_porta, E_frente, alt_porta),
                mat_ctx, color=cor_frente,
                puxador_tipo=puxador_tipo, puxador_cor=puxador_cor, puxador_pos=eff_pux_pos,
                desconto_perfil_mm=desconto_perfil_mm, perfil_modelo=perfil_modelo,
                door_side="left",
            )
            if getattr(p4, "ext", None) is None:
                p4.ext = {}
            p4.ext["slide_axis"] = QVector3D(-1.0, 0.0, 0.0)
            p4.ext["slide_distance"] = float(slide_dist)
            groups.append(p4)

        return groups

    @classmethod
    def build_prateleiras_avulsas(
        cls,
        largura_mm: float,
        altura_mm: float,
        prof_mm: float,
        num_prateleiras: int = 2,
        esp_mm: float = 15.0,
        has_primeira: bool = False,
        has_ultima: bool = False,
        material: str = "MDF Branco TX 15mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        material_fita: str | None = None,
        cor_fita: tuple[float, float, float] | None = None,
        fita_c1: bool = True,
        fita_c2: bool = True,
        fita_l1: bool = True,
        fita_l2: bool = True,
        mat_ctx: ModuloMaterialContext | None = None,
    ) -> list[Group]:
        """Gera um conjunto de prateleiras avulsas distribuídas no espaço total especificado.

        O parâmetro ``num_prateleiras`` define o número de prateleiras intermediárias
        que dividem o vão em partes iguais.
        ``has_primeira``: se True, adiciona uma prateleira na base inferior do vão (oz).
        ``has_ultima``: se True, adiciona uma prateleira no topo superior do vão (oz + A - E).
        Exemplo: 2 intermediárias + has_primeira + has_ultima = 4 prateleiras no total.
        """
        ox, oy, oz = offset
        L = float(largura_mm) / 1000.0
        A = float(altura_mm) / 1000.0
        P = float(prof_mm) / 1000.0
        E = float(esp_mm) / 1000.0
        cor = cls.get_material_color(material)
        mat_ctx = mat_ctx or ModuloMaterialContext(
            material_caixa=material,
            material_fita_caixa=material_fita,
        )

        n_interm = max(0, int(num_prateleiras))
        n_espacos = n_interm + 1

        # Altura útil livre para distribuição descontando as espessuras
        z_pos: list[tuple[str, float]] = []

        # 1. Primeira prateleira (Base do espaço útil)
        if has_primeira:
            z_pos.append(("Base", oz))

        # 2. Prateleiras intermediárias: dividem a altura A uniformemente
        if n_interm > 0:
            passo = max(0.0, (A - E) / n_espacos) if A >= E else 0.0
            for i in range(1, n_interm + 1):
                z_interm = oz + (i * passo)
                z_pos.append((f"Intermediária {i}" if n_interm > 1 else "Intermediária", z_interm))

        # 3. Última prateleira (Topo do espaço útil)
        if has_ultima:
            z_topo = oz + max(0.0, A - E)
            z_pos.append(("Topo", z_topo))

        # Caso nenhuma seja selecionada e nem haja intermediárias, garante ao menos 1
        if not z_pos:
            z_pos.append(("Central", oz + max(0.0, (A - E) / 2.0)))

        # Ordena as prateleiras em Z para numeração lógica
        z_pos.sort(key=lambda item: item[1])

        groups: list[Group] = []
        for idx, (label, z) in enumerate(z_pos, 1):
            spec = ChapaSpec.resolve(
                nome=f"Prateleira Avulsa {idx} ({label})",
                papel=PapelChapa.PRATELEIRA,
                ctx=mat_ctx,
                material_override=material,
                fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
                material_fita_override=material_fita,
            )
            p = build_chapa(
                spec,
                (ox, oy, z),
                (L, P, E),
                color=cor,
                cor_fita=cor_fita,
            )
            groups.append(p)

        return groups





