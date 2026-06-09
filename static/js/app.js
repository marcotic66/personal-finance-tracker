// ── State ──────────────────────────────────────────────────────────────────
const state = {
  page: 'dashboard',
  month: new Date().getMonth() + 1,
  year: new Date().getFullYear(),
  categories: [],
  transactions: [],
  budgets: [],
  goals: [],
  summary: null,
  txFilter: { category: '', type: '', startDate: '', endDate: '' },
  editTarget: null,
};

// ── API helpers ────────────────────────────────────────────────────────────
const API = '/api';

async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

const get = (p) => apiFetch(p);
const post = (p, b) => apiFetch(p, { method: 'POST', body: JSON.stringify(b) });
const put = (p, b) => apiFetch(p, { method: 'PUT', body: JSON.stringify(b) });
const del = (p) => apiFetch(p, { method: 'DELETE' });

// ── Toast ──────────────────────────────────────────────────────────────────
function toast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// ── Formatting helpers ─────────────────────────────────────────────────────
const MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December'];

function fmt(amount) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}

function fmtDate(dateStr) {
  const [y, m, d] = dateStr.split('-');
  return `${MONTH_NAMES[parseInt(m) - 1].slice(0, 3)} ${parseInt(d)}, ${y}`;
}

// ── Data loading ──────────────────────────────────────────────────────────
function txQueryParams() {
  const { startDate, endDate } = state.txFilter;
  if (startDate || endDate) {
    const p = new URLSearchParams();
    if (startDate) p.set('start_date', startDate);
    if (endDate)   p.set('end_date', endDate);
    return `?${p}`;
  }
  return `?month=${state.month}&year=${state.year}`;
}

async function loadAll() {
  const [cats, txs, bgets, sum, gls] = await Promise.all([
    get('/categories'),
    get(`/transactions${txQueryParams()}`),
    get(`/budgets?month=${state.month}&year=${state.year}`),
    get(`/summary?month=${state.month}&year=${state.year}`),
    get('/goals'),
  ]);
  state.categories   = cats;
  state.transactions = txs;
  state.budgets      = bgets;
  state.summary      = sum;
  state.goals        = gls;
}

async function loadCategories() {
  state.categories = await get('/categories');
}

async function loadGoals() {
  state.goals = await get('/goals');
}

// ── Navigation ────────────────────────────────────────────────────────────
function navigate(page) {
  state.page = page;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
  render();
}

// ── Month navigation ──────────────────────────────────────────────────────
function prevMonth() {
  if (state.month === 1) { state.month = 12; state.year--; }
  else state.month--;
  refresh();
}

function nextMonth() {
  if (state.month === 12) { state.month = 1; state.year++; }
  else state.month++;
  refresh();
}

async function refresh() {
  await loadAll();
  render();
}

// ── Chart instances ───────────────────────────────────────────────────────
let donutChart = null;
let barChart = null;

// ── Render dispatcher ─────────────────────────────────────────────────────
function render() {
  const app = document.getElementById('app');
  if (state.page === 'dashboard')    renderDashboard(app);
  else if (state.page === 'transactions') renderTransactions(app);
  else if (state.page === 'budgets')      renderBudgets(app);
  else if (state.page === 'goals')        renderGoals(app);
  else if (state.page === 'categories')   renderCategories(app);
}

// ── Comparison chip ───────────────────────────────────────────────────────
function changeChip(pct, lowerIsBetter = false) {
  if (pct === null || pct === undefined) return '';
  const abs = Math.abs(pct).toFixed(1);
  const up = pct >= 0;
  const good = lowerIsBetter ? !up : up;
  const arrow = up ? '▲' : '▼';
  const cls = up ? (good ? 'up-good' : 'up-bad') : (good ? 'down-good' : 'down-bad');
  return `<span class="card-change ${cls}">${arrow} ${abs}% vs last month</span>`;
}

// ── Dashboard ─────────────────────────────────────────────────────────────
function renderDashboard(app) {
  const s = state.summary;
  const net = s ? s.net : 0;

  app.innerHTML = `
    <div class="page-header">
      <div class="page-title">Dashboard</div>
      ${monthNavHTML()}
    </div>

    <div class="cards">
      <div class="card">
        <div class="card-label">Total Income</div>
        <div class="card-value income">${s ? fmt(s.total_income) : '—'}</div>
        ${s ? changeChip(s.income_change_pct, false) : ''}
      </div>
      <div class="card">
        <div class="card-label">Total Expenses</div>
        <div class="card-value expense">${s ? fmt(s.total_expenses) : '—'}</div>
        ${s ? changeChip(s.expense_change_pct, true) : ''}
      </div>
      <div class="card">
        <div class="card-label">Net Balance</div>
        <div class="card-value net ${net >= 0 ? 'positive' : 'negative'}">${s ? fmt(net) : '—'}</div>
      </div>
    </div>

    <div class="two-col">
      <div class="panel">
        <div class="panel-title">Expenses by Category</div>
        <div class="chart-wrap"><canvas id="donutCanvas"></canvas></div>
      </div>
      <div class="panel">
        <div class="panel-title">Budget vs Actual</div>
        <div class="chart-wrap"><canvas id="barCanvas"></canvas></div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-title">
        Budget Status
        <span style="font-size:12px;color:var(--text-muted);font-weight:400">
          ${MONTH_NAMES[state.month - 1]} ${state.year}
        </span>
      </div>
      <div class="budget-list" id="budgetBars"></div>
    </div>
  `;

  renderBudgetBars();
  renderDonut();
  renderBar();
}

function renderBudgetBars() {
  const container = document.getElementById('budgetBars');
  if (!container || !state.summary) return;

  const expenseCats = state.summary.by_category.filter(c => c.type === 'expense' && c.budget !== null);

  if (!expenseCats.length) {
    container.innerHTML = '<div class="empty"><div class="empty-icon">📊</div><p>No budgets set for this month</p></div>';
    return;
  }

  container.innerHTML = expenseCats.map(c => {
    const pct = c.budget ? Math.min((c.total / c.budget) * 100, 100) : 0;
    const over = c.budget && c.total > c.budget;
    const color = over ? 'var(--expense)' : (pct > 80 ? 'var(--warning)' : c.category_color);
    return `
      <div class="budget-item">
        <div class="budget-header">
          <div class="budget-name">${c.category_icon} <span>${c.category_name}</span></div>
          <div class="budget-amounts">
            <span class="${over ? 'over' : ''}">${fmt(c.total)}</span>
            ${c.budget ? ` / ${fmt(c.budget)}` : ''}
          </div>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width:${pct}%;background:${color}"></div>
        </div>
      </div>
    `;
  }).join('');
}

function renderDonut() {
  const canvas = document.getElementById('donutCanvas');
  if (!canvas || !state.summary) return;

  if (donutChart) { donutChart.destroy(); donutChart = null; }

  const data = state.summary.by_category.filter(c => c.type === 'expense' && c.total > 0);
  if (!data.length) {
    canvas.parentElement.innerHTML = '<div class="empty"><div class="empty-icon">🍩</div><p>No expense data</p></div>';
    return;
  }

  donutChart = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: data.map(c => c.category_name),
      datasets: [{
        data: data.map(c => c.total),
        backgroundColor: data.map(c => c.category_color),
        borderWidth: 2,
        borderColor: '#1a1d27',
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#8892a4', boxWidth: 12, padding: 10, font: { size: 11 } },
        },
        tooltip: {
          callbacks: {
            label: ctx => ` ${fmt(ctx.parsed)}`,
          },
        },
      },
      cutout: '65%',
    },
  });
}

function renderBar() {
  const canvas = document.getElementById('barCanvas');
  if (!canvas || !state.summary) return;

  if (barChart) { barChart.destroy(); barChart = null; }

  const data = state.summary.by_category.filter(c => c.type === 'expense' && c.budget !== null);
  if (!data.length) {
    canvas.parentElement.innerHTML = '<div class="empty"><div class="empty-icon">📊</div><p>No budget data</p></div>';
    return;
  }

  barChart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: data.map(c => c.category_name),
      datasets: [
        {
          label: 'Spent',
          data: data.map(c => c.total),
          backgroundColor: data.map(c => c.total > (c.budget || 0) ? '#ef4444' : '#6366f1'),
          borderRadius: 6,
        },
        {
          label: 'Budget',
          data: data.map(c => c.budget),
          backgroundColor: 'rgba(255,255,255,0.06)',
          borderRadius: 6,
          borderWidth: 1,
          borderColor: 'rgba(255,255,255,0.15)',
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#8892a4', font: { size: 11 } } },
        tooltip: { callbacks: { label: ctx => ` ${fmt(ctx.parsed.y)}` } },
      },
      scales: {
        x: { ticks: { color: '#8892a4', font: { size: 10 } }, grid: { display: false } },
        y: {
          ticks: { color: '#8892a4', font: { size: 10 }, callback: v => '$' + v },
          grid: { color: 'rgba(255,255,255,0.04)' },
        },
      },
    },
  });
}

// ── Transactions ──────────────────────────────────────────────────────────
function renderTransactions(app) {
  const { category: catFilter, type: typeFilter, startDate, endDate } = state.txFilter;

  let txs = state.transactions;
  if (catFilter) txs = txs.filter(t => t.category_id === parseInt(catFilter));
  if (typeFilter) txs = txs.filter(t => t.type === typeFilter);

  const catOptions = state.categories.map(c =>
    `<option value="${c.id}" ${catFilter == c.id ? 'selected' : ''}>${c.icon} ${c.name}</option>`
  ).join('');

  // Build CSV export URL from current filters
  const csvParams = new URLSearchParams();
  if (startDate || endDate) {
    if (startDate) csvParams.set('start_date', startDate);
    if (endDate)   csvParams.set('end_date', endDate);
  } else {
    csvParams.set('month', state.month);
    csvParams.set('year', state.year);
  }
  if (catFilter)  csvParams.set('category_id', catFilter);
  if (typeFilter) csvParams.set('type', typeFilter);
  const csvUrl = `/api/transactions/export?${csvParams}`;

  app.innerHTML = `
    <div class="page-header">
      <div class="page-title">Transactions</div>
      ${monthNavHTML()}
    </div>
    <div class="transactions-header">
      <div class="filters">
        <select class="filter-select" id="filterType" onchange="setTxFilter('type', this.value)">
          <option value="">All types</option>
          <option value="income" ${typeFilter === 'income' ? 'selected' : ''}>Income</option>
          <option value="expense" ${typeFilter === 'expense' ? 'selected' : ''}>Expense</option>
        </select>
        <select class="filter-select" id="filterCat" onchange="setTxFilter('category', this.value)">
          <option value="">All categories</option>
          ${catOptions}
        </select>
        <input type="date" class="filter-date" id="filterStart"
          value="${startDate}" title="Start date"
          onchange="setTxFilter('startDate', this.value)">
        <input type="date" class="filter-date" id="filterEnd"
          value="${endDate}" title="End date"
          onchange="setTxFilter('endDate', this.value)">
        ${startDate || endDate ? `<button class="btn btn-ghost" style="padding:6px 10px;font-size:12px" onclick="clearDateFilter()">✕ Clear dates</button>` : ''}
      </div>
      <div style="display:flex;gap:8px">
        <a href="${csvUrl}" download class="btn btn-ghost">⬇ Export CSV</a>
        <button class="btn btn-primary" onclick="openTxModal()">+ Add Transaction</button>
      </div>
    </div>
    <div class="panel">
      <div class="transactions-table-wrap">
        ${txs.length ? `
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Category</th>
                <th>Type</th>
                <th style="text-align:right">Amount</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              ${txs.map(t => `
                <tr>
                  <td style="color:var(--text-muted)">${fmtDate(t.date)}</td>
                  <td>${t.description}</td>
                  <td>
                    <span style="display:inline-flex;align-items:center;gap:5px">
                      <span style="width:8px;height:8px;border-radius:50%;background:${t.category.color};display:inline-block"></span>
                      ${t.category.icon} ${t.category.name}
                    </span>
                  </td>
                  <td><span class="badge ${t.type}">${t.type}</span></td>
                  <td style="text-align:right" class="amount-${t.type}">
                    ${t.type === 'income' ? '+' : '-'}${fmt(t.amount)}
                  </td>
                  <td style="text-align:right;white-space:nowrap">
                    <button class="action-btn" onclick="openTxModal(${t.id})" title="Edit">✏️</button>
                    <button class="action-btn danger" onclick="deleteTransaction(${t.id})" title="Delete">🗑️</button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        ` : `<div class="empty"><div class="empty-icon">💸</div><p>No transactions found for this period</p></div>`}
      </div>
    </div>
  `;
}

async function setTxFilter(key, val) {
  state.txFilter[key] = val;
  // date range changes require a fresh fetch; type/category filter client-side only
  if (key === 'startDate' || key === 'endDate') {
    state.transactions = await get(`/transactions${txQueryParams()}`);
  }
  renderTransactions(document.getElementById('app'));
}

async function clearDateFilter() {
  state.txFilter.startDate = '';
  state.txFilter.endDate = '';
  state.transactions = await get(`/transactions${txQueryParams()}`);
  renderTransactions(document.getElementById('app'));
}

// ── Transaction Modal ─────────────────────────────────────────────────────
function openTxModal(id = null) {
  const tx = id ? state.transactions.find(t => t.id === id) : null;
  state.editTarget = tx;

  const today = new Date().toISOString().split('T')[0];
  const incCats = state.categories.filter(c => c.type === 'income');
  const expCats = state.categories.filter(c => c.type === 'expense');

  const catOpts = (list) => list.map(c =>
    `<option value="${c.id}" ${tx && tx.category_id === c.id ? 'selected' : ''}>${c.icon} ${c.name}</option>`
  ).join('');

  const allCatOpts = `
    <optgroup label="Income">${catOpts(incCats)}</optgroup>
    <optgroup label="Expense">${catOpts(expCats)}</optgroup>
  `;

  document.getElementById('modalOverlay').innerHTML = `
    <div class="modal">
      <div class="modal-title">${tx ? 'Edit Transaction' : 'New Transaction'}</div>
      <div class="form-group">
        <label class="form-label">Type</label>
        <select class="form-select" id="txType">
          <option value="income" ${tx?.type === 'income' ? 'selected' : ''}>Income</option>
          <option value="expense" ${!tx || tx.type === 'expense' ? 'selected' : ''}>Expense</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Amount ($)</label>
        <input class="form-input" type="number" id="txAmount" min="0.01" step="0.01"
          value="${tx ? tx.amount : ''}" placeholder="0.00">
      </div>
      <div class="form-group">
        <label class="form-label">Description</label>
        <input class="form-input" type="text" id="txDesc" value="${tx ? tx.description : ''}" placeholder="What was this?">
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Date</label>
          <input class="form-input" type="date" id="txDate" value="${tx ? tx.date : today}">
        </div>
        <div class="form-group">
          <label class="form-label">Category</label>
          <select class="form-select" id="txCategory">${allCatOpts}</select>
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="saveTx()">Save</button>
      </div>
    </div>
  `;

  document.getElementById('modalOverlay').classList.add('open');
}

async function saveTx() {
  const type = document.getElementById('txType').value;
  const amount = parseFloat(document.getElementById('txAmount').value);
  const description = document.getElementById('txDesc').value.trim();
  const date = document.getElementById('txDate').value;
  const category_id = parseInt(document.getElementById('txCategory').value);

  if (!amount || !description || !date || !category_id) {
    toast('Please fill in all fields', 'error'); return;
  }

  try {
    if (state.editTarget) {
      await put(`/transactions/${state.editTarget.id}`, { amount, description, date, type, category_id });
      toast('Transaction updated');
    } else {
      await post('/transactions', { amount, description, date, type, category_id });
      toast('Transaction added');
    }
    closeModal();
    await refresh();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function deleteTransaction(id) {
  if (!confirm('Delete this transaction?')) return;
  try {
    await del(`/transactions/${id}`);
    toast('Deleted');
    await refresh();
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ── Budgets ───────────────────────────────────────────────────────────────
function renderBudgets(app) {
  const expCats = state.categories.filter(c => c.type === 'expense');
  const budgetMap = {};
  state.budgets.forEach(b => { budgetMap[b.category_id] = b; });

  app.innerHTML = `
    <div class="page-header">
      <div class="page-title">Budgets</div>
      ${monthNavHTML()}
    </div>
    <div class="panel">
      <div class="panel-title">
        Monthly Budgets — ${MONTH_NAMES[state.month - 1]} ${state.year}
        <button class="btn btn-primary" onclick="openBudgetModal()">+ Set Budget</button>
      </div>
      ${expCats.length ? `
        <table>
          <thead>
            <tr>
              <th>Category</th>
              <th style="text-align:right">Budget</th>
              <th style="text-align:right">Spent</th>
              <th style="text-align:right">Remaining</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${expCats.map(cat => {
              const b = budgetMap[cat.id];
              const spent = state.summary?.by_category.find(c => c.category_id === cat.id)?.total || 0;
              const remaining = b ? b.amount - spent : null;
              const over = remaining !== null && remaining < 0;
              return `
                <tr>
                  <td>
                    <span style="display:inline-flex;align-items:center;gap:8px">
                      <span style="width:10px;height:10px;border-radius:50%;background:${cat.color};display:inline-block"></span>
                      ${cat.icon} ${cat.name}
                    </span>
                  </td>
                  <td style="text-align:right">${b ? fmt(b.amount) : '<span style="color:var(--text-muted)">—</span>'}</td>
                  <td style="text-align:right" class="${spent > 0 ? 'amount-expense' : ''}">${spent > 0 ? fmt(spent) : '—'}</td>
                  <td style="text-align:right;${over ? 'color:var(--expense);font-weight:600' : 'color:var(--income)'}">
                    ${remaining !== null ? (over ? '-' : '+') + fmt(Math.abs(remaining)) : '—'}
                  </td>
                  <td style="text-align:right">
                    ${b
                      ? `<button class="action-btn" onclick="openBudgetModal(${b.id})" title="Edit">✏️</button>
                         <button class="action-btn danger" onclick="deleteBudget(${b.id})" title="Delete">🗑️</button>`
                      : `<button class="btn btn-ghost" style="font-size:12px;padding:4px 10px" onclick="openBudgetModal(null,${cat.id})">Set</button>`
                    }
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      ` : '<div class="empty"><div class="empty-icon">📋</div><p>No expense categories yet</p></div>'}
    </div>
  `;
}

function openBudgetModal(id = null, prefillCatId = null) {
  const budget = id ? state.budgets.find(b => b.id === id) : null;
  state.editTarget = budget;

  const expCats = state.categories.filter(c => c.type === 'expense');
  const targetCatId = budget?.category_id || prefillCatId;

  const catOpts = expCats.map(c =>
    `<option value="${c.id}" ${targetCatId == c.id ? 'selected' : ''}>${c.icon} ${c.name}</option>`
  ).join('');

  document.getElementById('modalOverlay').innerHTML = `
    <div class="modal">
      <div class="modal-title">${budget ? 'Edit Budget' : 'Set Budget'}</div>
      <div class="form-group">
        <label class="form-label">Category</label>
        <select class="form-select" id="budgetCat" ${budget ? 'disabled' : ''}>${catOpts}</select>
      </div>
      <div class="form-group">
        <label class="form-label">Budget Amount ($)</label>
        <input class="form-input" type="number" id="budgetAmount" min="1" step="1"
          value="${budget ? budget.amount : ''}" placeholder="0.00">
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Month</label>
          <select class="form-select" id="budgetMonth">
            ${MONTH_NAMES.map((m, i) =>
              `<option value="${i+1}" ${(budget?.month || state.month) == i+1 ? 'selected' : ''}>${m}</option>`
            ).join('')}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Year</label>
          <input class="form-input" type="number" id="budgetYear"
            value="${budget?.year || state.year}" min="2020" max="2035">
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="saveBudget()">Save</button>
      </div>
    </div>
  `;

  document.getElementById('modalOverlay').classList.add('open');
}

async function saveBudget() {
  const category_id = parseInt(document.getElementById('budgetCat').value);
  const amount = parseFloat(document.getElementById('budgetAmount').value);
  const month = parseInt(document.getElementById('budgetMonth').value);
  const year = parseInt(document.getElementById('budgetYear').value);

  if (!amount || !category_id) { toast('Please fill in all fields', 'error'); return; }

  try {
    if (state.editTarget) {
      await put(`/budgets/${state.editTarget.id}`, { amount, month, year });
      toast('Budget updated');
    } else {
      await post('/budgets', { category_id, amount, month, year });
      toast('Budget set');
    }
    closeModal();
    await refresh();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function deleteBudget(id) {
  if (!confirm('Remove this budget?')) return;
  try {
    await del(`/budgets/${id}`);
    toast('Budget removed');
    await refresh();
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ── Goals ─────────────────────────────────────────────────────────────────
function goalDeadlineHTML(deadline) {
  if (!deadline) return '<span class="goal-deadline ok">No deadline</span>';
  const days = Math.ceil((new Date(deadline) - new Date()) / 86400000);
  if (days < 0)  return `<span class="goal-deadline overdue">Overdue by ${Math.abs(days)}d</span>`;
  if (days <= 30) return `<span class="goal-deadline soon">${days} days left</span>`;
  return `<span class="goal-deadline ok">${fmtDate(deadline)}</span>`;
}

function renderGoals(app) {
  app.innerHTML = `
    <div class="page-header">
      <div class="page-title">Savings Goals</div>
      <button class="btn btn-primary" onclick="openGoalModal()">+ New Goal</button>
    </div>
    ${state.goals.length ? `
      <div class="goals-grid">
        ${state.goals.map(g => {
          const pct = Math.min(g.current_amount / g.target_amount * 100, 100);
          const done = g.current_amount >= g.target_amount;
          const color = done ? 'var(--income)' : (pct > 75 ? 'var(--warning)' : 'var(--accent)');
          return `
            <div class="goal-card">
              <div class="goal-header">
                <div>
                  <div class="goal-name">${done ? '✅ ' : '🎯 '}${g.name}</div>
                  ${goalDeadlineHTML(g.deadline)}
                </div>
                <div style="display:flex;gap:4px">
                  <button class="action-btn" onclick="openGoalModal(${g.id})" title="Edit">✏️</button>
                  <button class="action-btn danger" onclick="deleteGoal(${g.id})" title="Delete">🗑️</button>
                </div>
              </div>
              <div class="goal-amounts">
                <span class="goal-current" style="color:${color}">${fmt(g.current_amount)}</span>
                <span class="goal-target">of ${fmt(g.target_amount)}</span>
              </div>
              <div class="progress-bar-bg" style="margin-bottom:6px">
                <div class="progress-bar-fill" style="width:${pct}%;background:${color}"></div>
              </div>
              <div style="display:flex;justify-content:space-between;align-items:center">
                <span class="goal-pct">${pct.toFixed(1)}% saved</span>
                ${!done ? `<span class="goal-pct">${fmt(g.target_amount - g.current_amount)} to go</span>` : ''}
              </div>
              ${!done ? `
                <div class="goal-actions">
                  <button class="btn btn-ghost" style="flex:1;font-size:12px" onclick="openContributeModal(${g.id})">+ Add Funds</button>
                </div>` : ''}
            </div>
          `;
        }).join('')}
      </div>
    ` : `<div class="empty"><div class="empty-icon">🎯</div><p>No savings goals yet — create one to get started</p></div>`}
  `;
}

function openGoalModal(id = null) {
  const goal = id ? state.goals.find(g => g.id === id) : null;
  state.editTarget = goal;

  document.getElementById('modalOverlay').innerHTML = `
    <div class="modal">
      <div class="modal-title">${goal ? 'Edit Goal' : 'New Savings Goal'}</div>
      <div class="form-group">
        <label class="form-label">Goal Name</label>
        <input class="form-input" type="text" id="goalName"
          value="${goal?.name || ''}" placeholder="e.g. Emergency Fund">
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Target Amount ($)</label>
          <input class="form-input" type="number" id="goalTarget" min="1" step="1"
            value="${goal?.target_amount || ''}" placeholder="0.00">
        </div>
        <div class="form-group">
          <label class="form-label">Current Saved ($)</label>
          <input class="form-input" type="number" id="goalCurrent" min="0" step="0.01"
            value="${goal?.current_amount ?? 0}" placeholder="0.00">
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Deadline (optional)</label>
        <input class="form-input" type="date" id="goalDeadline"
          value="${goal?.deadline || ''}">
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="saveGoal()">Save</button>
      </div>
    </div>
  `;

  document.getElementById('modalOverlay').classList.add('open');
}

function openContributeModal(id) {
  const goal = state.goals.find(g => g.id === id);
  if (!goal) return;
  state.editTarget = goal;

  document.getElementById('modalOverlay').innerHTML = `
    <div class="modal">
      <div class="modal-title">Add Funds — ${goal.name}</div>
      <div style="color:var(--text-muted);font-size:13px;margin-bottom:16px">
        Current: ${fmt(goal.current_amount)} &nbsp;/&nbsp; Target: ${fmt(goal.target_amount)}
      </div>
      <div class="form-group">
        <label class="form-label">Amount to Add ($)</label>
        <input class="form-input" type="number" id="contributeAmount" min="0.01" step="0.01" placeholder="0.00">
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="saveContribution()">Add Funds</button>
      </div>
    </div>
  `;

  document.getElementById('modalOverlay').classList.add('open');
}

async function saveGoal() {
  const name = document.getElementById('goalName').value.trim();
  const target_amount = parseFloat(document.getElementById('goalTarget').value);
  const current_amount = parseFloat(document.getElementById('goalCurrent').value) || 0;
  const deadline = document.getElementById('goalDeadline').value || null;

  if (!name || !target_amount) { toast('Name and target amount are required', 'error'); return; }

  try {
    if (state.editTarget) {
      await put(`/goals/${state.editTarget.id}`, { name, target_amount, current_amount, deadline });
      toast('Goal updated');
    } else {
      await post('/goals', { name, target_amount, current_amount, deadline });
      toast('Goal created');
    }
    closeModal();
    await loadGoals();
    renderGoals(document.getElementById('app'));
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function saveContribution() {
  const add = parseFloat(document.getElementById('contributeAmount').value);
  if (!add || add <= 0) { toast('Enter a positive amount', 'error'); return; }

  const goal = state.editTarget;
  const new_amount = Math.min(goal.current_amount + add, goal.target_amount);

  try {
    await put(`/goals/${goal.id}`, { current_amount: new_amount });
    toast(new_amount >= goal.target_amount ? '🎉 Goal reached!' : 'Funds added');
    closeModal();
    await loadGoals();
    renderGoals(document.getElementById('app'));
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function deleteGoal(id) {
  if (!confirm('Delete this savings goal?')) return;
  try {
    await del(`/goals/${id}`);
    toast('Goal deleted');
    await loadGoals();
    renderGoals(document.getElementById('app'));
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ── Categories ────────────────────────────────────────────────────────────
function renderCategories(app) {
  app.innerHTML = `
    <div class="page-header">
      <div class="page-title">Categories</div>
      <button class="btn btn-primary" onclick="openCatModal()">+ New Category</button>
    </div>
    ${state.categories.length ? `
      <div class="cat-grid">
        ${state.categories.map(c => `
          <div class="cat-card">
            <div class="cat-icon">${c.icon}</div>
            <div class="cat-info">
              <div class="cat-name">${c.name}</div>
              <div class="cat-type"><span class="badge ${c.type}">${c.type}</span></div>
            </div>
            <div style="width:10px;height:10px;border-radius:50%;background:${c.color};flex-shrink:0"></div>
            <div class="cat-actions">
              <button class="action-btn" onclick="openCatModal(${c.id})" title="Edit">✏️</button>
              <button class="action-btn danger" onclick="deleteCategory(${c.id})" title="Delete">🗑️</button>
            </div>
          </div>
        `).join('')}
      </div>
    ` : '<div class="empty"><div class="empty-icon">🏷️</div><p>No categories yet</p></div>'}
  `;
}

function openCatModal(id = null) {
  const cat = id ? state.categories.find(c => c.id === id) : null;
  state.editTarget = cat;

  const COLORS = ['#22c55e','#ef4444','#6366f1','#f59e0b','#06b6d4','#ec4899','#8b5cf6','#f97316','#14b8a6','#0ea5e9'];

  document.getElementById('modalOverlay').innerHTML = `
    <div class="modal">
      <div class="modal-title">${cat ? 'Edit Category' : 'New Category'}</div>
      <div class="form-group">
        <label class="form-label">Name</label>
        <input class="form-input" type="text" id="catName" value="${cat?.name || ''}" placeholder="e.g. Groceries">
      </div>
      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Type</label>
          <select class="form-select" id="catType">
            <option value="expense" ${cat?.type !== 'income' ? 'selected' : ''}>Expense</option>
            <option value="income" ${cat?.type === 'income' ? 'selected' : ''}>Income</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Icon (emoji)</label>
          <input class="form-input" type="text" id="catIcon" value="${cat?.icon || '💰'}" placeholder="💰">
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Color</label>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px">
          ${COLORS.map(col => `
            <div onclick="selectColor('${col}')" id="swatch_${col.slice(1)}"
              style="width:28px;height:28px;border-radius:50%;background:${col};cursor:pointer;
                     border:3px solid ${cat?.color === col ? '#fff' : 'transparent'};transition:border 0.1s">
            </div>
          `).join('')}
        </div>
        <input type="hidden" id="catColor" value="${cat?.color || COLORS[0]}">
      </div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="saveCategory()">Save</button>
      </div>
    </div>
  `;

  document.getElementById('modalOverlay').classList.add('open');
}

function selectColor(color) {
  document.querySelectorAll('[id^="swatch_"]').forEach(el => {
    el.style.border = '3px solid transparent';
  });
  document.getElementById(`swatch_${color.slice(1)}`).style.border = '3px solid #fff';
  document.getElementById('catColor').value = color;
}

async function saveCategory() {
  const name = document.getElementById('catName').value.trim();
  const type = document.getElementById('catType').value;
  const icon = document.getElementById('catIcon').value.trim() || '💰';
  const color = document.getElementById('catColor').value;

  if (!name) { toast('Category name is required', 'error'); return; }

  try {
    if (state.editTarget) {
      await put(`/categories/${state.editTarget.id}`, { name, type, icon, color });
      toast('Category updated');
    } else {
      await post('/categories', { name, type, icon, color });
      toast('Category created');
    }
    closeModal();
    await loadCategories();
    await refresh();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function deleteCategory(id) {
  if (!confirm('Delete this category? This will fail if it has transactions.')) return;
  try {
    await del(`/categories/${id}`);
    toast('Category deleted');
    await loadCategories();
    render();
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ── Modal close ───────────────────────────────────────────────────────────
function closeModal() {
  document.getElementById('modalOverlay').classList.remove('open');
  document.getElementById('modalOverlay').innerHTML = '';
  state.editTarget = null;
}

// ── Month nav HTML ────────────────────────────────────────────────────────
function monthNavHTML() {
  return `
    <div class="month-nav">
      <button onclick="prevMonth()">‹</button>
      <span class="month-label">${MONTH_NAMES[state.month - 1]} ${state.year}</span>
      <button onclick="nextMonth()">›</button>
    </div>
  `;
}

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  document.getElementById('modalOverlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('modalOverlay')) closeModal();
  });

  await loadAll();
  navigate('dashboard');
});
