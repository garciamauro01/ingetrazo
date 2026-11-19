import pytest
from PySide6.QtWidgets import QApplication
from trazomob.production.labels import render_label_pixmap, ProductionLabelsDialog
from trazomob.production.report import generate_project_html_report
from trazomob.wall.elevation_dialog import WallElevationDialog

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_production_label_generation(qapp):
    part = {
        "nome": "Lateral Direita",
        "modulo": "Balcao 2P",
        "comprimento": 720.0,
        "largura": 550.0,
        "espessura": 15.0,
        "comprimento_corte": 722.0,
        "largura_corte": 552.0,
        "material": "Branco TX 15mm",
        "fita_c1": True,
        "fita_c2": False,
        "fita_l1": True,
        "fita_l2": False,
        "espessura_fita": 0.45,
        "quantidade": 2,
    }
    pix = render_label_pixmap(part)
    assert not pix.isNull()
    assert pix.width() == 340
    assert pix.height() == 210

def test_production_html_report(qapp):
    parts = [
        {
            "nome": "Porta Giro",
            "comprimento": 700.0,
            "largura": 395.0,
            "espessura": 18.0,
            "material": "Grafite 18mm",
            "fita_c1": True, "fita_c2": True, "fita_l1": True, "fita_l2": True,
            "quantidade": 2,
        },
        {
            "nome": "Base Balcao",
            "comprimento": 800.0,
            "largura": 550.0,
            "espessura": 15.0,
            "material": "Branco TX 15mm",
            "fita_c1": True, "fita_c2": False, "fita_l1": False, "fita_l2": False,
            "quantidade": 1,
        }
    ]
    html = generate_project_html_report(parts, project_name="Cozinha Gourmet", client_name="Cliente Teste")
    assert "<!DOCTYPE html>" in html
    assert "Cozinha Gourmet" in html
    assert "Grafite 18mm" in html
    assert "Branco TX 15mm" in html
    assert "Relatório Executivo & Orçamento Técnico" in html

def test_wall_elevation_installation_points(qapp):
    dlg = WallElevationDialog(viewport=None)
    assert hasattr(dlg, "chk_inst")
    assert dlg.chk_inst.isChecked()
    assert dlg.canvas.show_instalacoes is True

