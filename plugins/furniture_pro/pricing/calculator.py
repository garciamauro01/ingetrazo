# SPDX-License-Identifier: GPL-3.0-or-later
"""Costing and quoting.

Commercial rules are explicit and separate:

* **markup on cost** — ``sale = cost × (1 + markup)``;
* **margin on sale** — ``sale = cost ÷ (1 − margin)``.

Using one while calling it the other is the classic quoting error, so both
percentages are shown in the result and the effective values are recomputed
from the final price.  Discounts apply to the sale price, taxes apply after
the discount, and the rounding step is configurable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from ..core.models import BuildResult, EdgeBand, HardwareItem, Material, Panel
from ..core.validation import ValidationReport


@dataclass
class PricingSettings:
    currency: str = "BRL"
    tax_rate: float = 0.0
    discount_rate: float = 0.0
    margin_on_sale: float = 0.0
    markup_on_cost: float = 0.0
    rounding_step: float = 0.01
    labor_cost_per_hour: float = 0.0
    assembly_hours_per_module: float = 0.0
    labor_hours: float = 0.0
    overhead_rate: float = 0.0
    commission_rate: float = 0.0
    freight: float = 0.0
    extra_cost: float = 0.0
    waste_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "currency": self.currency, "tax_rate": self.tax_rate,
            "discount_rate": self.discount_rate,
            "margin_on_sale": self.margin_on_sale,
            "markup_on_cost": self.markup_on_cost,
            "rounding_step": self.rounding_step,
            "labor_cost_per_hour": self.labor_cost_per_hour,
            "assembly_hours_per_module": self.assembly_hours_per_module,
            "labor_hours": self.labor_hours,
            "overhead_rate": self.overhead_rate,
            "commission_rate": self.commission_rate,
            "freight": self.freight, "extra_cost": self.extra_cost,
            "waste_rate": self.waste_rate,
        }

    @classmethod
    def from_dict(cls, raw) -> "PricingSettings":
        raw = raw if isinstance(raw, dict) else {}
        out = cls()
        for key in out.to_dict():
            if key not in raw:
                continue
            value = raw[key]
            if key == "currency":
                out.currency = str(value or "BRL")
                continue
            try:
                setattr(out, key, float(value))
            except (TypeError, ValueError):
                pass
        return out

    def validate(self) -> list[str]:
        problems: list[str] = []
        for label, value in (("imposto", self.tax_rate),
                             ("desconto", self.discount_rate),
                             ("margem", self.margin_on_sale),
                             ("markup", self.markup_on_cost),
                             ("comissão", self.commission_rate),
                             ("overhead", self.overhead_rate),
                             ("perda de material", self.waste_rate)):
            if value < 0:
                problems.append(f"A taxa de {label} não pode ser negativa.")
        if self.margin_on_sale >= 1.0:
            problems.append("A margem sobre venda deve ser menor que 100%.")
        if self.discount_rate >= 1.0:
            problems.append("O desconto deve ser menor que 100%.")
        if self.tax_rate >= 1.0:
            problems.append("O imposto deve ser menor que 100%.")
        if self.commission_rate >= 1.0:
            problems.append("A comissão deve ser menor que 100%.")
        if self.rounding_step < 0:
            problems.append("O arredondamento não pode ser negativo.")
        return problems


@dataclass
class ModulePrice:
    module_id: str
    code: str
    name: str
    material_cost: float = 0.0
    edge_cost: float = 0.0
    hardware_cost: float = 0.0
    labor_cost: float = 0.0
    overhead_cost: float = 0.0
    extra_cost: float = 0.0
    cost: float = 0.0
    sale: float = 0.0
    margin: float = 0.0
    markup: float = 0.0

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Quote:
    modules: list[ModulePrice] = field(default_factory=list)
    material_cost: float = 0.0
    edge_cost: float = 0.0
    hardware_cost: float = 0.0
    labor_cost: float = 0.0
    overhead_cost: float = 0.0
    extra_cost: float = 0.0
    freight: float = 0.0
    cost: float = 0.0
    base_price: float = 0.0
    discount: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    margin_value: float = 0.0
    margin_on_sale: float = 0.0
    markup_on_cost: float = 0.0
    currency: str = "BRL"
    pricing_mode: str = "markup"
    warnings: list[str] = field(default_factory=list)
    settings: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "modules": [m.to_dict() for m in self.modules],
            "material_cost": self.material_cost,
            "edge_cost": self.edge_cost,
            "hardware_cost": self.hardware_cost,
            "labor_cost": self.labor_cost,
            "overhead_cost": self.overhead_cost,
            "extra_cost": self.extra_cost,
            "freight": self.freight,
            "cost": self.cost, "base_price": self.base_price,
            "discount": self.discount, "tax": self.tax,
            "total": self.total, "margin_value": self.margin_value,
            "margin_on_sale": self.margin_on_sale,
            "markup_on_cost": self.markup_on_cost,
            "currency": self.currency, "pricing_mode": self.pricing_mode,
            "warnings": list(self.warnings), "settings": dict(self.settings),
        }

    def lines(self) -> list[tuple[str, float]]:
        """Rows for a report, in display order."""
        return [
            ("Material", self.material_cost),
            ("Fita de borda", self.edge_cost),
            ("Ferragens", self.hardware_cost),
            ("Mão de obra", self.labor_cost),
            ("Overhead", self.overhead_cost),
            ("Custos extras", self.extra_cost),
            ("Frete", self.freight),
            ("Custo total", self.cost),
            ("Preço bruto", self.base_price),
            ("Desconto", -self.discount),
            ("Impostos", self.tax),
            ("Total", self.total),
        ]


def _round_money(value: float, step: float) -> float:
    if step <= 0:
        return round(float(value), 2)
    return round(round(float(value) / step) * step, 6)


def material_unit_cost(material: Material) -> tuple[float, str]:
    """Cost per square metre of a material and the basis used."""
    if material.cost_per_m2 > 0:
        return material.cost_per_m2, "m2"
    if material.cost_per_sheet > 0:
        sheet_m2 = (material.sheet_length_mm * material.sheet_width_mm) / 1e6
        if sheet_m2 > 0:
            return material.cost_per_sheet / sheet_m2, "sheet"
    return 0.0, "unpriced"


def _panel_area(panel: Panel) -> float:
    return (panel.length_mm * panel.width_mm) / 1_000_000.0 * max(1, panel.qty)


def _hardware_cost(use, hardware: dict[str, HardwareItem]) -> tuple[float, str]:
    item = hardware.get(use.hardware_id)
    if item is None:
        return 0.0, f"Ferragem não cadastrada: {use.hardware_id}."
    if item.cost <= 0:
        return 0.0, f"Ferragem sem preço: {item.name}."
    return float(item.cost) * float(use.qty), ""


def calculate_quote(
    results: Iterable[BuildResult],
    materials: dict[str, Material],
    edge_bands: dict[str, EdgeBand],
    hardware: dict[str, HardwareItem],
    settings: PricingSettings | None = None,
    *,
    cut_plan=None,
    project_name: str = "",
) -> Quote:
    """Price every module and the project.

    The material line uses the cutting plan's board count when a plan is
    given (the truthful way to price sheets); otherwise it estimates by part
    area and, if the user configured a waste rate, adds that allowance.
    """
    settings = settings or PricingSettings()
    quote = Quote(currency=settings.currency,
                  settings=settings.to_dict())
    problems = settings.validate()
    quote.warnings.extend(problems)
    report = ValidationReport()

    results = list(results)
    module_prices: list[ModulePrice] = []
    total_material_area: dict[str, float] = {}
    total_edge: dict[str, float] = {}
    hardware_totals: dict[str, float] = {}
    hardware_missing: set[str] = set()
    unpriced: set[str] = set()

    for result in results:
        spec = result.spec
        row = ModulePrice(module_id=spec.id, code=spec.code, name=spec.label)
        for panel in result.panels:
            area = _panel_area(panel)
            mat = materials.get(panel.material_id)
            if mat is None:
                row.material_cost += 0.0
                total_material_area.setdefault(panel.material_id, 0.0)
                report.warnings.append(
                    f"{spec.label}: material não cadastrado "
                    f"({panel.material_id}).")
                continue
            unit, basis = material_unit_cost(mat)
            if basis == "unpriced":
                unpriced.add(mat.name)
            row.material_cost += area * unit
            total_material_area[panel.material_id] = (
                total_material_area.get(panel.material_id, 0.0) + area)
            # Count the banded edges once per side: an edge can only carry
            # one band, and the cost is per metre of that edge.
            seen_bands = {b for b in panel.edges.values() if b}
            for band_id in seen_bands:
                band = edge_bands.get(band_id)
                if band is None:
                    report.warnings.append(
                        f"{spec.label}: fita não cadastrada ({band_id}).")
                    continue
                if band.cost_per_m <= 0:
                    unpriced.add(band.name)
                # Edge length by side, counted only once per side.
                mm = sum(panel.edge_length_mm(side)
                         for side, value in panel.edges.items()
                         if value == band_id)
                row.edge_cost += (mm / 1000.0 * max(1, panel.qty)
                                  * max(0.0, band.cost_per_m))
                total_edge[band_id] = total_edge.get(band_id, 0.0) + (
                    mm / 1000.0 * max(1, panel.qty))
        for use in result.hardware:
            cost, warning = _hardware_cost(use, hardware)
            row.hardware_cost += cost
            hardware_totals[use.hardware_id] = (
                hardware_totals.get(use.hardware_id, 0.0) + use.qty)
            if warning:
                hardware_missing.add(warning)
        module_prices.append(row)

    quote.modules = module_prices
    quote.material_cost = sum(r.material_cost for r in module_prices)
    quote.edge_cost = sum(r.edge_cost for r in module_prices)
    quote.hardware_cost = sum(r.hardware_cost for r in module_prices)

    # If a cutting plan exists, its board count is the material truth.
    if cut_plan is not None:
        by_material: dict[str, float] = {}
        for board in getattr(cut_plan, "boards", []) or []:
            mat = materials.get(getattr(board, "material_id", ""))
            if mat is None:
                continue
            cost = 0.0
            if mat.cost_per_sheet > 0:
                cost = mat.cost_per_sheet
            elif mat.cost_per_m2 > 0:
                cost = (mat.sheet_length_mm * mat.sheet_width_mm) / 1e6 \
                    * mat.cost_per_m2
            by_material[mat.id] = by_material.get(mat.id, 0.0) + cost
        planned_total = sum(by_material.values())
        if planned_total > 0 and quote.material_cost > 0:
            # Keep the module split, correct the project total to the plan.
            scale = planned_total / quote.material_cost
            for row in module_prices:
                row.material_cost *= scale
            quote.material_cost = planned_total
        elif planned_total > 0:
            quote.material_cost = planned_total

    if settings.waste_rate > 0 and cut_plan is None:
        quote.material_cost *= 1.0 + settings.waste_rate

    n_modules = len(module_prices)
    labor_hours = (settings.labor_hours
                   + settings.assembly_hours_per_module * n_modules)
    quote.labor_cost = max(0.0, settings.labor_cost_per_hour) * labor_hours
    base_costs = (quote.material_cost + quote.edge_cost
                  + quote.hardware_cost + quote.labor_cost)
    quote.overhead_cost = base_costs * max(0.0, settings.overhead_rate)
    quote.extra_cost = max(0.0, settings.extra_cost)
    quote.freight = max(0.0, settings.freight)
    quote.cost = base_costs + quote.overhead_cost + quote.extra_cost \
        + quote.freight

    # Commercial formula.  Margin wins when both are set, and says so.
    mode = "markup"
    if settings.margin_on_sale > 0:
        if settings.margin_on_sale >= 1:
            quote.warnings.append("Margem inválida; usando markup zero.")
            base_price = quote.cost
            mode = "markup"
        else:
            mode = "margin"
            if settings.markup_on_cost > 0:
                quote.warnings.append(
                    "Margem sobre venda e markup sobre custo foram informados "
                    "juntos; a margem sobre venda prevaleceu.")
            base_price = quote.cost / (1.0 - settings.margin_on_sale)
    else:
        base_price = quote.cost * (1.0 + max(0.0, settings.markup_on_cost))

    discount = base_price * max(0.0, min(0.999, settings.discount_rate))
    taxable = max(0.0, base_price - discount)
    tax = taxable * max(0.0, settings.tax_rate)
    total = taxable + tax
    quote.base_price = _round_money(base_price, settings.rounding_step)
    quote.discount = _round_money(discount, settings.rounding_step)
    quote.tax = _round_money(tax, settings.rounding_step)
    quote.total = _round_money(total, settings.rounding_step)
    quote.cost = _round_money(quote.cost, settings.rounding_step)
    quote.margin_value = quote.total - quote.cost
    quote.margin_on_sale = (quote.margin_value / quote.total
                            if quote.total else 0.0)
    quote.markup_on_cost = (quote.margin_value / quote.cost
                            if quote.cost else 0.0)
    quote.pricing_mode = mode

    # Allocate the final sale and cost to modules by their direct cost.
    direct_total = sum(r.material_cost + r.edge_cost + r.hardware_cost
                       for r in module_prices) or 1.0
    for row in module_prices:
        direct = row.material_cost + row.edge_cost + row.hardware_cost
        share = direct / direct_total if direct_total else 0.0
        row.labor_cost = quote.labor_cost * share
        row.overhead_cost = quote.overhead_cost * share
        row.extra_cost = (quote.extra_cost + quote.freight) * share
        row.cost = direct + row.labor_cost + row.overhead_cost + row.extra_cost
        row.sale = quote.total * share if quote.total else 0.0
        row.margin = (row.sale - row.cost) / row.sale if row.sale else 0.0
        row.markup = (row.sale - row.cost) / row.cost if row.cost else 0.0

    for name in sorted(unpriced):
        quote.warnings.append(f"Sem preço cadastrado: {name}.")
    quote.warnings.extend(sorted(hardware_missing))
    quote.warnings.extend(report.warnings)
    # De-duplicate while preserving order.
    quote.warnings = list(dict.fromkeys(quote.warnings))
    return quote


CURRENCY_SYMBOLS = {"BRL": "R$", "USD": "$", "EUR": "€", "ARS": "$",
                    "PEN": "S/"}


def format_money(value: float, currency: str = "BRL") -> str:
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    negative = value < 0
    text = f"{abs(float(value)):,.2f}"
    # Brazilian style: dot thousands, comma decimals, for BRL/PEN/EUR.
    if currency in ("BRL", "EUR", "PEN", "ARS"):
        text = text.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{'-' if negative else ''}{symbol} {text}"
