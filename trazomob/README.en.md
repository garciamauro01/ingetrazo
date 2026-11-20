<p align="right">
  <a href="README.md">Português</a> | <b>English</b>
</p>

# TrazoMob — Parametric Cabinetry, Woodworking & 3D Architecture for IngeTrazo

**TrazoMob** is the first-party interior-design and millwork module of the open-source [IngeTrazo CAD 3D](https://github.com/ingelibre/ingetrazo) fork: custom cabinetry, interior design, parametric room modeling, architectural openings (doors and windows), and integrated cutlist optimization. It ships with the fork — it is not a separate plugin.

---

## 🚀 Key Features

### 🪵 1. Parametric Cabinetry Modules
* **Comprehensive Catalog:** Base cabinets, wall/upper units, appliance towers, drawer units, pantries, straight corners, and L-shaped corner cabinets.
* **Standard 1000 × 1000 Corner Dimensions:** The L-corner base unit is square by definition; its dual doors overlap cleanly, with an optional **inner corner stop**.
* **Automatic Sizing & Partitions:** Door cabinets follow ergonomic width sizing rules (standard 400 mm per door), automatically inserting structural center partitions from 3 doors onward.
* **Parametric Countertops:** Straight and L-shaped countertops with customizable thickness build-up (apron/skirt) and backsplashes.
* **Real-Time Millimetric Adjustments:** Direct dynamic editing of width, height, depth, toe-kick recess, and panel thicknesses (15mm, 18mm, 25mm).
* **Interactive 3D Viewport:** Click interactively to open and close swing doors, lift-up flaps, and drawers directly in the 3D scene.

| Kitchen with External Pull Handles & Granite Countertop | Kitchen with Integrated J-Pull Profile & Vertical Stretchers |
| :---: | :---: |
| ![Kitchen with External Pull Handles](docs/images/cozinha_modulos_bancada_viewport.png) | ![Kitchen with J-Pull Profile and Upright Stretchers](docs/images/cozinha_puxador_perfil_travessas_em_pe.png) |
| *External pull handles, granite countertop with undermount sink, and upper cabinets* | *Continuous aluminum J-pull profile (gola) and structural vertical stretchers* |

<p align="center">
  <img src="docs/images/comparativo_travessas_em_pe_vs_deitada.png" alt="Comparison of Structural Stretchers (Vertical Upright vs Flat Horizontal) and Pulls" width="75%">
  <br>
  <em>Construction detail: On the left, base cabinet with upright vertical stretchers and J-pull profile; on the right, base cabinet with flat horizontal stretchers and external pull handles</em>
</p>

### 🧲 2. Magnetic Snapping & Smart Placement
* **Magnetic Wall Snapping:** Modules automatically detect walls, snapping and aligning their back panel flush to the masonry with automatic orientation.
* **Module-to-Module Snapping:** Snap base and wall units side-by-side with automatic magnetic latching and flush front alignment.
* **Elevation Guides & Insertion Frame:** Selecting a wall projects standardized reference guide lines (toe-kick, countertop, wall cabinets) directly on the surface, along with a **3D Snap Frame** (contiguous slot) showing the exact millimetric position of the next adjacent module.
* **Equal Spacing Distribution:** Automatically spaces selected cabinets uniformly across open spans between architectural boundaries.
* **Projected Dynamic Dimensions:** Real-time projected HUD dimension lines (in mm) displaying clear distances to wall corners or adjacent cabinets during mouse drag.
* **Custom Height Guides Editor:** Customize standard elevation guidelines tailored per room type (Kitchen, Bedroom, Bathroom, Office).

<p align="center">
  <img src="docs/images/parede_selecionada_guias_slot_frame.png" alt="Selected Wall with Elevation Reference Guides and Next Module 3D Frame" width="85%">
  <br>
  <em>Inner face of the selected wall with parametric elevation reference lines: existing base cabinet inserted and translucent cyan 3D Frame (armed slot) indicating millimetric positioning for the next module</em>
</p>

### 🧱 3. Smart Walls & 2D Floor Plan
* **Interactive 2D Floor Plan:** Draw closed floor layouts or freestanding wall segments in 2D with customizable thickness and ceiling height.
* **Automated 3D Room Generation:** Instantaneous one-click extrusion of solid, watertight 3D walls, floor slabs, and ceilings.
* **Manifold Solid Geometry:** Mitered corner joints with seamless, watertight geometry and zero internal non-manifold faces.
* **Automatic Wall Fill:** Select a wall face to generate contiguous modular runs that precisely fill the span — **base cabinets**, **drawer units**, or **upper cabinets**. Any remaining clearance is evenly distributed, wrapped in a single undo step.
* **Selective Wall Visibility:** Easily toggle individual wall visibility to inspect and design room interiors without obstruction.

| 2D Floor Plan Builder (Dimensions & Rooms) | Generated 3D Walls & Rooms |
| :---: | :---: |
| ![2D Floor Plan with Dimensions](docs/images/planta_2d_paredes_cotadas.png) | ![Constructed 3D Walls](docs/images/paredes_3d_construidas.png) |
| *2D drafting with dynamic dimensioning, T-junctions, and real-time area calculation* | *Instant 3D solid extrusion with clean miter joints and flooring* |

### 🚪 4. Integrated Openings (Doors & Windows)
* **Automatic Wall Cutouts:** Inserting a door or window automatically carves exact openings into the host wall mesh, maintaining solid, watertight geometry.
* **Jamb & Sill Dimensioning:** HUD projected dimension lines indicate real-time distances to corners, as well as vertical dimensions for windows (sill height, rough opening, header).
* **Live Drag Relocation:** Dragging an opening with the mouse or editing dimensions via the sidebar repositions the wall cutout in real time.
* **Full Undo / Redo (Ctrl+Z):** Fully integrated into IngeTrazo's transaction history — undoing placement or relocation cleanly restores the original solid wall.

<p align="center">
  <img src="docs/images/paredes_3d_com_portas_janelas.png" alt="Automatic Cutouts for Doors and Windows" width="80%">
  <br>
  <em>Room with doors and windows inserted, featuring live automatic wall opening cutouts</em>
</p>

### 💡 5. Decorative & Photometric Lighting
* **LED Strip Channels & Recessed Spots:** Add linear, omni point, and directional spotlight fixtures underneath wall cabinets, panels, and coves, with Kelvin color temperature control (2400K–6500K).
* **3D Target Aiming & Real IES Profiles:** Interactive spotlight aiming directly onto target surfaces in the 3D scene and support for manufacturer `.ies` photometric files.
* **Viewport Light Cones:** Visual cones and direction paths rendered directly in the 3D viewport for precise photometric alignment.

### 📸 6. Photorealistic Rendering & PBR Materials
* **Blender Cycles / EEVEE Integration:** Direct 3D scene export with automatic light-gizmo occlusion exclusion, physical photon tracing, soft sun shadows, and global illumination with denoising.
* **PBR Material Editor & Architectural Shaders:** Control over roughness, bump/normal relief, clearcoat, practical emissive materials (`Emit[...]` and `EmitFake`), and automatic **Thin Glass** shaders for single-face, *reflecta*, and fluted glass.
* **Fast Production Modes:** Batch rendering across all saved scenes (*Batch Render*), ultra-fast selection-only rendering (*Render Selection*), **White Model (*Clay Render*)** mode for lighting studies, and automatic proxy substitution (`_PROXY` → `_HIGHPOLY`).

<p align="center">
  <img src="docs/images/render_ambiente.png" alt="Photorealistic Kitchen Environment Render in TrazoMob" width="90%">
  <br>
  <em>Photorealistic kitchen render produced by TrazoMob featuring PBR materials, physical lighting, and granite countertop reflections</em>
</p>

### 📋 7. Cutlist & Production
* **Comprehensive Parts List:** Automatic panel classification (sides, bottom, shelves, top, stretchers, fronts, and backboards).
* **Edge Banding Management:** Granular edge banding assignment per face (top, bottom, left, right) with thickness presets (0.45mm, 1.0mm, 2.0mm).
* **2D Sheet Cutting Optimizer:** Nesting engine optimizing panel layout on standard sheet boards (e.g. MDF), supporting grain direction, blade kerf, and margin trimming.
* **Interactive Viewer:** Navigate between sheets and materials, with cut/final dimensions, edge banding, drilling and machining drawn directly on each part.
* **Yield & Offcuts:** Each sheet and the whole project report yield (%), usable area, reusable offcuts (≥ 200 × 200 mm) and edge-banding meters.
* **Export:** PDF reports, CSV spreadsheets, sheet diagrams as PNG, and cut plans as **DXF for CNC** with layers and drillings.

<p align="center">
  <img src="docs/images/plano_corte_aproveitamento_sobras.png" alt="2D Cut Plan with Yield and Offcuts" width="90%">
  <br>
  <em>Cut plan viewer: parts nested on the sheet, reusable offcuts highlighted in green, hinge-bore drilling, and yield summaries per material and for the whole project</em>
</p>

### 🏷️ 8. Production Labels with Code 128 & QR
* **Native Barcode and QR:** Every label prints a real **Code 128** (modulo 103 check digit) and a **QR Code**, both drawn by TrazoMob itself — no external dependencies.
* **Stable, Scannable Payload:** The code comes from a deterministic CRC32, so the same part always produces the same code on any machine or run.
* **Complete Part Card:** Name, parent module, final and cut dimensions, material, quantity, edge-banding diagram (C1/C2/L1/L2) and machining summary.
* **Print Ready:** Batch preview and PNG export of every label at higher resolution for thermal or A4 printing.

<p align="center">
  <img src="docs/images/etiquetas_code128_qr.png" alt="Production Labels with Code 128 and QR Code" width="55%">
  <br>
  <em>Shop-floor labels with scannable Code 128, QR Code and per-part edge-banding diagram</em>
</p>

### 🛠️ 9. Assembly Manual
* **Grouped by Module:** The manual organizes parts by module and shows room, floor, part count and hardware.
* **Consolidated Hardware:** One hardware count per module (hinges, slides, handles) instead of repeating it for every part.
* **Machining Instructions:** Every hole, groove or rebate becomes a readable assembly instruction with face, position and diameter.
* **Print-Ready HTML:** Automatically generated document with final and cut dimensions, edge banding and hardware, ready to print or save as PDF.

<p align="center">
  <img src="docs/images/manual_montagem.png" alt="Assembly Manual Grouped by Module" width="70%">
  <br>
  <em>Assembly manual generated from the cutlist, with parts, machining and hardware consolidated per module</em>
</p>

### ⭐ 10. My Modules
* **Save the Current Module:** Store any module configuration (dimensions, doors, drawers, materials and handles) as a personal template in one click.
* **Dedicated Category:** Saved modules appear under **⭐ My Modules**, both in the gallery and as a ribbon tab, ready to insert into the scene again.
* **Local Persistence:** Templates live in the user preferences (`user_modules`) and remain available across sessions and IngeTrazo updates.

<p align="center">
  <img src="docs/images/meus_modulos_ribbon.png" alt="My Modules Tab in the TrazoMob Ribbon" width="95%">
  <br>
  <em><b>⭐ My Modules</b> tab with saved personal templates alongside the static module catalog</em>
</p>

---

## 📦 Installation

TrazoMob ships inside the IngeTrazo fork — **nothing separate to install**.

1. Install the IngeTrazo fork (source or installer package).
2. Launch the application. The **TrazoMob** toolbar and right-dock panel are active automatically.

> The extension manager remains available for third-party extensions.
> TrazoMob, being first-party, does not appear there.

---

## 🛠️ Requirements & Compatibility

* **IngeTrazo CAD 3D:** Version `0.1.0` or higher.
* **Operating System:** Windows 10/11 or Linux.
* **Dependencies:** `PySide6`, `numpy`, `trimesh` (bundled with IngeTrazo).

* **Official Documentation:** See the [TrazoMob Operation Manual (PT)](docs/MANUAL_DE_OPERACAO_TRAZOMOB.md), the [Lighting & Photorealistic Rendering Manual (PT)](docs/MANUAL_ILUMINACAO.md), and the [Architecture Overview (PT)](docs/ARQUITETURA.md).

---

## 📄 License

Distributed under the **GPL-3.0-or-later** license. See the project license file for full terms and conditions.
