# Design

## UI Structure

The frontend is a single HTML page (`static/index.html`) with a fixed sidebar and a main content area. All view transitions happen by rewriting the `#app` div — there is no routing library or page reload.

```
┌─────────────┬──────────────────────────────────────┐
│  Sidebar    │  Main content area (#app)             │
│             │                                       │
│  💰 Finance │  [Page header + month nav]            │
│             │                                       │
│  📊 Dashboard│  [Cards / Tables / Charts]           │
│  💸 Transactions│                                   │
│  📋 Budgets │                                       │
│  🏷️ Categories│                                     │
└─────────────┴──────────────────────────────────────┘
```

## Visual Design

- **Dark theme** — background `#0f1117`, surface `#1a1d27`, border `#2e3248`
- **CSS variables** for all colors — single place to retheme
- **No framework** — one `style.css` file, no build step
- Income is always green (`#22c55e`), expenses red (`#ef4444`), accent indigo (`#6366f1`)
- Budget progress bars shift from indigo → amber → red as spending approaches and exceeds the limit

## State Management

All application state lives in a single `state` object in `app.js`:

```js
const state = {
  page,          // active view
  month, year,   // currently displayed period
  categories,    // full list (all time)
  transactions,  // filtered to current month/year
  budgets,       // filtered to current month/year
  summary,       // aggregated summary for current month/year
  txFilter,      // { category, type } — client-side filter on transactions view
  editTarget,    // record being edited in an open modal (null when closed)
}
```

`loadAll()` fetches all four API endpoints in parallel with `Promise.all` on every month change. The categories list is loaded separately via `loadCategories()` when a category is created/edited, because categories are not month-scoped.

## Pages

### Dashboard
- Three summary cards: income, expenses, net balance
- Donut chart: expense totals per category (Chart.js, `doughnut` type)
- Bar chart: budget vs actual per budgeted expense category (`bar` type)
- Budget progress bars for every expense category that has a budget

### Transactions
- Filterable table (type dropdown + category dropdown, client-side)
- Add/edit modal with type, amount, description, date, category fields
- Category type mismatch is caught both client-side (separate optgroups) and server-side (422)

### Budgets
- Full table of all expense categories showing budget, spent, and remaining
- Categories without a budget show a "Set" button that pre-fills the modal
- Over-budget remaining values shown in red

### Categories
- Card grid — one card per category, showing icon, name, type badge, and color dot
- Color picker uses a palette of 10 preset hex swatches; selected swatch gets a white border ring
- Deleting a category with transactions surfaces the server's 409 as a toast error

## Modals

One shared `#modalOverlay` div. Each action that needs a modal injects its form HTML via `innerHTML`, then adds the `open` class. Clicking the backdrop closes the modal. `state.editTarget` holds the record being edited (null for creates) so `save*()` functions know whether to `POST` or `PUT`.

## Charts

Chart.js is loaded from CDN (`cdn.jsdelivr.net`). Chart instances are stored in module-level variables (`donutChart`, `barChart`) and `.destroy()`-ed before re-rendering to avoid canvas reuse errors when navigating months.

## Error Handling

API errors surface as toast notifications. The `apiFetch` wrapper throws if `!res.ok`, using `data.detail` from FastAPI's error response. Toasts auto-dismiss after 3 seconds and are appended to `document.body` (not a container), so they stack correctly over modals.
