# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations
from typing import Any
from core.group import Group
from ..builders.mesh_utils import (
    _get_material_texture,
    _contorno_retangular_xy,
    _make_slab_with_holes_mesh,
    _make_bowl_mesh,
    _make_gourmet_faucet_mesh,
)
from ..builders.chapa_builder import build_chapa
from ..builders.chapa_spec import ChapaSpec, PapelChapa, ModuloMaterialContext


def _chapa(
    name: str,
    origin: tuple[float, float, float],
    size: tuple[float, float, float],
    material: str,
    fita_c1: bool = False,
    fita_c2: bool = False,
    fita_l1: bool = False,
    fita_l2: bool = False,
    **kwargs: Any,
) -> Group:
    """Cria uma peça de bancada pela API canônica de chapa (material explícito)."""
    spec = ChapaSpec.resolve(
        nome=name,
        papel=PapelChapa.PECA_AVULSA,
        ctx=ModuloMaterialContext(material_caixa=material),
        material_override=material,
        fita_override=(fita_c1, fita_c2, fita_l1, fita_l2),
    )
    return build_chapa(spec, origin, size, **kwargs)


class BancadaBuilder:
    """Construtor paramétrico 3D de bancadas de pedra, mármores, cubas e marmoraria."""

    @staticmethod
    def get_material_color(material: str) -> tuple[float, float, float]:
        from ..domain.materials_catalog import get_material_color
        return get_material_color(material)

    @classmethod
    def build_bancada_reta(
        cls,
        largura_mm: float,
        altura_mm: float = 40.0,
        prof_mm: float = 600.0,
        esp_pedra_mm: float = 20.0,
        altura_saia_mm: float = 40.0,
        altura_frontao_mm: float = 100.0,
        balanco_frontal_mm: float = 20.0,
        tem_frontao_traseiro: bool = True,
        tem_frontao_esq: bool = False,
        tem_frontao_dir: bool = False,
        tem_saia_esq: bool = True,
        tem_saia_dir: bool = True,
        material: str = "Granito Preto São Gabriel 20mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.82),
    ) -> list[Group]:
        """Gera uma bancada reta de pedra com tampo maciço, saia frontal/laterais e frontões."""
        ox, oy, oz = offset
        L = largura_mm / 1000.0
        P = prof_mm / 1000.0
        Ep = esp_pedra_mm / 1000.0
        Asaia = max(Ep, altura_saia_mm / 1000.0)
        Afront = altura_frontao_mm / 1000.0
        Bfront = balanco_frontal_mm / 1000.0
        cor = cls.get_material_color(material)

        groups: list[Group] = []

        # 1. Tampo Superior Principal (Massa da Pedra)
        # O tampo cobre de X: ox até ox + L, e em Y avança para a frente (-Y) pelo balanço
        # A face superior do tampo fica em oz + Asaia
        z_tampo = oz + Asaia - Ep
        y_frente = oy - Bfront
        groups.append(_chapa(
            "Bancada - Tampo Superior",
            (ox, y_frente, z_tampo),
            (L, P + Bfront, Ep),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
        ))

        # 2. Saia Frontal (Testeira)
        # Encaixada sob o tampo na face frontal
        if Asaia > Ep:
            groups.append(_chapa(
                "Bancada - Saia Frontal",
                (ox, y_frente, oz),
                (L, Ep, Asaia - Ep),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))

        # 3. Saias Laterais (se expostas)
        if tem_saia_esq and Asaia > Ep:
            groups.append(_chapa(
                "Bancada - Saia Lateral Esq",
                (ox, y_frente + Ep, oz),
                (Ep, P + Bfront - Ep, Asaia - Ep),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))
        if tem_saia_dir and Asaia > Ep:
            groups.append(_chapa(
                "Bancada - Saia Lateral Dir",
                (ox + L - Ep, y_frente + Ep, oz),
                (Ep, P + Bfront - Ep, Asaia - Ep),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))

        # 4. Frontão / Rodabanca (Traseiro e Laterais encostadas em parede)
        z_frontao = oz + Asaia
        if tem_frontao_traseiro and Afront > 0:
            groups.append(_chapa(
                "Bancada - Frontao Traseiro",
                (ox, oy + P - Ep, z_frontao),
                (L, Ep, Afront),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))
        if tem_frontao_esq and Afront > 0:
            groups.append(_chapa(
                "Bancada - Frontao Lateral Esq",
                (ox, y_frente, z_frontao),
                (Ep, P + Bfront - Ep, Afront),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))
        if tem_frontao_dir and Afront > 0:
            groups.append(_chapa(
                "Bancada - Frontao Lateral Dir",
                (ox + L - Ep, y_frente, z_frontao),
                (Ep, P + Bfront - Ep, Afront),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))

        return groups

    @classmethod
    def build_bancada_pia(
        cls,
        largura_mm: float,
        altura_mm: float = 40.0,
        prof_mm: float = 600.0,
        esp_pedra_mm: float = 20.0,
        altura_saia_mm: float = 40.0,
        altura_frontao_mm: float = 100.0,
        balanco_frontal_mm: float = 20.0,
        tem_saia_esq: bool = True,
        tem_saia_dir: bool = True,
        largura_cuba_mm: float = 560.0,
        prof_cuba_mm: float = 400.0,
        profundidade_cuba_mm: float = 180.0,
        posicao_cuba: str = "centro",  # "centro", "esquerda", "direita"
        tipo_cuba: str = "inox_simples",  # "inox_simples", "inox_dupla", "esculpida"
        canto_recorte: str = "arredondado",  # "reto" ou "arredondado"
        raio_canto_mm: float = 20.0,
        tem_area_molhada: bool = True,
        rebaixo_molhado_mm: float = 3.0,
        tem_torneira: bool = True,
        material: str = "Granito Preto São Gabriel 20mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.82),
    ) -> list[Group]:
        """Gera uma bancada de pia com tampo maciço INTEIRIÇO com recorte da cuba, área molhada rebaixada e cuba estilizada."""
        ox, oy, oz = offset
        L = largura_mm / 1000.0
        P = prof_mm / 1000.0
        Ep = esp_pedra_mm / 1000.0
        Asaia = max(Ep, altura_saia_mm / 1000.0)
        Afront = altura_frontao_mm / 1000.0
        Bfront = balanco_frontal_mm / 1000.0
        cor_pedra = cls.get_material_color(material)

        Lcuba = min(largura_cuba_mm / 1000.0, L - 0.20)
        Pcuba = min(prof_cuba_mm / 1000.0, P - 0.15)
        Acuba = profundidade_cuba_mm / 1000.0

        groups: list[Group] = []

        # Determina posição X da cuba
        if posicao_cuba == "esquerda":
            x_cuba = ox + 0.10
        elif posicao_cuba == "direita":
            x_cuba = ox + L - Lcuba - 0.10
        else:
            x_cuba = ox + (L - Lcuba) / 2.0

        y_frente = oy - Bfront
        # Posição Y da cuba (afastada 60mm da borda frontal da pedra)
        y_cuba = y_frente + Ep + 0.06
        y_tras_cuba = y_cuba + Pcuba

        z_tampo = oz + Asaia - Ep
        raio_canto_m = (raio_canto_mm / 1000.0) if canto_recorte == "arredondado" else 0.0

        # Define contorno(s) dos recortes de cuba
        furos_xy: list[list[tuple[float, float]]] = []
        if tipo_cuba == "inox_dupla":
            meia_l = (Lcuba - 0.03) / 2.0
            r_meia = min(raio_canto_m, (meia_l / 2.0) - 0.005)
            furos_xy.append(_contorno_retangular_xy(x_cuba, y_cuba, meia_l, Pcuba, r_meia))
            furos_xy.append(_contorno_retangular_xy(x_cuba + meia_l + 0.03, y_cuba, meia_l, Pcuba, r_meia))
        else:
            furos_xy.append(_contorno_retangular_xy(x_cuba, y_cuba, Lcuba, Pcuba, raio_canto_m))

        # 1. Geometria da Bancada: Borda Seca Contínua (Moldura Perimetral) + Fundo Rebaixado (Área Molhada)
        # Exatamente como no modelo de referência profissional (Component_9.skp):
        # A bancada possui:
        # - Altura total com testeira/saia dobrada: Asaia (ex: 40mm)
        # - Borda seca elevada no topo (Z = oz + Asaia - Ep até oz + Asaia) contornando a frente e laterais (largura padrão: 20mm a 40mm)
        # - Área molhada rebaixada em 20mm (nível Z = oz + Asaia - 2*Ep até oz + Asaia - Ep) ocupando toda a bacia central
        # - Recorte da cuba no fundo rebaixado com os cantos arredondados ou retos especificados
        # - Frontão traseiro (rodabanca) subindo colado na parede traseira
        # - Cuba 3D posicionada exatamente no recorte

        larg_moldura = 0.020  # Moldura de borda de 20mm (idêntica ao Component_9.skp)
        reb_m = max(0.010, min(Ep, rebaixo_molhado_mm / 1000.0 if rebaixo_molhado_mm > 0 else 0.020)) if tem_area_molhada else 0.0

        if tem_area_molhada:
            # 1.1 Moldura Perimetral Elevada (Nível Superior / Seco: Z de oz + Asaia - reb_m até oz + Asaia)
            # A moldura corre na frente e nas laterais até o fundo da bancada (oy + P)
            prof_moldura_lat = (oy + P) - (y_frente + larg_moldura)
            groups.append(_chapa(
                "Bancada - Moldura Seca Frontal",
                (ox, y_frente, oz + Asaia - reb_m),
                (L, larg_moldura, reb_m),
                material, color=cor_pedra
            ))
            groups.append(_chapa(
                "Bancada - Moldura Seca Lateral Esq",
                (ox, y_frente + larg_moldura, oz + Asaia - reb_m),
                (larg_moldura, prof_moldura_lat, reb_m),
                material, color=cor_pedra
            ))
            groups.append(_chapa(
                "Bancada - Moldura Seca Lateral Dir",
                (ox + L - larg_moldura, y_frente + larg_moldura, oz + Asaia - reb_m),
                (larg_moldura, prof_moldura_lat, reb_m),
                material, color=cor_pedra
            ))
            # Moldura traseira sob o frontão (para que o frontão assente sobre a pedra):
            groups.append(_chapa(
                "Bancada - Moldura Seca Traseira",
                (ox + larg_moldura, oy + P - Ep, oz + Asaia - reb_m),
                (L - 2 * larg_moldura, Ep, reb_m),
                material, color=cor_pedra
            ))

            # 1.2 Fundo Rebaixado da Área Molhada (Com o recorte vazado da cuba)
            # Ocupa o vão interno entre as molduras elevadas
            x_fundo = ox + larg_moldura
            larg_fundo = L - 2 * larg_moldura
            y_fundo = y_frente + larg_moldura
            prof_fundo = (oy + P - Ep) - y_fundo
            z_fundo = oz + Asaia - Ep - reb_m

            tex_pedra = _get_material_texture(material)
            tampo_molhado_mesh = _make_slab_with_holes_mesh(
                x0=x_fundo, y0=y_fundo, z0=z_fundo,
                largura=larg_fundo, profundidade=prof_fundo,
                espessura=Ep,
                furos_xy=furos_xy,
                color=cor_pedra,
                texture=tex_pedra,
            )
            grp_tampo_molhado = Group(tampo_molhado_mesh, name="Bancada - Tampo Superior Área Molhada")
            if getattr(grp_tampo_molhado, "ext", None) is None:
                grp_tampo_molhado.ext = {}
            grp_tampo_molhado.ext["trazomob"] = {
                "nome": "Bancada - Tampo Superior Área Molhada",
                "comprimento": larg_fundo * 1000.0,
                "largura": prof_fundo * 1000.0,
                "espessura": Ep * 1000.0,
                "material": material,
                "canto_recorte": canto_recorte,
                "raio_canto_mm": raio_canto_mm,
            }
            groups.append(grp_tampo_molhado)

        else:
            # Sem área molhada rebaixada: Tampo monolítico inteiriço contínuo
            tex_pedra = _get_material_texture(material)
            tampo_mesh = _make_slab_with_holes_mesh(
                x0=ox, y0=y_frente, z0=z_tampo,
                largura=L, profundidade=P + Bfront, espessura=Ep,
                furos_xy=furos_xy,
                color=cor_pedra,
                texture=tex_pedra,
            )
            grp_tampo = Group(tampo_mesh, name="Bancada - Tampo Superior Inteiriço")
            if getattr(grp_tampo, "ext", None) is None:
                grp_tampo.ext = {}
            grp_tampo.ext["trazomob"] = {
                "nome": "Bancada - Tampo Superior",
                "comprimento": L * 1000.0,
                "largura": (P + Bfront) * 1000.0,
                "espessura": Ep * 1000.0,
                "material": material,
                "canto_recorte": canto_recorte,
                "raio_canto_mm": raio_canto_mm,
            }
            groups.append(grp_tampo)

        # 2. Cuba 3D (Inox ou Esculpida) com cantos retos ou arredondados idênticos ao recorte
        cor_inox = (0.80, 0.82, 0.85)
        cor_fundo_cuba = (0.70, 0.72, 0.75)
        cor_cuba_wall = cor_pedra if "esculpida" in tipo_cuba else cor_inox
        cor_cuba_bot = cor_pedra if "esculpida" in tipo_cuba else cor_fundo_cuba

        # Altura do topo da bacia da cuba (encosta por baixo ou no nível do recorte)
        z_cuba_topo = z_fundo if tem_area_molhada else z_tampo

        if tipo_cuba == "inox_dupla":
            meia_l = (Lcuba - 0.03) / 2.0
            r_meia = min(raio_canto_m, (meia_l / 2.0) - 0.005)
            for idx_c, xc in enumerate([x_cuba, x_cuba + meia_l + 0.03]):
                bowl_mesh = _make_bowl_mesh(
                    x0=xc, y0=y_cuba, largura=meia_l, profundidade=Pcuba,
                    raio=r_meia, z_topo=z_cuba_topo, altura=Acuba,
                    cor_parede=cor_inox, cor_fundo=cor_fundo_cuba
                )
                groups.append(Group(bowl_mesh, name=f"Cuba Inox - Bacia {idx_c+1}"))
                rx = xc + (meia_l / 2.0) - 0.035
                ry = y_cuba + (Pcuba / 2.0) - 0.035
                groups.append(_chapa(
                    f"Cuba - Valvula Inox {idx_c+1}",
                    (rx, ry, z_cuba_topo - Acuba + 0.002),
                    (0.07, 0.07, 0.003),
                    "Inox Cromado", color=(0.90, 0.92, 0.95)
                ))
        else:
            bowl_mesh = _make_bowl_mesh(
                x0=x_cuba, y0=y_cuba, largura=Lcuba, profundidade=Pcuba,
                raio=raio_canto_m, z_topo=z_cuba_topo, altura=Acuba,
                cor_parede=cor_cuba_wall, cor_fundo=cor_cuba_bot
            )
            groups.append(Group(bowl_mesh, name="Cuba - Bacia"))

            # Ralo / Válvula de escoamento no centro do fundo
            rx = x_cuba + (Lcuba / 2.0) - 0.04
            ry = y_cuba + (Pcuba / 2.0) - 0.04
            groups.append(_chapa(
                "Cuba - Valvula Inox",
                (rx, ry, z_cuba_topo - Acuba + 0.002),
                (0.08, 0.08, 0.003),
                "Inox Cromado", color=(0.90, 0.92, 0.95)
            ))

        # 3. Torneira Monocomando Gourmet (Cromada / Grafite)
        if tem_torneira:
            tx = x_cuba + (Lcuba / 2.0)
            ty = y_tras_cuba + 0.035
            tz = oz + Asaia
            faucet_mesh = _make_gourmet_faucet_mesh((tx, ty, tz))
            grp_torneira = Group(faucet_mesh, name="Torneira Gourmet Monocomando")
            if getattr(grp_torneira, "ext", None) is None:
                grp_torneira.ext = {}
            grp_torneira.ext["trazomob"] = {
                "nome": "Torneira Gourmet Monocomando",
                "material": "Metal Cromado",
            }
            groups.append(grp_torneira)

        # 4. Saia / Testeira Frontal e Laterais (Engrossamento que vai da base até a moldura/tampo)
        # Para que a saia encontre a moldura superior SEM VÃO NENHUM:
        # A face superior da saia encosta exatamente na base da moldura (Z = oz + Asaia - reb_m)
        # e desce até Z = oz.
        if Asaia > Ep:
            z_topo_saia = oz + Asaia - reb_m
            alt_saia_real = z_topo_saia - oz
            if alt_saia_real > 0.001:
                groups.append(_chapa(
                    "Bancada - Saia Frontal",
                    (ox, y_frente, oz),
                    (L, Ep, alt_saia_real),
                    material, color=cor_pedra
                ))
                if tem_saia_esq:
                    groups.append(_chapa(
                        "Bancada - Saia Lateral Esq",
                        (ox, y_frente + Ep, oz),
                        (Ep, P + Bfront - Ep, alt_saia_real),
                        material, color=cor_pedra
                    ))
                if tem_saia_dir:
                    groups.append(_chapa(
                        "Bancada - Saia Lateral Dir",
                        (ox + L - Ep, y_frente + Ep, oz),
                        (Ep, P + Bfront - Ep, alt_saia_real),
                        material, color=cor_pedra
                    ))

        # 5. Frontão Traseiro (Rodabanca colado na parede traseira)
        z_frontao = oz + Asaia
        if Afront > 0:
            groups.append(_chapa(
                "Bancada - Frontao Traseiro",
                (ox, oy + P - Ep, z_frontao),
                (L, Ep, Afront),
                material, color=cor_pedra
            ))

        return groups

    @classmethod
    def build_bancada_canto_l(
        cls,
        largura_mm: float,
        altura_mm: float = 40.0,
        prof_mm: float = 1200.0,
        larg_asa_mm: float = 600.0,
        esp_pedra_mm: float = 20.0,
        altura_saia_mm: float = 40.0,
        altura_frontao_mm: float = 100.0,
        balanco_frontal_mm: float = 0.0,
        tem_saia_esq: bool = True,
        tem_saia_dir: bool = True,
        material: str = "Granito Preto São Gabriel 20mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.82),
    ) -> list[Group]:
        """Gera uma bancada em L contínua de pedra com frontões nas 2 faces maiores de parede e saias frontais."""
        ox, oy, oz = offset
        Lx = largura_mm / 1000.0
        Ly = prof_mm / 1000.0
        # Profundidade das asas da bancada (limitada às dimensões totais)
        P_asa = min(larg_asa_mm / 1000.0, min(Lx, Ly) - 0.10)
        P_asa = max(0.30, P_asa)
        Px = P_asa
        Py = P_asa
        Ep = esp_pedra_mm / 1000.0
        Asaia = max(Ep, altura_saia_mm / 1000.0)
        Afront = altura_frontao_mm / 1000.0
        cor = cls.get_material_color(material)

        groups: list[Group] = []
        z_tampo = oz + Asaia - Ep

        # ── 1. TAMPOS DA BANCADA EM L ──────────────────────────────────────────
        # A bancada em L encosta nas 2 paredes no canto externo (ox, oy + Ly):
        # - Parede Traseira ao longo do eixo X (Y = oy + Ly): comprimento total Lx
        # - Parede Lateral Esquerda ao longo do eixo Y (X = ox): comprimento total Ly
        # Asa X (corre ao longo da parede traseira do fundo Y = oy + Ly):
        # Vai de x = ox até ox + Lx, e em Y ocupa de (oy + Ly - Px) até (oy + Ly)
        groups.append(_chapa(
            "Bancada L - Tampo Asa X",
            (ox, oy + Ly - Px, z_tampo),
            (Lx, Px, Ep),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
        ))

        # Asa Y (corre ao longo da parede lateral esquerda X = ox):
        # Vai de y = oy até (oy + Ly - Px), e em X ocupa de ox até (ox + Py)
        # (excluindo a sobreposição do canto já coberta pela Asa X)
        groups.append(_chapa(
            "Bancada L - Tampo Asa Y",
            (ox, oy, z_tampo),
            (Py, Ly - Px, Ep),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
        ))

        # ── 2. SAIAS / TESTEIRAS (Bordas voltadas para o usuário) ─────────────
        # As faces frontais livres onde o usuário fica:
        # 1) Frente interna da Asa X: ao longo de X em y = oy + Ly - Px, de x = ox + Py até ox + Lx
        # 2) Frente interna da Asa Y: ao longo de Y em x = ox + Py - Ep, de y = oy até oy + Ly - Px
        # 3) Terminal frontal da Asa Y (extremidade frontal sul): y = oy, de x = ox até ox + Py
        # 4) Terminal lateral da Asa X (extremidade direita leste): x = ox + Lx - Ep, de y = oy + Ly - Px até oy + Ly
        if Asaia > Ep:
            # 1. Saia Frontal Interna Asa X
            groups.append(_chapa(
                "Bancada L - Saia Frontal X",
                (ox + Py, oy + Ly - Px, oz),
                (Lx - Py, Ep, Asaia - Ep),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))
            # 2. Saia Frontal Interna Asa Y
            groups.append(_chapa(
                "Bancada L - Saia Frontal Y",
                (ox + Py - Ep, oy, oz),
                (Ep, Ly - Px, Asaia - Ep),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))
            # 3. Terminal da Asa Y (frente inferior em y = oy)
            if tem_saia_esq:
                groups.append(_chapa(
                    "Bancada L - Saia Terminal Y",
                    (ox, oy, oz),
                    (Py - Ep, Ep, Asaia - Ep),
                    material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
                ))
            # 4. Terminal da Asa X (borda direita exposta em x = ox + Lx - Ep)
            if tem_saia_dir:
                groups.append(_chapa(
                    "Bancada L - Saia Terminal X",
                    (ox + Lx - Ep, oy + Ly - Px, oz),
                    (Ep, Px, Asaia - Ep),
                    material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
                ))

        # ── 3. FRONTÕES / RODABANCAS NAS 2 FACES MAIORES (PAREDES) ───────────
        # Conforme a regra do usuário:
        # "o frontao vai nas 2 faces maiores" (as duas paredes que delimitam o canto em L).
        # Face 1 (Parede Traseira ao longo de X): Y = oy + Ly - Ep, cobrindo o comprimento total Lx!
        # Face 2 (Parede Lateral ao longo de Y): X = ox, cobrindo a profundidade total Ly (ou Ly - Ep na quina)!
        z_frontao = oz + Asaia
        if Afront > 0:
            # Frontão Parede Traseira (Face Maior 1 ao longo de X):
            # Cobre toda a extensão Lx da parede de fundo
            groups.append(_chapa(
                "Bancada L - Frontao Parede X",
                (ox, oy + Ly - Ep, z_frontao),
                (Lx, Ep, Afront),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))
            # Frontão Parede Lateral Esquerda (Face Maior 2 ao longo de Y):
            # Cobre de y = oy até a face interna do Frontão Traseiro (oy + Ly - Ep)
            groups.append(_chapa(
                "Bancada L - Frontao Parede Y",
                (ox, oy, z_frontao),
                (Ep, Ly - Ep, Afront),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))

        return groups

    @classmethod
    def build_bancada_ilha(
        cls,
        largura_mm: float,
        altura_mm: float = 60.0,
        prof_mm: float = 900.0,
        esp_pedra_mm: float = 20.0,
        altura_saia_mm: float = 60.0,
        material: str = "Quartzo Branco Calacatta 20mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.82),
    ) -> list[Group]:
        """Gera uma ilha / bancada gourmet ampla com testeiras nos 4 lados (ilha 360°)."""
        ox, oy, oz = offset
        L = largura_mm / 1000.0
        P = prof_mm / 1000.0
        Ep = esp_pedra_mm / 1000.0
        Asaia = max(Ep, altura_saia_mm / 1000.0)
        cor = cls.get_material_color(material)

        groups: list[Group] = []
        z_tampo = oz + Asaia - Ep

        # Tampo Superior
        groups.append(_chapa(
            "Ilha - Tampo Gourmet",
            (ox, oy, z_tampo),
            (L, P, Ep),
            material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
        ))

        # Saias perimetrais nos 4 lados
        if Asaia > Ep:
            alt_saia = Asaia - Ep
            # Frontal
            groups.append(_chapa(
                "Ilha - Saia Frontal",
                (ox, oy, oz),
                (L, Ep, alt_saia),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))
            # Traseira
            groups.append(_chapa(
                "Ilha - Saia Traseira",
                (ox, oy + P - Ep, oz),
                (L, Ep, alt_saia),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))
            # Lateral Esquerda
            groups.append(_chapa(
                "Ilha - Saia Lateral Esq",
                (ox, oy + Ep, oz),
                (Ep, P - 2 * Ep, alt_saia),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))
            # Lateral Direita
            groups.append(_chapa(
                "Ilha - Saia Lateral Dir",
                (ox + L - Ep, oy + Ep, oz),
                (Ep, P - 2 * Ep, alt_saia),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            ))

        return groups

    @classmethod
    def build_tampao_engrossado_pedra(
        cls,
        largura_mm: float = 600.0,
        altura_mm: float = 860.0,
        prof_mm: float = 40.0,
        esp_pedra_mm: float = 20.0,
        material: str = "Granito Preto São Gabriel 20mm",
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> list[Group]:
        """Gera um tampão engrossado de pedra (marmoraria) em bloco único com largura, altura e espessura configuráveis."""
        ox, oy, oz = offset
        L = max(0.05, float(largura_mm) / 1000.0)
        A = max(0.05, float(altura_mm) / 1000.0)
        E_total = max(0.01, float(prof_mm) / 1000.0)
        cor = cls.get_material_color(material)

        return [
            _chapa(
                "Tampao Pedra - Bloco",
                (ox, oy, oz),
                (L, E_total, A),
                material, fita_c1=True, fita_c2=True, fita_l1=True, fita_l2=True, color=cor
            )
        ]


# Aliases
CountertopBuilder = BancadaBuilder

