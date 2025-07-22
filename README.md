# TG‑FTIR EGA Web App

Interactive Dash/Plotly application for **Evolved Gas Analysis (EGA)** using **Thermogravimetry (TG) – FTIR coupling**.  
It provides an interactive dashboard to show how the system works, TG curve comparison, and joint TG‑FTIR analysis.

---

## 🔎 Features

- **Home**  
  Two cards with a presentation of the applications and a background image (`tga_ftir.svg`) with three overlaid buttons (FTIR, Transfer line, TG) that open modals.  
  Each modal contains diagrams with clickable floating-circles that display contextual text.

- **TG Comparison**  
  Compare multiple TG runs (mass loss steps, derivative curves, etc.).

- **TG‑FTIR Analysis**  
  Synchronize TG data with FTIR spectra and explore them together.
---

## 📁 Project Structure

| app.py

| tg_ftir_module.py

| requirements.txt

| assets/

|  |___ style.css

|  |___ tga_ftir.svg

|  |___ esquema_ftir.svg

|  |___ diagrama_ftir.svg

|  |___ esquema_tga.svg

|  |___ diagrama_tga.svg

|  |___ descriptions.json

|  pages/

|  |___ home.py

|  |___ tg_comparison.py

|  |___ tg_ftir_analysis.py

---
### Key files

- **`app.py`** – Dash entry point.  
- **`tg_ftir_module.py`** –  
  - `build_buttons_row()` → image + buttons.  
  - `build_modals()` → FTIR/TG/Transfer line modals with floating-circles.  
  - `register_callbacks(app)` → open/close modals and floating-circles text logic.  
- **`pages/home.py`** – Home page layout: intro card + dashboard card + modals.  
- **`assets/style.css`** – Button/floating-circles positioning and styling (including hover effects).  
- **`assets/descriptions.json`** – Text content shown when clicking hotspots.

---

## 🛠 Requirements

- Python ≥ 3.8  
- dash  
- dash-bootstrap-components  
- plotly  
- pandas, numpy  
*(or simply install from `requirements.txt`)*

---

## 🚀 Getting Started

1. **Clone**
   ```bash
   git clone https://github.com/paulacomesanha/TG-FTIR.git
   cd TG-FTIR
