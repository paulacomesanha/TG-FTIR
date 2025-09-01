# DATA MANAGER — TG / EGA Dashboard (Dash)

A multi-page **Plotly-Dash** app to load, explore, and compare **Thermogravimetric (TG)** and **Evolved Gas Analysis (TG-FTIR / EGA)** data.  
It includes a collapsible sidebar, unified legend with per-trace visibility, **Walkthrough** buttons that preload example files, and an **FTIR expert chat** powered by OpenAI.

---

## ✨ Features

- **Home**
  - Intro card and a TG-FTIR system section with modals (FTIR, TG, Transfer line) to show how the system works.
- **Thermogravimetric Analysis** (`/tg-comparison`)
  - Upload **multiple TG CSVs** and compare.
  - Plots: temperature program, **normalized DTG**, **normalized TG**.
  - Unified legend with “eye” toggles.
  - **Walkthrough** button that auto-loads two demo CSVs.
- **Evolved Gas Analysis (EGA)** (`/tg-ftir-analysis`)
  - Upload **TG (CSV)**, **GS (XLSX)**, and **FTIR (CSV)**.
  - Plots: TG% + d(TG)/dT, time vs. temperature (with a draggable red time marker), FTIR spectrum (wavenumber axis reversed).
  - “**Set spectrum**” to pin spectra, with removable badges.
  - **Walkthrough** button that auto-loads three demo files (TG/GS/FTIR).
  - **Expert chat** that interprets the current FTIR spectrum (needs `OPENAI_API_KEY`).

---

## 🗂 Project Structure
```
project/
├─ app.py                         # App shell, sidebar, layout
├─ pages/
│  ├─ home.py                     # Landing + TG-FTIR system buttons and modals
│  ├─ tg_comparison.py            # Thermogravimetric Analysis page
│  └─ tg_ftir_analysis.py         # EGA (TG-FTIR) page
├─ home_dashboard.py              # Modal builders + callbacks used on Home
├─ assets/
│  ├─ descriptions.json
│  ├─ tga_ftir.svg
│  ├─ esquema_ftir.svg
│  ├─ diagrama_ftir.svg
│  ├─ esquema_tga.svg
│  ├─ diagrama_tga.svg
│  └─ walkthrough/                # Put your demo files here
│     ├─ TG_100CO_R10R5_W6.csv
│     ├─ TG_80CO-20ES_R10R5_W6.csv
│     ├─ TG_example.csv
│     ├─ GS_example.xlsx
│     └─ FTIR_example.csv
└─ .env                           # OPENAI_API_KEY (optional)
```

Dash automatically serves everything inside `assets/`.

---

## ⚙️ Requirements

- Python **3.10+** recommended.

```bash
pip install dash dash-bootstrap-components dash-mantine-components plotly \
            pandas numpy scipy python-dotenv openai
```
  
  Font Awesome is referenced via CDN in `app.py` for icons.

---

## 🔐 Environment (optional)

Create a `.env` if you want to enable the **FTIR expert chat**:
```ini
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
```

If not set, the chat panel stays hidden.

---

## ▶️ Run

From the project root:

```bash
python app.py
```

The app finds a free port and opens your browser automatically (e.g., `http://127.0.0.1:PORT/`).

---

## 📥 Data Formats

**TG CSV (used in both pages)**

Expected columns (by index):

  - `time` at **col 0** (minutes; converted to seconds as time*60 in EGA),

  - `mass` at **col 1** (mg),

  - `program temperature` at **col 3** (°C),

  - `sample temperature` at **col 4** (°C).

In **TG Comparison**, if the file has ≥ **5 columns**, it uses **col 4** as `Temperature` and **col 1** as `Mass`.
If fewer, it falls back to **col 0** as generic `X_Value` and **col 1** as `Mass`.

**GS XLSX (EGA only)**

  - Read with `pandas.read_excel(..., skiprows=4)`.

  - Uses **col 0** as time (s) and **col 1** as signal.

**FTIR CSV (EGA only)**

  - Parsed with **semicolon** (`;`) delimiter.

  - All commas are converted to dots (`str.replace(',', '.')`) then cast to float.

  - The file is transposed so time ends up in a column named `Time (s)`, and **wavenumbers** are the remaining columns.

---

## 🧭 Walkthrough (demo files)

Both pages include a **Walkthrough** button (next to the Refresh icon) that preloads local demo files.

  - **TG Comparison** (`pages/tg_comparison.py`): edit `WALKTHROUGH_FILES` to point to your two CSVs.

  - **EGA** (`pages/tg_ftir_analysis.py`): edit `EGA_WALKTHROUGH` to point to your TG CSV, GS XLSX, and FTIR CSV.

Example (EGA):

```python
BASE_DIR = Path(__file__).resolve().parents[1]
EGA_WALKTHROUGH = {
    "tg":   {"label": "TG_example.csv",   "path": BASE_DIR / "assets" / "walkthrough" / "TG_example.csv",   "mime": "text/csv"},
    "gs":   {"label": "GS_example.xlsx",  "path": BASE_DIR / "assets" / "walkthrough" / "GS_example.xlsx",  "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    "ftir": {"label": "FTIR_example.csv", "path": BASE_DIR / "assets" / "walkthrough" / "FTIR_example.csv", "mime": "text/csv"},
}
```

  If any file is missing, the Walkthrough does nothing (to avoid breaking the flow).

---

## 🛠 Troubleshooting

**Nothing happens on Walkthrough**:

  - Check the paths in `WALKTHROUGH_FILES` / `EGA_WALKTHROUGH`.

  - Ensure files exist under `assets/walkthrough/`.

**FTIR CSV not read**

  - It expects `;`(semicolon) delimiter and decimals with `,`or `.` (commas are converted).

**Graphs don't appear**

  - EGA requires **all three** files (TG/GS/FTIR). TG Comparison requires at least one CSV.

**OpenAI error in chat**

  - Set `OPENAI_API_KEY` in `.env` and restart the app.
