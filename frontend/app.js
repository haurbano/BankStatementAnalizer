const API_BASE_URL = "/api";

const form = document.getElementById("upload-form");
const fileInput = document.getElementById("pdf-file");
const errorBanner = document.getElementById("error-banner");
const categoryTitle = document.getElementById("category-title");
const categoryChip = document.getElementById("category-total");
const resetButton = document.getElementById("reset-button");
const categoriesList = document.getElementById("categories-list");
const transactionsContainer = document.getElementById("transactions-container");
const overallTotalEl = document.getElementById("overall-total");
const searchInput = document.getElementById("search-input");
const clearSearchButton = document.getElementById("clear-search");
const passwordDialog = document.getElementById("password-dialog");
const passwordForm = document.getElementById("password-form");
const passwordInput = document.getElementById("password-input");
const passwordHint = document.getElementById("password-hint");
const passwordCancel = document.getElementById("password-cancel");
const statementLabelEl = document.getElementById("statement-label");

const categoryTemplate = document.getElementById("category-item-template");
const tableTemplate = document.getElementById("transactions-table-template");

let categoriesData = [];
let flattenedTransactions = [];
let overallTotal = 0;
let currentCategory = null;
let searchQuery = "";
let pendingFile = null;
let pendingPassword = null;

const currencyFormatter = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

const dateFormatter = new Intl.DateTimeFormat("es-CO", {
  year: "numeric",
  month: "short",
  day: "2-digit",
});

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
  errorBanner.classList.add("error");
}

function clearError() {
  errorBanner.textContent = "";
  errorBanner.classList.add("hidden");
  errorBanner.classList.remove("error");
}

function formatDate(dateString) {
  if (!dateString) return dateString;
  const parsed = new Date(`${dateString}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return dateString;
  return dateFormatter.format(parsed);
}

function setActiveCategory(name) {
  categoriesList.querySelectorAll(".category-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.category === name);
  });
}

function renderTransactions(transactions, label) {
  if (!transactions.length) {
    transactionsContainer.innerHTML = '<p class="empty-state">No hay transacciones para mostrar.</p>';
    categoryTitle.textContent = label;
    return;
  }

  const tableFragment = tableTemplate.content.cloneNode(true);
  const tbody = tableFragment.querySelector("tbody");

  transactions.forEach((tx) => {
    const row = document.createElement("tr");
    const dateCell = document.createElement("td");
    const descriptionCell = document.createElement("td");
    const amountCell = document.createElement("td");

    dateCell.textContent = formatDate(tx.date);
    descriptionCell.textContent = tx.description;
    amountCell.textContent = currencyFormatter.format(tx.amount);
    amountCell.classList.add("numeric");

    row.appendChild(dateCell);
    row.appendChild(descriptionCell);
    row.appendChild(amountCell);

    tbody.appendChild(row);
  });

  transactionsContainer.innerHTML = "";
  transactionsContainer.appendChild(tableFragment);
  categoryTitle.textContent = label;
}

function handleCategorySelection(category) {
  currentCategory = category.name;
  setActiveCategory(category.name);
  categoryChip.textContent = currencyFormatter.format(category.total);
  categoryChip.classList.remove("hidden");
  resetButton.classList.remove("hidden");
  refreshTransactionsView();
}

function renderCategories(categories) {
  categoriesList.innerHTML = "";

  categories.forEach((category) => {
    const node = categoryTemplate.content.cloneNode(true);
    const button = node.querySelector(".category-item");
    const nameEl = node.querySelector(".category-name");
    const countEl = node.querySelector(".category-count");
    const totalEl = node.querySelector(".category-total");

    button.dataset.category = category.name;
    nameEl.textContent = category.name;
    countEl.textContent = `${category.transactions.length} transacción${
      category.transactions.length === 1 ? "" : "es"
    }`;
    totalEl.textContent = currencyFormatter.format(category.total);

    button.addEventListener("click", () => {
      handleCategorySelection(category);
    });

    categoriesList.appendChild(node);
  });
}

function renderAllTransactions() {
  currentCategory = null;
  setActiveCategory("");
  if (categoriesData.length > 0) {
    categoryChip.textContent = currencyFormatter.format(overallTotal);
    categoryChip.classList.remove("hidden");
    resetButton.classList.remove("hidden");
    refreshTransactionsView();
  } else {
    categoryChip.classList.add("hidden");
    resetButton.classList.add("hidden");
    renderTransactions([], "Sin datos");
  }
}

resetButton.addEventListener("click", () => {
  renderAllTransactions();
});

async function submitAnalysis(file, password) {
  const formData = new FormData();
  formData.append("file", file);
  if (password) {
    formData.append("password", password);
  }

  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const error = new Error(payload.detail || "No se pudo procesar el PDF");
    error.status = response.status;
    error.responsePayload = payload;
    throw error;
  }

  return response.json();
}

fileInput.addEventListener("change", async () => {
  clearError();

  const file = fileInput.files?.[0];
  if (!file) {
    return;
  }

  pendingFile = file;
  pendingPassword = null;

  form.classList.add("loading");

  try {
    const data = await submitAnalysis(file, null);
    categoriesData = (data.categories || []).sort((a, b) => b.total - a.total);
    flattenedTransactions = categoriesData.flatMap((category) =>
      category.transactions.map((tx) => ({ ...tx, category: category.name }))
    );

    overallTotal = data.overall_total || 0;
    overallTotalEl.textContent = currencyFormatter.format(overallTotal);
    const monthLabel = data.month ? data.month : data.statement;
    if (statementLabelEl) {
      statementLabelEl.textContent = `${data.statement || "Extracto"} · ${monthLabel}`;
    }
    searchInput.disabled = categoriesData.length === 0;
    searchInput.value = "";
    clearSearchButton.classList.add("hidden");
    searchQuery = "";

    if (categoriesData.length === 0) {
      categoriesList.innerHTML = '<p class="empty-state">No se encontraron gastos.</p>';
      renderAllTransactions();
      return;
    }

    renderCategories(categoriesData);
    handleCategorySelection(categoriesData[0]);
  } catch (error) {
    console.error(error);
    pendingFile = file;
    if (error.status === 401) {
      passwordHint.textContent = error.message;
      passwordInput.value = "";
      pendingPassword = null;
      passwordDialog.showModal();
    } else {
      showError(error.message);
    }
  } finally {
    form.classList.remove("loading");
    form.reset();
  }
});

passwordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearError();
  if (!pendingFile) {
    passwordDialog.close();
    return;
  }

  pendingPassword = passwordInput.value;
  passwordDialog.close();
  form.classList.add("loading");

  try {
    const data = await submitAnalysis(pendingFile, pendingPassword);
    categoriesData = (data.categories || []).sort((a, b) => b.total - a.total);
    flattenedTransactions = categoriesData.flatMap((category) =>
      category.transactions.map((tx) => ({ ...tx, category: category.name }))
    );

    overallTotal = data.overall_total || 0;
    overallTotalEl.textContent = currencyFormatter.format(overallTotal);
    searchInput.disabled = categoriesData.length === 0;
    searchInput.value = "";
    clearSearchButton.classList.add("hidden");
    searchQuery = "";

    if (categoriesData.length === 0) {
      categoriesList.innerHTML = '<p class="empty-state">No se encontraron gastos.</p>';
      renderAllTransactions();
      return;
    }

    renderCategories(categoriesData);
    handleCategorySelection(categoriesData[0]);
  } catch (error) {
    console.error(error);
    if (error.status === 401) {
      passwordHint.textContent = error.message || "Contraseña incorrecta. Intenta nuevamente.";
      passwordInput.value = "";
      passwordDialog.showModal();
    } else {
      showError(error.message);
      pendingFile = null;
    }
  } finally {
    form.classList.remove("loading");
    form.reset();
  }
});

passwordCancel.addEventListener("click", () => {
  pendingFile = null;
  pendingPassword = null;
  passwordDialog.close();
});

function getActiveTransactions() {
  if (currentCategory) {
    const category = categoriesData.find((cat) => cat.name === currentCategory);
    return category ? category.transactions : [];
  }
  return flattenedTransactions;
}

function filterTransactions(transactions, query) {
  if (!query) {
    return transactions;
  }
  const lowerQuery = query.toLowerCase();
  return transactions.filter((tx) => {
    const fields = [tx.description, tx.date, tx.category].join(" ");
    return fields.toLowerCase().includes(lowerQuery);
  });
}

function refreshTransactionsView() {
  const baseTransactions = getActiveTransactions();
  const filtered = filterTransactions(baseTransactions, searchQuery);
  const title = currentCategory || "Todas las transacciones";
  renderTransactions(filtered, searchQuery ? `${title} · resultados` : title);
}

searchInput.addEventListener("input", (event) => {
  searchQuery = event.target.value.trim();
  if (searchQuery) {
    clearSearchButton.classList.remove("hidden");
  } else {
    clearSearchButton.classList.add("hidden");
  }
  refreshTransactionsView();
});

clearSearchButton.addEventListener("click", () => {
  searchQuery = "";
  searchInput.value = "";
  clearSearchButton.classList.add("hidden");
  refreshTransactionsView();
});
