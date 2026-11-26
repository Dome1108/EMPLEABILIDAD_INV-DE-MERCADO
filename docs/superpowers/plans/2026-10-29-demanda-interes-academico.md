# Demanda e interés académico Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fourth top-level Streamlit navigation tab named `Demanda e interés académico` with a styled placeholder view for future matriculados and titulados charts.

**Architecture:** Create an isolated page script at `views/demanda_interes.py` and register it in the existing `st.navigation` list in `app.py`. The new page will reuse the existing palette helpers but will not import, query, or alter any current data logic; its two chart areas will be explicit placeholders until the CSV integration is requested.

**Tech Stack:** Python, Streamlit, existing `palettes.py` helpers, `streamlit.testing.v1.AppTest`, `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-29-demanda-interes-academico-design.md`

## Global Constraints

- The tab must appear in the top navigation beside the three existing views.
- The visible title must be `Demanda e interés académico`.
- This stage must not read CSV files, query SQL, or implement the notebook charts.
- Existing view logic in `views/empleabilidad.py`, `views/carreras.py`, and `views/educacion_continua.py` must remain unchanged.
- Reuse the existing visual language and palette utilities; add no new dependencies.

## Review Focus

- The new page renders without external data or secrets; its smoke test runs `AppTest` directly against the new page.
- The navigation URL is stable and URL-safe: `demanda-interes-academico`.
- The page title and both placeholders remain visible after a fresh Streamlit run.
- Existing dashboard tests continue to pass after registering the new page.
- The new view does not import or mutate current data modules.

### Task 1: Add a failing smoke test for the isolated page

**Files:**
- Create: `tests/test_demanda_interes.py`
- Test: `tests/test_demanda_interes.py`

**Interfaces:**
- Consumes: the future Streamlit page at `views/demanda_interes.py`.
- Produces: a regression test proving the page renders its title and both chart placeholders.

- [ ] **Step 1: Write the failing test**

Create a `unittest.TestCase` that runs `AppTest.from_file` against
`views/demanda_interes.py` and asserts:

```python
app = AppTest.from_file(str(page_path), default_timeout=30).run()
self.assertFalse(app.exception)
self.assertTrue(any("Demanda e interés académico" in item.value for item in app.title))
self.assertTrue(any("Matriculados" in item.value for item in app.subheader))
self.assertTrue(any("Titulados" in item.value for item in app.subheader))
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m unittest tests.test_demanda_interes -v
```

Expected: FAIL because `views/demanda_interes.py` does not exist yet.

### Task 2: Implement the isolated page and register the top tab

**Files:**
- Create: `views/demanda_interes.py`
- Modify: `app.py` in the existing `st.navigation([...])` list only

**Interfaces:**
- Consumes: `PALETTES`, `theme_colors`, and `theme_figure` from `palettes.py` only for visual consistency.
- Produces: a Streamlit page at URL path `demanda-interes-academico` with title `Demanda e interés académico`, and visible `Matriculados` and `Titulados` placeholder panels.

- [ ] **Step 1: Implement the minimal page**

In `views/demanda_interes.py`, render the page title, a short explanatory
caption, and two bordered panels. Each panel must have a subheader with the
exact labels `Matriculados` and `Titulados`, plus a neutral placeholder message
stating that the chart will be connected later. Use the existing blue/vino
palette selected from `st.session_state` and local CSS only; do not load data.

- [ ] **Step 2: Register the page in the top navigation**

Add exactly one `st.Page` entry to the existing list in `app.py`:

```python
st.Page(
    'views/demanda_interes.py',
    title='Demanda e interés académico',
    url_path='demanda-interes-academico',
)
```

Place it after `Empleabilidad y mercado` so it appears beside the existing
top-level tabs without changing any existing page registration.

- [ ] **Step 3: Run the focused smoke test**

Run:

```powershell
python -m unittest tests.test_demanda_interes -v
```

Expected: PASS with no Streamlit exception.

### Task 3: Verify the existing application and the new top navigation

**Files:**
- Modify: none
- Test: existing `tests/test_app.py` and `tests/` suite

**Interfaces:**
- Consumes: the registered page and the existing dashboard test suite.
- Produces: fresh verification evidence that current pages still behave as before and the new page can be opened from the top navigation.

- [ ] **Step 1: Run the complete existing test suites**

Run:

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s viabilidad/tests -v
```

Expected: both commands exit with code 0 and report no failures.

- [ ] **Step 2: Run a Streamlit smoke check**

Start the app from the project root:

```powershell
python -m streamlit run app.py --server.headless true --server.port 8501
```

Open `http://localhost:8501`, confirm the top bar shows the new tab beside the
existing tabs, open it, and confirm both `Matriculados` and `Titulados` panels
are visible. Stop the process after the check.

- [ ] **Step 3: Review the diff**

Run:

```powershell
git diff -- app.py views/demanda_interes.py tests/test_demanda_interes.py
```

Confirm the diff contains only the one navigation registration, the new
isolated page, and its smoke test; no current view logic or CSV handling has
been changed.
