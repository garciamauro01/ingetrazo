# SPDX-License-Identifier: GPL-3.0-or-later
"""Costing rules: markup on cost, margin on sale, taxes, discounts, rounding."""
from __future__ import annotations

import pytest

from plugins.furniture_pro.furniture import template_by_type
from plugins.furniture_pro.furniture.generator import build_module
from plugins.furniture_pro.hardware import HardwareLibrary
from plugins.furniture_pro.materials import MaterialLibrary
from plugins.furniture_pro.pricing import (CURRENCY_SYMBOLS, ModulePrice,
                                         PricingSettings, Quote, calculate_quote,
                                         format_money, material_unit_cost)


def _priced_libraries():
    materials = MaterialLibrary.with_defaults().materials
    bands = MaterialLibrary.with_defaults().edge_bands
    hardware = HardwareLibrary.with_defaults()
    for material in materials.values():
        material.cost_per_m2 = 5.0
    for item in hardware.items.values():
        item.cost = 12.0
    return materials, bands, hardware.items


def _quote(settings: PricingSettings) -> Quote:
    materials, bands, hardware = _priced_libraries()
    spec = template_by_type("armario_inferior").create()
    result = build_module(spec, materials, bands)
    return calculate_quote([result], materials, bands, hardware, settings)


def test_pricing_settings_round_trip_through_dict() -> None:
    settings = PricingSettings(currency="USD", tax_rate=0.1, discount_rate=0.05,
                               margin_on_sale=0.2, markup_on_cost=0.1,
                               rounding_step=0.05, labor_cost_per_hour=40,
                               assembly_hours_per_module=2, labor_hours=3,
                               overhead_rate=0.15, commission_rate=0.05,
                               freight=100, extra_cost=20, waste_rate=0.02)
    restored = PricingSettings.from_dict(settings.to_dict())
    assert restored == settings
    defaults = PricingSettings.from_dict(None)
    assert defaults.currency == "BRL"
    assert defaults.tax_rate == 0.0
    assert defaults.margin_on_sale == 0.0
    assert defaults.markup_on_cost == 0.0


def test_pricing_settings_reject_out_of_range_values() -> None:
    assert PricingSettings(tax_rate=-0.1).validate()
    assert PricingSettings(discount_rate=1.0).validate()
    assert PricingSettings(margin_on_sale=1.0).validate()
    assert PricingSettings(commission_rate=1.0).validate()
    assert PricingSettings(rounding_step=-1.0).validate()
    assert PricingSettings.from_dict({"currency": "BRL"}).validate() == []


def test_material_unit_cost_prefers_m2_and_falls_back_to_sheet() -> None:
    from plugins.furniture_pro.core.models import Material

    mat = Material("MAT-X", "X", cost_per_m2=4.0, cost_per_sheet=100.0)
    assert material_unit_cost(mat) == (4.0, "m2")
    mat2 = Material("MAT-Y", "Y", cost_per_m2=0.0, cost_per_sheet=300.0,
                    sheet_length_mm=3000.0, sheet_width_mm=1500.0)
    unit, basis = material_unit_cost(mat2)
    assert basis == "sheet"
    assert unit == pytest.approx(300.0 / 4.5)
    assert material_unit_cost(Material("MAT-Z", "Z")) == (0.0, "unpriced")


def test_quote_defaults_to_markup_on_cost() -> None:
    quote = _quote(PricingSettings())
    assert quote.pricing_mode == "markup"
    assert quote.base_price == pytest.approx(quote.cost)


def test_quote_uses_markup_on_cost_when_no_margin_is_set() -> None:
    quote = _quote(PricingSettings(markup_on_cost=0.25))
    assert quote.pricing_mode == "markup"
    # Values are rounded to the configured step before being reported.
    assert quote.base_price == pytest.approx(quote.cost * 1.25, abs=0.05)
    assert quote.total == pytest.approx(quote.base_price, abs=0.05)


def test_quote_uses_margin_on_sale_when_configured() -> None:
    quote = _quote(PricingSettings(margin_on_sale=0.25))
    assert quote.pricing_mode == "margin"
    assert quote.base_price == pytest.approx(
        quote.cost / (1.0 - 0.25), abs=0.05)
    effective_margin = (quote.total - quote.cost) / quote.total
    assert quote.margin_on_sale == pytest.approx(effective_margin, abs=1e-3)
    assert quote.markup_on_cost == pytest.approx(
        quote.margin_on_sale / (1.0 - quote.margin_on_sale), abs=1e-3)


def test_margin_wins_when_both_are_configured() -> None:
    quote = _quote(PricingSettings(margin_on_sale=0.2, markup_on_cost=0.5))
    assert quote.pricing_mode == "margin"
    assert any("prevaleceu" in w for w in quote.warnings)
    assert quote.base_price == pytest.approx(quote.cost / 0.8, abs=0.05)


def test_invalid_margin_falls_back_to_markup_zero() -> None:
    quote = _quote(PricingSettings(margin_on_sale=1.0))
    assert quote.pricing_mode == "markup"
    assert any("Margem inválida" in w for w in quote.warnings)
    assert quote.base_price == pytest.approx(quote.cost)


def test_discount_and_tax_compose_on_the_sale_price() -> None:
    quote = _quote(PricingSettings(discount_rate=0.10, tax_rate=0.20))
    base = quote.cost
    discount = base * 0.10
    tax = (base - discount) * 0.20
    assert quote.base_price == pytest.approx(base, abs=0.05)
    assert quote.discount == pytest.approx(discount, abs=0.05)
    assert quote.tax == pytest.approx(tax, abs=0.05)
    assert quote.total == pytest.approx(base - discount + tax, abs=0.05)


def test_labor_overhead_extra_and_freight_feed_the_cost() -> None:
    quote = _quote(PricingSettings(
        labor_cost_per_hour=30.0, assembly_hours_per_module=2.0,
        overhead_rate=0.2, extra_cost=15.0, freight=10.0))
    components = (quote.material_cost + quote.edge_cost + quote.hardware_cost
                  + quote.labor_cost)
    assert quote.overhead_cost == pytest.approx(components * 0.2, abs=0.05)
    assert quote.cost == pytest.approx(
        components * 1.2 + quote.extra_cost + quote.freight, abs=0.05)
    assert quote.freight == 10.0
    assert quote.extra_cost == 15.0


def test_quote_warns_when_materials_have_no_price() -> None:
    materials = MaterialLibrary.with_defaults().materials
    bands = MaterialLibrary.with_defaults().edge_bands
    hardware = HardwareLibrary.with_defaults()
    for item in hardware.items.values():
        item.cost = 0.0
    spec = template_by_type("armario_inferior").create()
    result = build_module(spec, materials, bands)
    quote = calculate_quote([result], materials, bands, hardware.items)
    assert any("Sem preço cadastrado" in w for w in quote.warnings)


def test_quote_reports_one_price_row_per_module() -> None:
    quote = _quote(PricingSettings())
    assert len(quote.modules) == 1
    row: ModulePrice = quote.modules[0]
    assert row.module_id
    assert row.cost >= 0.0
    assert row.sale >= 0.0
    assert quote.material_cost >= 0.0
    assert quote.hardware_cost >= 0.0


def test_quote_lines_cover_every_committed_line() -> None:
    quote = _quote(PricingSettings())
    labels = [label for label, _value in quote.lines()]
    assert labels[0] == "Material"
    assert labels[-1] == "Total"
    assert len(labels) == 12


def test_format_money_uses_brazilian_grouping_and_symbols() -> None:
    assert CURRENCY_SYMBOLS["BRL"] == "R$"
    assert format_money(1234.56, "BRL") == "R$ 1.234,56"
    assert format_money(0.0, "BRL") == "R$ 0,00"
    assert format_money(10.0, "USD") == "$ 10.00"
