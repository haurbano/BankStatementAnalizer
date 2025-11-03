from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

import pandas as pd
import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect


CONFIG_PATH = Path(__file__).with_name("category_keywords.json")
CURRENCY_CODE = "COP"
PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2})\s+([A-Za-zÀ-ÖØ-öø-ÿ0-9 \*\-]+?)\s+\$([\d\.,]+)"
)
MONTH_PATTERN = re.compile(
    r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)",
    flags=re.IGNORECASE,
)


@dataclass
class AnalysisResult:
    statement: str
    currency: str
    generated_at: str
    overall_total: float
    categories: List[dict]
    month: str | None = None

    def to_dict(self) -> dict:
        return {
            "statement": self.statement,
            "currency": self.currency,
            "generated_at": self.generated_at,
            "overall_total": self.overall_total,
            "categories": self.categories,
            "month": self.month,
        }


def load_category_keywords(path: Path | None = None) -> dict[str, list[str]]:
    target_path = Path(path) if path else CONFIG_PATH
    if not target_path.exists():
        return {"Otros": []}

    try:
        raw_mapping = json.loads(target_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"El archivo de categorías no es un JSON válido: {target_path}"
        ) from exc

    if not isinstance(raw_mapping, dict):
        raise ValueError(
            f"La definición de categorías debe ser un objeto JSON (recibido {type(raw_mapping).__name__})"
        )

    normalized: dict[str, list[str]] = {}
    for category, keywords in raw_mapping.items():
        if not isinstance(keywords, Iterable) or isinstance(keywords, (str, bytes)):
            raise ValueError(
                f"Las palabras clave de la categoría '{category}' deben ser una lista"
            )
        normalized[category] = [str(keyword).upper() for keyword in keywords if keyword]

    normalized.setdefault("Otros", [])
    return normalized


def _normalize_amount(raw_amount: str) -> float:
    cleaned = raw_amount.replace(".", "").replace(",", ".")
    return float(cleaned)


def extract_transactions_from_bytes(
    pdf_bytes: bytes, password: str | None = None
) -> pd.DataFrame:
    """Parse the PDF content and return a DataFrame of transactions."""
    transactions = []
    buffer = io.BytesIO(pdf_bytes)

    detected_month: str | None = None

    try:
        with pdfplumber.open(buffer, password=password or None) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if not detected_month:
                    match_month = MONTH_PATTERN.search(text)
                    if match_month:
                        detected_month = match_month.group(0).title()

                for match in PATTERN.finditer(text):
                    date, desc, amount = match.groups()
                    value = _normalize_amount(amount)
                    if value <= 0:
                        continue
                    transactions.append(
                        {
                            "Fecha": date,
                            "Descripción": desc.strip(),
                            "Monto": value,
                        }
                    )
    except PDFPasswordIncorrect as exc:  # pdf requires password or incorrect password
        message = (
            "Contraseña incorrecta para el PDF proporcionado"
            if password
            else "El PDF está protegido y requiere contraseña"
        )
        raise ValueError(message) from exc
    except Exception as exc:
        raise ValueError("No se pudo leer el PDF proporcionado") from exc

    if not transactions:
        return pd.DataFrame(columns=["Fecha", "Descripción", "Monto"])

    df = pd.DataFrame(transactions)
    df["Fecha"] = pd.to_datetime(df["Fecha"], format="%Y-%m-%d", errors="coerce").dt.strftime(
        "%Y-%m-%d"
    )
    df.attrs["month_label"] = detected_month
    return df


def categorize(description: str, keywords_lookup: dict[str, Iterable[str]]) -> str:
    upper_desc = description.upper()
    for category, keywords in keywords_lookup.items():
        if any(keyword in upper_desc for keyword in keywords):
            return category
    return "Otros"


def append_categories(df: pd.DataFrame, keywords_lookup: dict[str, list[str]]) -> pd.DataFrame:
    categorized = df.copy()
    categorized["Categoría"] = categorized["Descripción"].apply(
        lambda desc: categorize(desc, keywords_lookup)
    )
    return categorized


def build_category_summary(df: pd.DataFrame) -> pd.Series:
    return df.groupby("Categoría")["Monto"].sum().sort_values(ascending=False)


def build_payload(
    df: pd.DataFrame,
    summary: pd.Series,
    statement_label: str,
) -> AnalysisResult:
    categories_payload = []
    for category in summary.index:
        category_rows = (
            df[df["Categoría"] == category]
            .sort_values(["Fecha", "Descripción"], ascending=[True, True])
            [["Fecha", "Descripción", "Monto"]]
        )
        transactions = [
            {
                "date": row["Fecha"],
                "description": row["Descripción"],
                "amount": round(float(row["Monto"]), 2),
            }
            for row in category_rows.to_dict(orient="records")
        ]
        categories_payload.append(
            {
                "name": category,
                "total": round(float(summary[category]), 2),
                "transactions": transactions,
            }
        )

    generated_at = datetime.utcnow().isoformat()
    return AnalysisResult(
        statement=statement_label,
        currency=CURRENCY_CODE,
        generated_at=generated_at,
        overall_total=round(float(summary.sum()), 2),
        categories=categories_payload,
        month=df.attrs.get("month_label"),
    )


def analyze_pdf_bytes(
    pdf_bytes: bytes, statement_label: str, password: str | None = None
) -> AnalysisResult:
    keywords_lookup = load_category_keywords()
    df = extract_transactions_from_bytes(pdf_bytes, password=password)
    if df.empty:
        return AnalysisResult(
            statement=statement_label,
            currency=CURRENCY_CODE,
            generated_at=datetime.utcnow().isoformat(),
            overall_total=0.0,
            categories=[],
        )

    categorized_df = append_categories(df, keywords_lookup)
    summary = build_category_summary(categorized_df)
    return build_payload(categorized_df, summary, statement_label)


def analyze_pdf_file(path: Path, password: str | None = None) -> AnalysisResult:
    pdf_bytes = path.read_bytes()
    return analyze_pdf_bytes(pdf_bytes, statement_label=path.stem, password=password)
