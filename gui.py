"""Desktop GUI for the Personal Finance Tracker — connects to the REST API."""
import queue
import threading
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import messagebox, ttk

import requests
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

BASE_URL = "http://localhost:8000/api"

COLORS = {
    "bg":         "#0f1117",
    "surface":    "#1a1d27",
    "surface2":   "#22263a",
    "border":     "#2e3248",
    "text":       "#e2e8f0",
    "muted":      "#8892a4",
    "accent":     "#6366f1",
    "income":     "#22c55e",
    "expense":    "#ef4444",
    "warning":    "#f59e0b",
}

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ── API client ─────────────────────────────────────────────────────────────

class ApiClient:
    def __init__(self):
        self._s = requests.Session()
        self._s.headers["Content-Type"] = "application/json"

    def _get(self, path, **params):
        r = self._s.get(BASE_URL + path, params={k: v for k, v in params.items() if v is not None}, timeout=8)
        r.raise_for_status()
        return r.json()

    def _post(self, path, payload):
        r = self._s.post(BASE_URL + path, json=payload, timeout=8)
        r.raise_for_status()
        return r.json()

    def _put(self, path, payload):
        r = self._s.put(BASE_URL + path, json=payload, timeout=8)
        r.raise_for_status()
        return r.json()

    def _delete(self, path):
        r = self._s.delete(BASE_URL + path, timeout=8)
        r.raise_for_status()

    def get_categories(self):           return self._get("/categories/")
    def get_transactions(self, m, y):   return self._get("/transactions/", month=m, year=y)
    def get_budgets(self, m, y):        return self._get("/budgets/", month=m, year=y)
    def get_summary(self, m, y):        return self._get("/summary/", month=m, year=y)
    def get_goals(self):                return self._get("/goals/")

    def create_transaction(self, p):    return self._post("/transactions/", p)
    def update_transaction(self, i, p): return self._put(f"/transactions/{i}", p)
    def delete_transaction(self, i):    return self._delete(f"/transactions/{i}")

    def create_budget(self, p):         return self._post("/budgets/", p)
    def update_budget(self, i, p):      return self._put(f"/budgets/{i}", p)
    def delete_budget(self, i):         return self._delete(f"/budgets/{i}")


# ── App state ──────────────────────────────────────────────────────────────

@dataclass
class AppState:
    month: int = field(default_factory=lambda: __import__("datetime").date.today().month)
    year: int  = field(default_factory=lambda: __import__("datetime").date.today().year)
    categories: list = field(default_factory=list)
    transactions: list = field(default_factory=list)
    budgets: list = field(default_factory=list)
    goals: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)


# ── Helpers ────────────────────────────────────────────────────────────────

def fmt(amount):
    return f"${amount:,.2f}"


def fmt_date(date_str):
    y, m, d = date_str.split("-")
    return f"{MONTH_NAMES[int(m)-1][:3]} {int(d)}, {y}"


def _api_error(exc):
    """Extract a readable message from a requests exception."""
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            return exc.response.json().get("detail", str(exc))
        except Exception:
            pass
    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        return "Cannot reach the server. Is it running?\n\nuv run uvicorn main:app --reload"
    return str(exc)


# ── Modal dialogs ──────────────────────────────────────────────────────────

class _BaseDialog(tk.Toplevel):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.withdraw()
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.title(title)
        self.configure(bg=COLORS["surface"])
        self.result = None
        self._build()
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width()  - self.winfo_width())  // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
        self.deiconify()
        self.wait_window()

    def _build(self): pass

    def _field(self, parent, label, row, widget_factory):
        lbl = tk.Label(parent, text=label, bg=COLORS["surface"],
                       fg=COLORS["muted"], font=("TkDefaultFont", 9))
        lbl.grid(row=row, column=0, sticky="w", padx=(16, 8), pady=(8, 0))
        widget = widget_factory(parent)
        widget.grid(row=row+1, column=0, sticky="ew", padx=16, pady=(2, 0))
        return widget

    def _entry(self, parent):
        e = ttk.Entry(parent, style="Dark.TEntry")
        return e

    def _combo(self, parent, values, readonly=True):
        c = ttk.Combobox(parent, values=values,
                         state="readonly" if readonly else "normal",
                         style="Dark.TCombobox")
        return c

    def _buttons(self, parent):
        f = tk.Frame(parent, bg=COLORS["surface"])
        f.grid(row=99, column=0, sticky="ew", padx=16, pady=16)
        f.columnconfigure(0, weight=1)
        ttk.Button(f, text="Cancel", style="Ghost.TButton",
                   command=self.destroy).grid(row=0, column=0, sticky="e", padx=(0, 8))
        ttk.Button(f, text="Save", style="Accent.TButton",
                   command=self._save).grid(row=0, column=1, sticky="e")

    def _save(self): pass


class TransactionDialog(_BaseDialog):
    def __init__(self, parent, categories, transaction=None):
        self._cats = categories
        self._tx = transaction
        title = "Edit Transaction" if transaction else "New Transaction"
        super().__init__(parent, title)

    def _build(self):
        f = tk.Frame(self, bg=COLORS["surface"])
        f.grid(row=0, column=0, sticky="nsew")
        f.columnconfigure(0, weight=1)

        self._type_var = tk.StringVar(value=self._tx["type"] if self._tx else "expense")
        self._type_cb = self._field(f, "Type", 0,
            lambda p: self._combo(p, ["expense", "income"]))
        self._type_cb.set(self._type_var.get())
        self._type_cb.bind("<<ComboboxSelected>>", self._on_type_change)

        self._amount_entry = self._field(f, "Amount ($)", 2, lambda p: self._entry(p))
        if self._tx:
            self._amount_entry.insert(0, str(self._tx["amount"]))

        self._desc_entry = self._field(f, "Description", 4, lambda p: self._entry(p))
        if self._tx:
            self._desc_entry.insert(0, self._tx["description"])

        self._date_entry = self._field(f, "Date (YYYY-MM-DD)", 6, lambda p: self._entry(p))
        self._date_entry.insert(0, self._tx["date"] if self._tx else
                                __import__("datetime").date.today().isoformat())

        self._cat_names, self._cat_ids = self._filtered_cats(self._type_var.get())
        self._cat_cb = self._field(f, "Category", 8,
            lambda p: self._combo(p, self._cat_names))
        if self._tx:
            for i, cid in enumerate(self._cat_ids):
                if cid == self._tx["category_id"]:
                    self._cat_cb.current(i)
                    break
        elif self._cat_names:
            self._cat_cb.current(0)

        self._buttons(f)

    def _filtered_cats(self, type_):
        filtered = [c for c in self._cats if c["type"] == type_]
        names = [f"{c['icon']} {c['name']}" for c in filtered]
        ids   = [c["id"] for c in filtered]
        return names, ids

    def _on_type_change(self, _=None):
        t = self._type_cb.get()
        names, ids = self._filtered_cats(t)
        self._cat_names, self._cat_ids = names, ids
        self._cat_cb["values"] = names
        if names:
            self._cat_cb.current(0)

    def _save(self):
        try:
            amount = float(self._amount_entry.get())
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError as e:
            messagebox.showerror("Validation", str(e), parent=self)
            return
        desc = self._desc_entry.get().strip()
        date = self._date_entry.get().strip()
        if not desc or not date:
            messagebox.showerror("Validation", "Description and date are required.", parent=self)
            return
        cat_idx = self._cat_cb.current()
        if cat_idx < 0:
            messagebox.showerror("Validation", "Please select a category.", parent=self)
            return
        self.result = {
            "amount": amount,
            "description": desc,
            "date": date,
            "type": self._type_cb.get(),
            "category_id": self._cat_ids[cat_idx],
        }
        self.destroy()


class BudgetDialog(_BaseDialog):
    def __init__(self, parent, categories, budget=None, prefill_cat_id=None, month=None, year=None):
        self._cats = [c for c in categories if c["type"] == "expense"]
        self._budget = budget
        self._prefill_cat_id = prefill_cat_id
        self._default_month = month
        self._default_year  = year
        title = "Edit Budget" if budget else "Set Budget"
        super().__init__(parent, title)

    def _build(self):
        f = tk.Frame(self, bg=COLORS["surface"])
        f.grid(row=0, column=0, sticky="nsew")
        f.columnconfigure(0, weight=1)

        cat_names = [f"{c['icon']} {c['name']}" for c in self._cats]
        cat_ids   = [c["id"] for c in self._cats]
        self._cat_ids = cat_ids

        self._cat_cb = self._field(f, "Category", 0, lambda p: self._combo(p, cat_names))
        if self._budget:
            for i, cid in enumerate(cat_ids):
                if cid == self._budget["category_id"]:
                    self._cat_cb.current(i); break
            self._cat_cb.config(state="disabled")
        elif self._prefill_cat_id:
            for i, cid in enumerate(cat_ids):
                if cid == self._prefill_cat_id:
                    self._cat_cb.current(i); break
        elif cat_names:
            self._cat_cb.current(0)

        self._amount_entry = self._field(f, "Budget Amount ($)", 2, lambda p: self._entry(p))
        if self._budget:
            self._amount_entry.insert(0, str(self._budget["amount"]))

        self._month_cb = self._field(f, "Month", 4, lambda p: self._combo(p, MONTH_NAMES))
        default_m = (self._budget["month"] if self._budget else self._default_month or 1) - 1
        self._month_cb.current(default_m)

        self._year_entry = self._field(f, "Year", 6, lambda p: self._entry(p))
        self._year_entry.insert(0, str(self._budget["year"] if self._budget else
                                        self._default_year or
                                        __import__("datetime").date.today().year))

        self._buttons(f)

    def _save(self):
        try:
            amount = float(self._amount_entry.get())
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            year = int(self._year_entry.get())
        except ValueError as e:
            messagebox.showerror("Validation", str(e), parent=self)
            return
        month = self._month_cb.current() + 1
        cat_idx = self._cat_cb.current()
        if cat_idx < 0:
            messagebox.showerror("Validation", "Please select a category.", parent=self)
            return
        self.result = {"amount": amount, "month": month, "year": year}
        if not self._budget:
            self.result["category_id"] = self._cat_ids[cat_idx]
        self.destroy()


# ── Summary cards ──────────────────────────────────────────────────────────

class SummaryCard(tk.Frame):
    def __init__(self, parent, label, color, **kw):
        super().__init__(parent, bg=COLORS["surface"],
                         highlightbackground=COLORS["border"], highlightthickness=1, **kw)
        tk.Label(self, text=label, bg=COLORS["surface"], fg=COLORS["muted"],
                 font=("TkDefaultFont", 9)).pack(anchor="w", padx=16, pady=(14, 2))
        self._val = tk.Label(self, text="—", bg=COLORS["surface"], fg=color,
                             font=("TkDefaultFont", 20, "bold"))
        self._val.pack(anchor="w", padx=16, pady=(0, 14))

    def update(self, value):
        self._val.config(text=value)


# ── Chart panels ───────────────────────────────────────────────────────────

class DonutPanel(ttk.LabelFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, text="Expenses by Category", **kw)
        self._fig = Figure(figsize=(4.2, 3.2), dpi=90, facecolor=COLORS["surface"])
        self._ax  = self._fig.add_subplot(111)
        self._ax.set_facecolor(COLORS["surface"])
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def update(self, by_category):
        self._ax.clear()
        self._ax.set_facecolor(COLORS["surface"])
        data = [c for c in by_category if c["type"] == "expense" and c["total"] > 0]
        if not data:
            self._ax.text(0.5, 0.5, "No expense data", ha="center", va="center",
                          color=COLORS["muted"], transform=self._ax.transAxes, fontsize=10)
        else:
            total = sum(c["total"] for c in data)
            legend_labels = [
                f"{c['category_name']}  {c['total'] / total * 100:.0f}%"
                for c in data
            ]
            wedges, _ = self._ax.pie(
                [c["total"] for c in data],
                labels=None,
                colors=[c["category_color"] for c in data],
                autopct=None,
                startangle=90,
                wedgeprops={"width": 0.55, "linewidth": 1.5, "edgecolor": COLORS["surface"]},
            )
            self._ax.legend(
                wedges,
                legend_labels,
                loc="center left",
                bbox_to_anchor=(1.0, 0.5),
                fontsize=8,
                labelcolor=COLORS["muted"],
                facecolor=COLORS["surface"],
                edgecolor=COLORS["border"],
                framealpha=1,
                handlelength=1.2,
                handleheight=1.2,
                borderpad=0.6,
            )
        self._fig.tight_layout(pad=0.5)
        self._canvas.draw_idle()


class BarPanel(ttk.LabelFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, text="Budget vs Actual", **kw)
        self._fig = Figure(figsize=(4.2, 3.2), dpi=90, facecolor=COLORS["surface"])
        self._ax  = self._fig.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

    def update(self, by_category):
        import numpy as np
        self._ax.clear()
        self._ax.set_facecolor(COLORS["bg"])
        self._fig.set_facecolor(COLORS["surface"])

        data = [c for c in by_category if c["type"] == "expense" and c["budget"] is not None]
        if not data:
            self._ax.text(0.5, 0.5, "No budget data", ha="center", va="center",
                          color=COLORS["muted"], transform=self._ax.transAxes, fontsize=10)
            self._ax.set_facecolor(COLORS["surface"])
            self._canvas.draw_idle()
            return

        x = np.arange(len(data))
        w = 0.38
        spent_colors = [COLORS["expense"] if c["total"] > (c["budget"] or 0) else COLORS["accent"]
                        for c in data]
        self._ax.bar(x - w/2, [c["total"] for c in data],   w, color=spent_colors,
                     label="Spent", zorder=3)
        self._ax.bar(x + w/2, [c["budget"] for c in data],  w,
                     color=COLORS["surface2"], label="Budget",
                     edgecolor=COLORS["border"], linewidth=0.8, zorder=3)

        self._ax.set_xticks(x)
        self._ax.set_xticklabels([c["category_name"] for c in data],
                                  rotation=30, ha="right", fontsize=8,
                                  color=COLORS["muted"])
        self._ax.tick_params(axis="y", colors=COLORS["muted"], labelsize=8)
        self._ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
        for spine in self._ax.spines.values():
            spine.set_color(COLORS["border"])
        self._ax.set_facecolor(COLORS["bg"])
        self._ax.grid(axis="y", color=COLORS["border"], linewidth=0.5, zorder=0)
        self._ax.legend(fontsize=8, labelcolor=COLORS["muted"],
                        facecolor=COLORS["surface"], edgecolor=COLORS["border"])
        self._fig.tight_layout(pad=0.5)
        self._canvas.draw_idle()


# ── Budget progress bars ────────────────────────────────────────────────────

class BudgetBarsPanel(ttk.LabelFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, text="Budget Progress", **kw)
        self._inner = tk.Frame(self, bg=COLORS["surface"])
        self._inner.pack(fill="both", expand=True, padx=12, pady=8)

    def update(self, by_category):
        for w in self._inner.winfo_children():
            w.destroy()

        data = [c for c in by_category if c["type"] == "expense" and c["budget"] is not None]
        if not data:
            tk.Label(self._inner, text="No budgets set for this month",
                     bg=COLORS["surface"], fg=COLORS["muted"],
                     font=("TkDefaultFont", 10)).pack(pady=16)
            return

        for i, c in enumerate(data):
            row = tk.Frame(self._inner, bg=COLORS["surface"])
            row.pack(fill="x", pady=(0, 10))
            row.columnconfigure(1, weight=1)

            pct  = min(c["total"] / c["budget"], 1.0) if c["budget"] else 0
            over = c["budget"] and c["total"] > c["budget"]
            bar_color = (COLORS["expense"] if over else
                         COLORS["warning"] if pct > 0.8 else c["category_color"])

            tk.Label(row, text=f"{c['category_icon']} {c['category_name']}",
                     bg=COLORS["surface"], fg=COLORS["text"],
                     font=("TkDefaultFont", 10), width=18, anchor="w"
                     ).grid(row=0, column=0, sticky="w")

            amount_txt = fmt(c["total"])
            if c["budget"]:
                amount_txt += f" / {fmt(c['budget'])}"
            tk.Label(row, text=amount_txt,
                     bg=COLORS["surface"],
                     fg=COLORS["expense"] if over else COLORS["muted"],
                     font=("TkDefaultFont", 9)
                     ).grid(row=0, column=2, sticky="e", padx=(8, 0))

            canvas = tk.Canvas(row, bg=COLORS["surface2"], height=8,
                                highlightthickness=0)
            canvas.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))
            # Draw the fill after layout settles; use after() to avoid triggering
            # update_idletasks() mid-redraw which crashes matplotlib's legend draw.
            canvas.after(50, lambda c=canvas, p=pct, col=bar_color:
                         c.create_rectangle(0, 0, int(c.winfo_width() * p), 8,
                                            fill=col, outline=""))


# ── Goals progress bars ────────────────────────────────────────────────────

class GoalsBarsPanel(ttk.LabelFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, text="Savings Goals", **kw)
        self._inner = tk.Frame(self, bg=COLORS["surface"])
        self._inner.pack(fill="both", expand=True, padx=12, pady=8)

    def update(self, goals, categories):
        for w in self._inner.winfo_children():
            w.destroy()

        if not goals:
            tk.Label(self._inner, text="No savings goals yet",
                     bg=COLORS["surface"], fg=COLORS["muted"],
                     font=("TkDefaultFont", 10)).pack(pady=16)
            return

        cat_map = {c["id"]: c for c in categories}

        for g in goals:
            pct  = min(g["current_amount"] / g["target_amount"], 1.0) if g["target_amount"] else 0
            done = g["current_amount"] >= g["target_amount"]
            bar_color = (COLORS["income"] if done else
                         COLORS["warning"] if pct > 0.75 else COLORS["accent"])

            linked = cat_map.get(g.get("category_id"))
            name_text = ("✅ " if done else "🎯 ") + g["name"]
            if linked:
                name_text += f"  ({linked['icon']} {linked['name']})"

            row = tk.Frame(self._inner, bg=COLORS["surface"])
            row.pack(fill="x", pady=(0, 10))
            row.columnconfigure(1, weight=1)

            tk.Label(row, text=name_text,
                     bg=COLORS["surface"], fg=COLORS["text"],
                     font=("TkDefaultFont", 10), anchor="w"
                     ).grid(row=0, column=0, sticky="w")

            amount_txt = fmt(g["current_amount"]) + " / " + fmt(g["target_amount"])
            tk.Label(row, text=amount_txt,
                     bg=COLORS["surface"],
                     fg=COLORS["income"] if done else COLORS["muted"],
                     font=("TkDefaultFont", 9)
                     ).grid(row=0, column=2, sticky="e", padx=(8, 0))

            canvas = tk.Canvas(row, bg=COLORS["surface2"], height=8,
                                highlightthickness=0)
            canvas.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(4, 0))
            canvas.after(50, lambda c=canvas, p=pct, col=bar_color:
                         c.create_rectangle(0, 0, int(c.winfo_width() * p), 8,
                                            fill=col, outline=""))


# ── Dashboard tab ──────────────────────────────────────────────────────────

class DashboardTab(ttk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self._build()

    def _build(self):
        cards = tk.Frame(self, bg=COLORS["bg"])
        cards.pack(fill="x", padx=16, pady=(16, 8))
        for i in range(3):
            cards.columnconfigure(i, weight=1)

        self._income_card  = SummaryCard(cards, "Total Income",   COLORS["income"])
        self._expense_card = SummaryCard(cards, "Total Expenses",  COLORS["expense"])
        self._net_card     = SummaryCard(cards, "Net Balance",     COLORS["income"])
        self._income_card.grid( row=0, column=0, sticky="nsew", padx=(0, 8))
        self._expense_card.grid(row=0, column=1, sticky="nsew", padx=8)
        self._net_card.grid(    row=0, column=2, sticky="nsew", padx=(8, 0))

        charts = tk.Frame(self, bg=COLORS["bg"])
        charts.pack(fill="both", expand=True, padx=16, pady=8)
        charts.columnconfigure(0, weight=1)
        charts.columnconfigure(1, weight=1)
        charts.rowconfigure(0, weight=1)

        self._donut = DonutPanel(charts)
        self._donut.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._bar = BarPanel(charts)
        self._bar.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._budget_bars = BudgetBarsPanel(self)
        self._budget_bars.pack(fill="x", padx=16, pady=(0, 8))

        self._goal_bars = GoalsBarsPanel(self)
        self._goal_bars.pack(fill="x", padx=16, pady=(0, 16))

    def refresh(self, summary, goals, categories):
        if not summary:
            return
        net = summary["net"]
        self._income_card.update(fmt(summary["total_income"]))
        self._expense_card.update(fmt(summary["total_expenses"]))
        self._net_card.update(fmt(net))
        self._net_card._val.config(fg=COLORS["income"] if net >= 0 else COLORS["expense"])
        self._donut.update(summary["by_category"])
        self._bar.update(summary["by_category"])
        self._budget_bars.update(summary["by_category"])
        self._goal_bars.update(goals, categories)


# ── Transactions tab ───────────────────────────────────────────────────────

class TransactionsTab(ttk.Frame):
    def __init__(self, parent, app, **kw):
        super().__init__(parent, **kw)
        self._app = app
        self._build()

    def _build(self):
        toolbar = tk.Frame(self, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=16, pady=(12, 0))

        tk.Label(toolbar, text="Type:", bg=COLORS["bg"], fg=COLORS["muted"],
                 font=("TkDefaultFont", 9)).pack(side="left")
        self._type_var = tk.StringVar(value="")
        self._type_cb  = ttk.Combobox(toolbar, textvariable=self._type_var,
                                      values=["", "income", "expense"],
                                      state="readonly", width=10, style="Dark.TCombobox")
        self._type_cb.current(0)
        self._type_cb.pack(side="left", padx=(4, 16))
        self._type_cb.bind("<<ComboboxSelected>>", self._apply_filter)

        tk.Label(toolbar, text="Category:", bg=COLORS["bg"], fg=COLORS["muted"],
                 font=("TkDefaultFont", 9)).pack(side="left")
        self._cat_var = tk.StringVar(value="")
        self._cat_cb  = ttk.Combobox(toolbar, textvariable=self._cat_var,
                                     state="readonly", width=16, style="Dark.TCombobox")
        self._cat_cb.pack(side="left", padx=(4, 0))
        self._cat_cb.bind("<<ComboboxSelected>>", self._apply_filter)

        ttk.Button(toolbar, text="+ Add Transaction", style="Accent.TButton",
                   command=self._add).pack(side="right")

        frame = tk.Frame(self, bg=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=16, pady=12)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        cols = ("date", "description", "category", "type", "amount")
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                   selectmode="browse", style="Dark.Treeview")
        for col, label, width, anchor in [
            ("date",        "Date",        110, "w"),
            ("description", "Description", 220, "w"),
            ("category",    "Category",    140, "w"),
            ("type",        "Type",         80, "center"),
            ("amount",      "Amount",      100, "e"),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=anchor, stretch=(col == "description"))

        self._tree.tag_configure("income",  foreground=COLORS["income"])
        self._tree.tag_configure("expense", foreground=COLORS["expense"])

        sb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda _: self._edit())

        actions = tk.Frame(self, bg=COLORS["bg"])
        actions.pack(fill="x", padx=16, pady=(0, 12))
        self._edit_btn = ttk.Button(actions, text="Edit",   style="Ghost.TButton",
                                    command=self._edit, state="disabled")
        self._del_btn  = ttk.Button(actions, text="Delete", style="Danger.TButton",
                                    command=self._delete, state="disabled")
        self._edit_btn.pack(side="left", padx=(0, 8))
        self._del_btn.pack(side="left")
        self._count_lbl = tk.Label(actions, text="", bg=COLORS["bg"], fg=COLORS["muted"],
                                   font=("TkDefaultFont", 9))
        self._count_lbl.pack(side="right")

        self._all_txs = []

    def _on_select(self, _=None):
        sel = self._tree.selection()
        state = "normal" if sel else "disabled"
        self._edit_btn.config(state=state)
        self._del_btn.config(state=state)

    def _apply_filter(self, _=None):
        self._populate(self._all_txs)

    def refresh(self, transactions, categories):
        self._all_txs = transactions
        cat_names = [""] + [f"{c['icon']} {c['name']}" for c in categories]
        self._cat_cb["values"] = cat_names
        self._cat_cb_cats = [None] + categories
        self._populate(transactions)

    def _populate(self, transactions):
        type_filter = self._type_var.get()
        cat_idx = self._cat_cb.current()
        cat_filter_id = (self._cat_cb_cats[cat_idx]["id"]
                         if hasattr(self, "_cat_cb_cats") and cat_idx > 0 else None)

        self._tree.delete(*self._tree.get_children())
        shown = 0
        for tx in transactions:
            if type_filter and tx["type"] != type_filter:
                continue
            if cat_filter_id and tx["category_id"] != cat_filter_id:
                continue
            sign = "+" if tx["type"] == "income" else "-"
            self._tree.insert("", "end", iid=str(tx["id"]), tags=(tx["type"],), values=(
                fmt_date(tx["date"]),
                tx["description"],
                f"{tx['category']['icon']} {tx['category']['name']}",
                tx["type"],
                f"{sign}{fmt(tx['amount'])}",
            ))
            shown += 1
        self._count_lbl.config(text=f"{shown} transaction{'s' if shown != 1 else ''}")
        self._on_select()

    def _add(self):
        dlg = TransactionDialog(self._app, self._app.state.categories)
        if dlg.result:
            self._app.run_bg(self._app.api.create_transaction, dlg.result,
                             on_success=lambda _: self._app.refresh_all())

    def _edit(self):
        sel = self._tree.selection()
        if not sel: return
        tx_id = int(sel[0])
        tx = next((t for t in self._all_txs if t["id"] == tx_id), None)
        if not tx: return
        dlg = TransactionDialog(self._app, self._app.state.categories, transaction=tx)
        if dlg.result:
            self._app.run_bg(self._app.api.update_transaction, tx_id, dlg.result,
                             on_success=lambda _: self._app.refresh_all())

    def _delete(self):
        sel = self._tree.selection()
        if not sel: return
        tx_id = int(sel[0])
        if not messagebox.askyesno("Delete", "Delete this transaction?", parent=self._app):
            return
        self._app.run_bg(self._app.api.delete_transaction, tx_id,
                         on_success=lambda _: self._app.refresh_all())


# ── Budgets tab ────────────────────────────────────────────────────────────

class BudgetsTab(ttk.Frame):
    def __init__(self, parent, app, **kw):
        super().__init__(parent, **kw)
        self._app = app
        self._build()

    def _build(self):
        toolbar = tk.Frame(self, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=16, pady=(12, 0))
        ttk.Button(toolbar, text="+ Set Budget", style="Accent.TButton",
                   command=self._add).pack(side="right")

        frame = tk.Frame(self, bg=COLORS["bg"])
        frame.pack(fill="both", expand=True, padx=16, pady=12)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        cols = ("category", "budget", "spent", "remaining")
        self._tree = ttk.Treeview(frame, columns=cols, show="headings",
                                   selectmode="browse", style="Dark.Treeview")
        for col, label, width, anchor in [
            ("category",  "Category",  180, "w"),
            ("budget",    "Budget",    110, "e"),
            ("spent",     "Spent",     110, "e"),
            ("remaining", "Remaining", 110, "e"),
        ]:
            self._tree.heading(col, text=label)
            self._tree.column(col, width=width, anchor=anchor)

        self._tree.tag_configure("over",   foreground=COLORS["expense"])
        self._tree.tag_configure("under",  foreground=COLORS["income"])
        self._tree.tag_configure("nobudget", foreground=COLORS["muted"])

        sb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        actions = tk.Frame(self, bg=COLORS["bg"])
        actions.pack(fill="x", padx=16, pady=(0, 12))
        self._edit_btn = ttk.Button(actions, text="Edit",   style="Ghost.TButton",
                                    command=self._edit, state="disabled")
        self._del_btn  = ttk.Button(actions, text="Delete", style="Danger.TButton",
                                    command=self._delete, state="disabled")
        self._edit_btn.pack(side="left", padx=(0, 8))
        self._del_btn.pack(side="left")

        self._budgets = []
        self._summary_cats = []

    def _on_select(self, _=None):
        sel = self._tree.selection()
        has = bool(sel)
        # only enable edit/delete when a budgeted row (iid is budget id) is selected
        is_budget = has and not sel[0].startswith("nb_")
        self._edit_btn.config(state="normal" if is_budget else "disabled")
        self._del_btn.config(state="normal"  if is_budget else "disabled")

    def refresh(self, budgets, summary):
        self._budgets = budgets
        self._summary_cats = summary.get("by_category", []) if summary else []
        budget_map = {b["category_id"]: b for b in budgets}
        spent_map  = {c["category_id"]: c["total"] for c in self._summary_cats}

        self._tree.delete(*self._tree.get_children())
        for b in budgets:
            cid   = b["category_id"]
            spent = spent_map.get(cid, 0.0)
            rem   = b["amount"] - spent
            over  = rem < 0
            tag   = "over" if over else "under"
            rem_str = ("-" if over else "+") + fmt(abs(rem))
            self._tree.insert("", "end", iid=str(b["id"]), tags=(tag,), values=(
                f"{b['category']['icon']} {b['category']['name']}",
                fmt(b["amount"]),
                fmt(spent) if spent else "—",
                rem_str,
            ))

    def _add(self):
        dlg = BudgetDialog(self._app, self._app.state.categories,
                           month=self._app.state.month, year=self._app.state.year)
        if dlg.result:
            self._app.run_bg(self._app.api.create_budget, dlg.result,
                             on_success=lambda _: self._app.refresh_all())

    def _edit(self):
        sel = self._tree.selection()
        if not sel: return
        b_id = int(sel[0])
        b = next((b for b in self._budgets if b["id"] == b_id), None)
        if not b: return
        dlg = BudgetDialog(self._app, self._app.state.categories, budget=b)
        if dlg.result:
            self._app.run_bg(self._app.api.update_budget, b_id, dlg.result,
                             on_success=lambda _: self._app.refresh_all())

    def _delete(self):
        sel = self._tree.selection()
        if not sel: return
        b_id = int(sel[0])
        if not messagebox.askyesno("Delete", "Remove this budget?", parent=self._app):
            return
        self._app.run_bg(self._app.api.delete_budget, b_id,
                         on_success=lambda _: self._app.refresh_all())


# ── Main application ───────────────────────────────────────────────────────

class FinanceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Finance Tracker")
        self.geometry("1000x720")
        self.minsize(800, 600)
        self.configure(bg=COLORS["bg"])

        self.api   = ApiClient()
        self.state = AppState()
        self._q    = queue.Queue()
        self._pending = 0
        self._lock    = threading.Lock()

        self._apply_styles()
        self._build_ui()
        self.after(50, self._poll_queue)
        self.refresh_all()

    def _apply_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")

        bg, sur, brd, txt, mut, acc = (
            COLORS["bg"], COLORS["surface"], COLORS["border"],
            COLORS["text"], COLORS["muted"], COLORS["accent"],
        )

        s.configure(".",                 background=bg, foreground=txt, borderwidth=0)
        s.configure("TFrame",            background=bg)
        s.configure("TLabel",            background=bg, foreground=txt)
        s.configure("TLabelframe",       background=sur, foreground=mut, bordercolor=brd)
        s.configure("TLabelframe.Label", background=sur, foreground=mut,
                    font=("TkDefaultFont", 9))
        s.configure("TNotebook",         background=bg, borderwidth=0)
        s.configure("TNotebook.Tab",     background=sur, foreground=mut,
                    padding=[14, 7], font=("TkDefaultFont", 10))
        s.map("TNotebook.Tab",
              background=[("selected", acc)],
              foreground=[("selected", "#ffffff")])

        s.configure("Dark.Treeview",
                    background=sur, foreground=txt,
                    fieldbackground=sur, rowheight=30, borderwidth=0)
        s.configure("Dark.Treeview.Heading",
                    background=bg, foreground=mut,
                    relief="flat", font=("TkDefaultFont", 9))
        s.map("Dark.Treeview", background=[("selected", acc)],
              foreground=[("selected", "#ffffff")])

        s.configure("Dark.TEntry",    fieldbackground=bg, foreground=txt,
                    insertcolor=txt, bordercolor=brd, lightcolor=brd, darkcolor=brd)
        s.configure("Dark.TCombobox", fieldbackground=bg, foreground=txt,
                    selectbackground=acc, arrowcolor=mut)
        s.map("Dark.TCombobox", fieldbackground=[("readonly", bg)])

        s.configure("Accent.TButton", background=acc, foreground="#ffffff",
                    font=("TkDefaultFont", 10), padding=[10, 6])
        s.map("Accent.TButton", background=[("active", COLORS["accent"])])

        s.configure("Ghost.TButton", background=COLORS["surface2"], foreground=txt,
                    font=("TkDefaultFont", 10), padding=[10, 6],
                    bordercolor=brd, relief="flat")
        s.map("Ghost.TButton", background=[("active", brd)])

        s.configure("Danger.TButton", background=COLORS["surface2"],
                    foreground=COLORS["expense"],
                    font=("TkDefaultFont", 10), padding=[10, 6],
                    bordercolor=COLORS["expense"], relief="flat")
        s.map("Danger.TButton", background=[("active", brd)])

        s.configure("TScrollbar", background=sur, troughcolor=bg,
                    arrowcolor=mut, bordercolor=bg)

    def _build_ui(self):
        # Top bar
        topbar = tk.Frame(self, bg=COLORS["surface"],
                          highlightbackground=COLORS["border"], highlightthickness=1)
        topbar.pack(fill="x", side="top")

        tk.Label(topbar, text="💰  Finance Tracker", bg=COLORS["surface"],
                 fg=COLORS["text"], font=("TkDefaultFont", 13, "bold")
                 ).pack(side="left", padx=20, pady=10)

        self._status_lbl = tk.Label(topbar, text="", bg=COLORS["surface"],
                                    fg=COLORS["muted"], font=("TkDefaultFont", 9))
        self._status_lbl.pack(side="right", padx=20)

        # Month nav
        nav = tk.Frame(topbar, bg=COLORS["surface"])
        nav.pack(side="right", padx=12, pady=6)
        tk.Button(nav, text="‹", bg=COLORS["surface2"], fg=COLORS["text"],
                  relief="flat", font=("TkDefaultFont", 13), bd=0,
                  activebackground=COLORS["border"],
                  command=self._prev_month).pack(side="left", padx=(0, 4))
        self._month_lbl = tk.Label(nav, bg=COLORS["surface"], fg=COLORS["text"],
                                   font=("TkDefaultFont", 11, "bold"), width=14,
                                   anchor="center")
        self._month_lbl.pack(side="left")
        tk.Button(nav, text="›", bg=COLORS["surface2"], fg=COLORS["text"],
                  relief="flat", font=("TkDefaultFont", 13), bd=0,
                  activebackground=COLORS["border"],
                  command=self._next_month).pack(side="left", padx=(4, 0))

        self._update_month_label()

        # Notebook
        self._nb = ttk.Notebook(self, style="TNotebook")
        self._nb.pack(fill="both", expand=True, padx=0, pady=0)

        self._dash_tab = DashboardTab(self._nb)
        self._tx_tab   = TransactionsTab(self._nb, self)
        self._bgt_tab  = BudgetsTab(self._nb, self)

        self._nb.add(self._dash_tab, text="  📊  Dashboard  ")
        self._nb.add(self._tx_tab,   text="  💸  Transactions  ")
        self._nb.add(self._bgt_tab,  text="  📋  Budgets  ")

    def _update_month_label(self):
        self._month_lbl.config(
            text=f"{MONTH_NAMES[self.state.month - 1]} {self.state.year}")

    def _prev_month(self):
        if self.state.month == 1:
            self.state.month, self.state.year = 12, self.state.year - 1
        else:
            self.state.month -= 1
        self._update_month_label()
        self.refresh_all()

    def _next_month(self):
        if self.state.month == 12:
            self.state.month, self.state.year = 1, self.state.year + 1
        else:
            self.state.month += 1
        self._update_month_label()
        self.refresh_all()

    # ── Background task runner ─────────────────────────────────────────────

    def run_bg(self, fn, *args, on_success=None, on_error=None):
        def worker():
            try:
                result = fn(*args)
                self._q.put(("ok", on_success, result))
            except Exception as exc:
                self._q.put(("err", on_error, exc))
        threading.Thread(target=worker, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                kind, cb, payload = self._q.get_nowait()
                if kind == "ok":
                    if cb: cb(payload)
                else:
                    if cb:
                        cb(payload)
                    else:
                        msg = _api_error(payload)
                        messagebox.showerror("Error", msg, parent=self)
                        self._status_lbl.config(text="Error — see dialog", fg=COLORS["expense"])
        except queue.Empty:
            pass
        self.after(50, self._poll_queue)

    # ── Refresh ────────────────────────────────────────────────────────────

    def refresh_all(self):
        m, y = self.state.month, self.state.year
        self._status_lbl.config(text="Loading…", fg=COLORS["muted"])

        results = {}
        with self._lock:
            self._pending = 5

        def store(key):
            def cb(data):
                results[key] = data
                with self._lock:
                    self._pending -= 1
                    done = self._pending == 0
                if done:
                    self.state.categories   = results.get("cats", [])
                    self.state.transactions = results.get("txs", [])
                    self.state.budgets      = results.get("bgt", [])
                    self.state.goals        = results.get("gls", [])
                    self.state.summary      = results.get("sum", {})
                    self._redraw()
            return cb

        def err_cb(exc):
            self._status_lbl.config(text="Server offline", fg=COLORS["expense"])
            messagebox.showerror("Connection Error", _api_error(exc), parent=self)

        self.run_bg(self.api.get_categories,               on_success=store("cats"), on_error=err_cb)
        self.run_bg(self.api.get_transactions, m, y,       on_success=store("txs"),  on_error=err_cb)
        self.run_bg(self.api.get_budgets,      m, y,       on_success=store("bgt"),  on_error=err_cb)
        self.run_bg(self.api.get_goals,                    on_success=store("gls"),  on_error=err_cb)
        self.run_bg(self.api.get_summary,      m, y,       on_success=store("sum"),  on_error=err_cb)

    def _redraw(self):
        self._status_lbl.config(text="", fg=COLORS["muted"])
        self._dash_tab.refresh(self.state.summary, self.state.goals, self.state.categories)
        self._tx_tab.refresh(self.state.transactions, self.state.categories)
        self._bgt_tab.refresh(self.state.budgets, self.state.summary)


if __name__ == "__main__":
    app = FinanceApp()
    app.mainloop()
