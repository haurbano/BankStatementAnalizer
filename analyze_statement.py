import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pdfplumber
import re

# === CONFIGURATION ===
BASE_DIR = Path(__file__).parent
PDF_PATH = BASE_DIR / "Septiembre 2025.pdf"
OUTPUT_JSON_PATH = BASE_DIR / "transactions.json"
OUTPUT_HTML_PATH = BASE_DIR / "dashboard.html"
STATEMENT_LABEL = PDF_PATH.stem

CATEGORY_KEYWORDS = {
    "Comida y restaurantes": ["STARBUCKS", "YOGURT", "AVA", "PIZZA", "CREPES", "PARRILLA", "RESTAURANT", "WOK", "CENADERO", "VENTOLINI", "CARBONES", "CAFÉ", "PANADERIA", "DELIGOURME"],
    "Supermercado": ["EXITO", "CARREFOUR", "SUPERMERCADO"],
    "Servicios": ["EMCALI", "COMCEL", "MOVISTAR"],
    "Salud": ["CLINICA", "CRUZ VERDE", "DROGAS", "OPTICA", "FUNDACION VALLE"],
    "Suscripciones": ["SPOTIFY", "NETFLIX", "APPLE", "YOUTUBE"],
    "Transporte": ["TERPEL", "DIDI", "UBER", "TAXI", "MUBON"],
    "Educación": ["COLEGIO"],
    "Deporte": ["BODYTECH", "PADEL"],
    "Hogar": ["HOMECENTER", "Emcali", "RESIDENCIAL"],
    "Compras": ["aliexpress"],
    "Otros": []  # fallback
}

# === PDF PARSING ===
def extract_transactions(pdf_path: Path) -> pd.DataFrame:
    transactions = []
    pattern = re.compile(r"(\d{4}-\d{2}-\d{2})\s+([A-Z0-9 \*\-]+?)\s+\$([\d\.,]+)")
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            for match in pattern.finditer(text):
                date, desc, amount = match.groups()
                amount = float(amount.replace(".", "").replace(",", "."))
                if amount > 0:  # skip payments
                    transactions.append({
                        "Fecha": date,
                        "Descripción": desc.strip(),
                        "Monto": amount
                    })
    return pd.DataFrame(transactions)

# === CATEGORIZACIÓN ===
def categorize(description):
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in description.upper() for k in keywords):
            return category
    return "Otros"

# === STRUCTURED PAYLOAD ===
def build_payload(df, summary):
    categories_payload = []
    for category in summary.index:
        category_df = (
            df[df["Categoría"] == category]
            .sort_values("Fecha")
            [["Fecha", "Descripción", "Monto"]]
        )
        transactions = [
            {
                "date": row["Fecha"],
                "description": row["Descripción"],
                "amount": round(float(row["Monto"]), 2),
            }
            for row in category_df.to_dict(orient="records")
        ]
        categories_payload.append(
            {
                "name": category,
                "total": round(float(summary[category]), 2),
                "transactions": transactions,
            }
        )

    return {
        "statement": PDF_PATH.stem,
        "generated_at": datetime.now().isoformat(),
        "currency": "COP",
        "overall_total": round(float(summary.sum()), 2),
        "categories": categories_payload,
    }

# === JSON EXPORT ===
def export_to_json(payload, output_path):
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nJSON export saved to {output_path}")

# === HTML EXPORT ===
def export_to_html(payload, output_path):
    payload_json = json.dumps(payload, ensure_ascii=False)
    html_template = """<!DOCTYPE html>
<html lang=\"es\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Resumen de gastos</title>
    <style>
      :root {
        color-scheme: light dark;
        --bg: #f6f8fb;
        --card: #ffffffee;
        --border: #d9dee7;
        --accent: #2563eb;
        --accent-soft: rgba(37, 99, 235, 0.08);
        --text: #101928;
        --text-muted: #4b5565;
        font-family: \"Inter\", system-ui, -apple-system, Segoe UI, sans-serif;
      }

      body {
        margin: 0;
        background: var(--bg);
        color: var(--text);
      }

      h1,
      h2,
      h3,
      h4,
      h5 {
        margin: 0;
        font-weight: 600;
      }

      .page {
        max-width: 1100px;
        margin: 0 auto;
        padding: 32px 24px 48px;
        display: flex;
        flex-direction: column;
        gap: 24px;
      }

      .header {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .header span {
        color: var(--text-muted);
        font-size: 0.95rem;
      }

      .layout {
        display: grid;
        grid-template-columns: minmax(240px, 1fr) 2fr;
        gap: 24px;
      }

      @media (max-width: 900px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }

      .card {
        background: var(--card);
        backdrop-filter: blur(14px);
        border-radius: 16px;
        border: 1px solid var(--border);
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
      }

      .card-header,
      .card-body {
        padding: 20px 24px;
      }

      .card-header {
        border-bottom: 1px solid var(--border);
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .totals {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .totals span {
        font-size: 1rem;
        color: var(--text-muted);
      }

      .total-amount {
        font-size: 1.8rem;
        font-weight: 650;
      }

      .categories-list {
        display: flex;
        flex-direction: column;
        padding: 12px 0;
        gap: 6px;
      }

      .category-item {
        border-radius: 12px;
        border: 1px solid transparent;
        padding: 12px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
        transition: border-color 120ms ease, background 120ms ease, transform 120ms ease;
        background: none;
      }

      .category-item:hover {
        background: var(--accent-soft);
        border-color: rgba(37, 99, 235, 0.2);
        transform: translateY(-1px);
      }

      .category-item.active {
        background: rgba(37, 99, 235, 0.15);
        border-color: rgba(37, 99, 235, 0.4);
        color: var(--accent);
        font-weight: 600;
      }

      .category-meta {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .category-meta small {
        font-size: 0.85rem;
        color: var(--text-muted);
        font-weight: 500;
      }

      .transactions-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.97rem;
      }

      .transactions-table thead {
        text-transform: uppercase;
        letter-spacing: 0.02em;
        font-size: 0.8rem;
        color: var(--text-muted);
      }

      .transactions-table th,
      .transactions-table td {
        text-align: left;
        padding: 12px 16px;
      }

      .transactions-table tbody tr {
        border-top: 1px solid var(--border);
      }

      .transactions-table tbody tr:hover {
        background: rgba(148, 163, 184, 0.12);
      }

      .empty-state {
        text-align: center;
        padding: 32px;
        color: var(--text-muted);
      }

      .chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(37, 99, 235, 0.1);
        color: var(--accent);
        border-radius: 999px;
        padding: 6px 14px;
        font-size: 0.85rem;
        font-weight: 500;
        letter-spacing: 0.01em;
      }

      button.reset {
        margin-left: auto;
        background: none;
        border: none;
        color: var(--accent);
        font-weight: 600;
        cursor: pointer;
        font-size: 0.9rem;
      }

      button.reset:hover {
        text-decoration: underline;
      }
    </style>
  </head>
  <body>
    <main class=\"page\">
      <header class=\"header\">
        <h1>Resumen de gastos</h1>
        <span id=\"statement-label\">Cargando extracto…</span>
      </header>

      <section class=\"layout\">
        <article class=\"card\" id=\"categories-card\">
          <div class=\"card-header\">
            <h2>Categorías</h2>
            <div class=\"totals\">
              <span>Total general</span>
              <span class=\"total-amount\" id=\"overall-total\">—</span>
            </div>
          </div>
          <div class=\"card-body\">
            <div class=\"categories-list\" id=\"categories-list\"></div>
          </div>
        </article>

        <article class=\"card\" id=\"transactions-card\">
          <div class=\"card-header\">
            <div style=\"display: flex; align-items: center; gap: 12px; width: 100%;\">
              <div>
                <h2 id=\"category-title\">Selecciona una categoría</h2>
                <span id=\"category-total\" class=\"chip\" style=\"display: none;\"></span>
              </div>
              <button class=\"reset\" id=\"reset-button\" type=\"button\" style=\"display: none;\">
                Ver todas las transacciones
              </button>
            </div>
          </div>
          <div class=\"card-body\" id=\"transactions-container\">
            <p class=\"empty-state\">Haz clic en una categoría para explorar los detalles.</p>
          </div>
        </article>
      </section>
    </main>

    <script>
      const DATA = __PAYLOAD__;

      const statementLabel = document.getElementById(\"statement-label\");
      const overallTotal = document.getElementById(\"overall-total\");
      const categoriesList = document.getElementById(\"categories-list\");
      const categoryTitle = document.getElementById(\"category-title\");
      const categoryChip = document.getElementById(\"category-total\");
      const transactionsContainer = document.getElementById(\"transactions-container\");
      const resetButton = document.getElementById(\"reset-button\");

      let categoriesData = [];
      let fullTransactionList = [];

      const currencyFormatter = new Intl.NumberFormat(\"es-CO\", {
        style: \"currency\",
        currency: \"COP\",
        maximumFractionDigits: 0,
      });

      const dateFormatter = new Intl.DateTimeFormat(\"es-CO\", {
        year: \"numeric\",
        month: \"short\",
        day: \"2-digit\",
      });

      function formatDate(date) {
        const parsed = new Date(date + \"T00:00:00\");
        if (Number.isNaN(parsed.getTime())) {
          return date;
        }
        return dateFormatter.format(parsed);
      }

      function setActiveCategory(categoryName) {
        categoriesList.querySelectorAll(\".category-item\").forEach((item) => {
          item.classList.toggle(\"active\", item.dataset.category === categoryName);
        });
      }

      function renderTransactions(transactions, headerLabel) {
        if (!transactions.length) {
          transactionsContainer.innerHTML = '<p class=\"empty-state\">No hay transacciones para mostrar.</p>';
          categoryTitle.textContent = headerLabel;
          return;
        }

        const rows = transactions
          .map(
            (tx) =>
              `\n              <tr>\n                <td>${formatDate(tx.date)}</td>\n                <td>${tx.description}</td>\n                <td style=\"text-align:right; font-variant-numeric: tabular-nums;\">\n                  ${currencyFormatter.format(tx.amount)}\n                </td>\n              </tr>\n            `
          )
          .join(\"\");

        transactionsContainer.innerHTML = `\n          <table class=\"transactions-table\">\n            <thead>\n              <tr>\n                <th>Fecha</th>\n                <th>Descripción</th>\n                <th style=\"text-align:right;\">Monto</th>\n              </tr>\n            </thead>\n            <tbody>${rows}</tbody>\n          </table>\n        `;

        categoryTitle.textContent = headerLabel;
      }

      function handleCategoryClick(category) {
        setActiveCategory(category.name);
        categoryChip.style.display = \"inline-flex\";
        categoryChip.textContent = currencyFormatter.format(category.total);
        resetButton.style.display = \"inline-flex\";
        renderTransactions(category.transactions, category.name);
      }

      function renderCategories(categories) {
        categoriesList.innerHTML = categories
          .map(
            (category) =>
              `\n              <button class=\"category-item\" type=\"button\" data-category=\"${category.name}\">\n                <span class=\"category-meta\">\n                  <strong>${category.name}</strong>\n                  <small>${category.transactions.length} transacción${
              category.transactions.length === 1 ? \"\" : \"es\"
            }</small>\n                </span>\n                <span style=\"font-variant-numeric: tabular-nums;\">\n                  ${currencyFormatter.format(category.total)}\n                </span>\n              </button>\n            `
          )
          .join(\"\");

        categoriesList.querySelectorAll(\".category-item\").forEach((button) => {
          button.addEventListener(\"click\", () => {
            const category = categories.find((cat) => cat.name === button.dataset.category);
            if (category) {
              handleCategoryClick(category);
            }
          });
        });
      }

      function renderAllTransactions() {
        setActiveCategory(\"\");
        categoryChip.style.display = \"none\";
        resetButton.style.display = fullTransactionList.length ? \"inline-flex\" : \"none\";
        renderTransactions(fullTransactionList, \"Todas las transacciones\");
      }

      function bootstrap() {
        statementLabel.textContent = `${DATA.statement} · Actualizado ${formatDate((DATA.generated_at || '').slice(0, 10))}`;
        overallTotal.textContent = currencyFormatter.format(DATA.overall_total);

        categoriesData = [...DATA.categories].sort((a, b) => b.total - a.total);
        fullTransactionList = categoriesData.flatMap((category) =>
          category.transactions.map((tx) => ({ ...tx, category: category.name }))
        );

        renderCategories(categoriesData);
        renderAllTransactions();

        resetButton.style.display = categoriesData.length ? \"inline-flex\" : \"none\";
      }

      resetButton.addEventListener(\"click\", () => {
        renderAllTransactions();
      });

      bootstrap();
    </script>
  </body>
</html>
"""

    output_path.write_text(
        html_template.replace("__PAYLOAD__", payload_json), encoding="utf-8"
    )
    print(f"HTML dashboard saved to {output_path}")


# === MAIN ===
df = extract_transactions(PDF_PATH)
if df.empty:
    raise SystemExit("No se encontraron transacciones en el extracto.")

df["Categoría"] = df["Descripción"].apply(categorize)

summary = df.groupby("Categoría")["Monto"].sum().sort_values(ascending=False)

print("=== GASTOS POR CATEGORÍA ===")
print(summary)

payload = build_payload(df, summary)

export_to_json(payload, OUTPUT_JSON_PATH)
export_to_html(payload, OUTPUT_HTML_PATH)

# === PLOT ===
def label_format(pct, allvals):
    absolute = int(round(pct / 100.0 * sum(allvals)))
    return f"{pct:.1f}%\n${absolute:,.0f}"

plt.figure(figsize=(8, 8))
wedges, texts, autotexts = plt.pie(
    summary,
    autopct=lambda pct: label_format(pct, summary),
    startangle=140,
    textprops=dict(color="black", fontsize=9),
)
plt.legend(summary.index, title="Categorías", loc="center left", bbox_to_anchor=(1, 0.5))
plt.title(f"Distribución de gastos - {STATEMENT_LABEL}")
plt.tight_layout()
plt.show()
