"""Reglas por persona y corte. No depende de Streamlit ni de SQL Server."""
from dataclasses import dataclass
import calendar
import re
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

RESULT_SCHEMA_VERSION = 4


@dataclass(frozen=True)
class Snapshot:
    year: int
    month: int
    table: str
    salary_columns: tuple[str, ...]

    @property
    def date(self):
        return pd.Timestamp(self.year, self.month, calendar.monthrange(self.year, self.month)[1])

    @property
    def label(self):
        return f"{['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo'][self.month]} {self.year}"


SNAPSHOTS = (
    Snapshot(2023, 2, "APOR_Y_FEB_23", ("SALARIO",)),
    Snapshot(2024, 5, "APOR_Y_MAY_24", ("SALARIO_TOTAL", "SALARIO_FIJO")),
    Snapshot(2025, 1, "APOR_Y_ENE_25", ("SALARIO_TOTAL", "SALARIO_FIJO")),
    Snapshot(2026, 1, "SIM_Y_ENE_26", ("SALARIO",)),
)

PRIVATE_SIERRA = {
    "UNIVERSIDAD TECNICA PARTICULAR DE LOJA": "UTPL",
    "PONTIFICIA UNIVERSIDAD CATOLICA DEL ECUADOR": "PUCE",
    "UNIVERSIDAD POLITECNICA SALESIANA": "UPS",
    "UNIVERSIDAD DE LAS AMERICAS": "UDLA",
    "UNIVERSIDAD CATOLICA DE CUENCA": "UCACUE",
    "UNIVERSIDAD TECNOLOGICA INDOAMERICA": "UTI",
    "UNIVERSIDAD SAN FRANCISCO DE QUITO": "USFQ",
    "UNIVERSIDAD REGIONAL AUTONOMA DE LOS ANDES": "UNIANDES",
    "UNIVERSIDAD UTE": "UTE",
    "UNIVERSIDAD INTERNACIONAL DEL ECUADOR": "UIDE",
    "UNIVERSIDAD DEL AZUAY": "UAZUAY",
    "UNIVERSIDAD DE LOS HEMISFERIOS": "UHE",
    "UNIVERSIDAD PARTICULAR INTERNACIONAL SEK": "UISEK",
    "UNIVERSIDAD TECNOLOGICA ISRAEL": "UISRAEL",
    "UNIVERSIDAD DE OTAVALO": "UOTAVALO",
    "UNIVERSIDAD METROPOLITANA": "UMET",
    "UNIVERSIDAD IBEROAMERICANA DEL ECUADOR": "UNIBE",
    "UNIVERSIDAD DE ESPECIALIDADES TURISTICAS": "UDET",
}


def institution_key(value):
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


PRIVATE_ALIASES = {institution_key(name): code for name, code in PRIVATE_SIERRA.items()}
PRIVATE_ALIASES.update({code: code for code in PRIVATE_SIERRA.values()})
PRIVATE_ALIASES.update({
    "UNIVERSIDAD TECNOLOGICA EQUINOCCIAL": "UTE",
    "UNIVERSIDAD INTERNACIONAL SEK": "UISEK",
})


def normalize_id(value):
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    if not re.fullmatch(r"[0-9]{1,10}", value):
        return None
    return value.zfill(10)


def sri_status(row, cutoff):
    """Vigencia inferida con último inicio/suspensión/reinicio; sin historial completo."""
    start = row.get("FECHA_INICIO_ACTIVIDADES", pd.NaT)
    suspension = row.get("FECHA_SUSPENSION_DEFINITIVA", pd.NaT)
    restart = row.get("FECHA_REINICIO_ACTIVIDADES", pd.NaT)
    current = str(row.get("ESTADO_CONTRIBUYENTE", "")).strip().upper()
    if pd.isna(start):
        return "Indeterminado"
    if start > cutoff:
        return "Inactivo"
    if pd.notna(restart) and restart < start:
        return "Indeterminado"
    if pd.notna(suspension) and suspension < start:
        return "Indeterminado"
    if pd.notna(suspension) and suspension <= cutoff:
        if pd.notna(restart) and suspension < restart <= cutoff:
            return "Activo"
        return "Inactivo"
    if pd.notna(restart) and restart > cutoff:
        # La última suspensión puede ser posterior al último reinicio:
        # falta el evento que originó ese reinicio; no inventar ese intervalo.
        if pd.isna(suspension) or suspension >= restart:
            return "Indeterminado"
    if pd.notna(suspension) and suspension > cutoff:
        return "Activo"
    if pd.notna(restart) and restart <= cutoff:
        return "Activo" if current == "ACTIVO" else "Indeterminado"
    return "Activo" if current == "ACTIVO" else "Indeterminado"


def calculate(graduates, employment, sri, as_of=None):
    grads = graduates.copy()
    grads["person"] = grads["IDENTIFICACION"].map(normalize_id)
    grads["FECHA_REGISTRO"] = pd.to_datetime(grads["FECHA_REGISTRO"], errors="coerce")
    invalid_ids = int(grads["person"].isna().sum())
    invalid_dates = int(grads["FECHA_REGISTRO"].isna().sum())
    grads = grads.dropna(subset=["person", "FECHA_REGISTRO"])
    grads["INSTITUCION_EDUCACION_SUPERIOR"] = grads["INSTITUCION_EDUCACION_SUPERIOR"].fillna("Sin institución")
    grads["private_code"] = grads["INSTITUCION_EDUCACION_SUPERIOR"].map(institution_key).map(PRIVATE_ALIASES)
    # Educación 2026 utiliza todo el año disponible sin alterar cohortes laborales.
    as_of = pd.Timestamp(as_of or datetime.now(ZoneInfo("America/Guayaquil")).date()).normalize()
    current = grads[grads["FECHA_REGISTRO"].dt.year.eq(2026) & (grads["FECHA_REGISTRO"] <= as_of)]
    current_cutoff = current["FECHA_REGISTRO"].max()
    tax = sri.copy()
    for col in ("FECHA_INICIO_ACTIVIDADES", "FECHA_SUSPENSION_DEFINITIVA", "FECHA_REINICIO_ACTIVIDADES", "FECHA_CARGA", "FECHA_ACTUALIZACION"):
        tax[col] = pd.to_datetime(tax[col], errors="coerce")
    tax["NUMERO_RUC"] = tax["NUMERO_RUC"].astype(str).str.strip()
    tax = tax.sort_values(["FECHA_CARGA", "FECHA_ACTUALIZACION"], na_position="first").drop_duplicates("NUMERO_RUC", keep="last")
    results, summaries, institutions, private_institutions = {}, [], [], []
    for snapshot in SNAPSHOTS:
        cohort = grads[grads["FECHA_REGISTRO"] <= snapshot.date]
        academic_limit = as_of if snapshot.year == 2026 else snapshot.date
        academic = grads[grads["FECHA_REGISTRO"] <= academic_limit]
        academic_recent = academic[academic["FECHA_REGISTRO"].dt.year.eq(snapshot.year)]
        academic_cutoff = academic["FECHA_REGISTRO"].max() if snapshot.year == 2026 else snapshot.date
        people = cohort.groupby("person").agg(first_registration=("FECHA_REGISTRO", "min")).reset_index()
        jobs = employment[snapshot.year].copy()
        jobs["person"] = jobs["NUMAFI"].map(normalize_id)
        jobs["salary"] = pd.to_numeric(jobs["salary"], errors="coerce")
        jobs.loc[jobs["salary"] <= 0, "salary"] = np.nan
        # Una observación por empleador; evita multiplicar filas duplicadas.
        jobs["RUCEMP"] = jobs["RUCEMP"].fillna("Sin empleador").astype(str).str.strip()
        salaries = jobs.groupby(["person", "RUCEMP"])["salary"].max().groupby("person").sum(min_count=1)
        people = people.merge(salaries.rename("salary"), on="person", how="left")
        people["dependent"] = people["person"].isin(jobs["person"].dropna())
        people["ruc"] = people["person"] + "001"
        statuses = {row["NUMERO_RUC"]: sri_status(row, snapshot.date) for _, row in tax.iterrows()}
        people["sri_status"] = people["ruc"].map(statuses).fillna("No encontrado")
        people["status"] = np.select(
            [people["dependent"], people["sri_status"].eq("Activo")],
            ["Dependientes", "Independientes"], default="Sin información laboral")
        people["visible"] = people["status"].ne("Sin información laboral")
        n = len(people)
        employed = int(people["visible"].sum())
        salary = people.loc[people["dependent"], "salary"].dropna()
        counts = people["status"].value_counts()
        summaries.append(dict(year=snapshot.year, cutoff=snapshot.date.date(), label=snapshot.label,
            graduates=n, employed=employed, rate=100 * employed/n if n else np.nan,
            dependent=int(counts.get("Dependientes", 0)), independent=int(counts.get("Independientes", 0)),
            unknown=int(counts.get("Sin información laboral", 0)),
            sri_uncertain=int((people["sri_status"].eq("Indeterminado") & ~people["dependent"]).sum()),
            p25=salary.quantile(.25), p75=salary.quantile(.75), salary_n=len(salary),
            recent=int(academic_recent["person"].nunique()),
            academic_cutoff=academic_cutoff.date().isoformat() if pd.notna(academic_cutoff) else None))
        # Una persona puede haber estudiado en varias instituciones; dentro de cada una cuenta una vez.
        inst = academic.groupby("INSTITUCION_EDUCACION_SUPERIOR").agg(professionals=("person", "nunique"))
        recent = academic_recent.groupby("INSTITUCION_EDUCACION_SUPERIOR")["person"].nunique()
        inst["recent"] = recent.reindex(inst.index).fillna(0).astype(int)
        institutions.append(inst.reset_index().assign(year=snapshot.year))
        private = academic.dropna(subset=["private_code"])
        totals = private.groupby("private_code")["person"].nunique()
        recent_private = private[private["FECHA_REGISTRO"].dt.year.eq(snapshot.year)].groupby("private_code")["person"].nunique()
        for name, code in PRIVATE_SIERRA.items():
            private_institutions.append(dict(year=snapshot.year, institution=name, code=code,
                professionals=int(totals.get(code, 0)), recent=int(recent_private.get(code, 0))))
        results[snapshot.year] = people
    quality = dict(invalid_ids=invalid_ids, invalid_dates=invalid_dates,
        recent_2026=int(current["person"].nunique()),
        recent_2026_cutoff=current_cutoff.date().isoformat() if pd.notna(current_cutoff) else None,
        private_institutions=private_institutions)
    return pd.DataFrame(summaries), pd.concat(institutions, ignore_index=True), results, quality
