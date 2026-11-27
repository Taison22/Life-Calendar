#!/usr/bin/env python3
"""
Life Calendar — Интерактивный календарь жизни
Desktop app visualizing life in weeks.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk
from tkinter import Canvas, messagebox, filedialog
import tkinter as tk
from datetime import date
from typing import Optional, Dict, Any, List, Tuple

from database import (
    init_db, get_setting, set_setting, get_all_settings,
    get_categories, get_events_for_week, get_all_events,
    add_event, update_event, delete_event, get_week_colors,
    export_data, import_data,
)
from calculations import (
    parse_date, calculate_life_stats, date_for_life_week,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLOR_PAST = "#3B82F6"
COLOR_CURRENT = "#F59E0B"
COLOR_FUTURE = "#374151"
COLOR_BG = "#0F172A"
COLOR_SIDEBAR = "#1E293B"
COLOR_CARD = "#1E293B"
COLOR_TEXT = "#E2E8F0"
COLOR_MUTED = "#94A3B8"
COLOR_ACCENT = "#6366F1"


class LifeCalendarApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Life Calendar — Календарь жизни")
        self.geometry("1280x800")
        self.minsize(1000, 600)

        init_db()

        self.settings = get_all_settings()
        self.birth_date: Optional[date] = parse_date(self.settings.get("birth_date", ""))
        self.life_expectancy = int(self.settings.get("life_expectancy", "90") or 90)
        self.first_day = int(self.settings.get("first_day_of_week", "0") or 0)
        self.stats: Dict[str, Any] = {}
        self.week_colors: Dict[Tuple[int, int], str] = {}
        self._events_cache: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
        self.current_view = "calendar"
        self.tooltip = None
        self.square_size = 10
        self.gap = 2
        self._grid_meta = {}
        self._highlight_week: Optional[Tuple[int, int]] = None  # (life_year, week)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()
        self.after(100, self._check_setup)

    def _on_close(self):
        """Clean up reusable tooltip window and exit."""
        if self.tooltip is not None:
            try:
                self.tooltip.destroy()
            except Exception:
                pass
            self.tooltip = None
        self.destroy()

    def _check_setup(self):
        if self.settings.get("setup_completed") != "1" or not self.birth_date:
            self._show_setup_dialog()
        else:
            self.refresh_data()

    def refresh_data(self):
        if not self.birth_date:
            return
        self.stats = calculate_life_stats(
            self.birth_date, self.life_expectancy, first_day_of_week=self.first_day
        )
        self.week_colors = get_week_colors()
        self._events_cache.clear()  # invalidate event cache after any data change
        if self.current_view == "calendar":
            self._draw_grid()
        elif self.current_view == "stats":
            self._render_stats()
        elif self.current_view == "events":
            self._render_events()

    def _get_events_cached(self, year: int, week: int) -> List[Dict[str, Any]]:
        key = (year, week)
        if key not in self._events_cache:
            self._events_cache[key] = get_events_for_week(year, week)
        return self._events_cache[key]

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar, text="📅 Life Calendar",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(pady=(24, 4), padx=16)

        ctk.CTkLabel(
            self.sidebar, text="Календарь жизни",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_MUTED
        ).pack(pady=(0, 24), padx=16)

        self.nav_buttons = {}
        for key, label, icon in [
            ("calendar", "Календарь жизни", "▦"),
            ("stats", "Статистика", "📊"),
            ("events", "События", "📝"),
            ("settings", "Настройки", "⚙"),
        ]:
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {icon}  {label}",
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                text_color=COLOR_TEXT,
                hover_color="#334155",
                font=ctk.CTkFont(size=14),
                command=lambda k=key: self._switch_view(k)
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = btn

        self.sidebar_info = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_info.pack(side="bottom", fill="x", padx=12, pady=16)
        self.info_label = ctk.CTkLabel(
            self.sidebar_info, text="",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_MUTED,
            justify="left",
            wraplength=180
        )
        self.info_label.pack(anchor="w")

        self.content = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.views: Dict[str, ctk.CTkFrame] = {}
        for name in ("calendar", "stats", "events", "settings"):
            f = ctk.CTkFrame(self.content, fg_color="transparent")
            f.grid(row=0, column=0, sticky="nsew")
            self.views[name] = f
            f.grid_remove()

        self._build_calendar_view()
        self._build_stats_view()
        self._build_events_view()
        self._build_settings_view()
        self._switch_view("calendar")

    def _switch_view(self, name: str):
        self.current_view = name
        for k, f in self.views.items():
            if k == name:
                f.grid()
            else:
                f.grid_remove()
        for k, btn in self.nav_buttons.items():
            btn.configure(fg_color="#334155" if k == name else "transparent")
        if name == "calendar":
            self._draw_grid()
        elif name == "stats":
            self._render_stats()
        elif name == "events":
            self._render_events()
        elif name == "settings":
            self._render_settings()

    def _build_calendar_view(self):
        frame = self.views["calendar"]
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(frame, fg_color="transparent", height=50)
        toolbar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        toolbar.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(
            toolbar, text="90 лет жизни в неделях",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLOR_TEXT
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            toolbar, text="К текущей неделе", width=140, height=32,
            command=self._scroll_to_current, fg_color=COLOR_ACCENT
        ).grid(row=0, column=1, padx=12)

        self.age_jump = ctk.CTkEntry(toolbar, width=80, placeholder_text="Год")
        self.age_jump.grid(row=0, column=3, padx=4)
        ctk.CTkButton(
            toolbar, text="Перейти", width=80, height=32,
            command=self._jump_to_year
        ).grid(row=0, column=4, padx=4)

        legend = ctk.CTkFrame(toolbar, fg_color="transparent")
        legend.grid(row=0, column=5, padx=(20, 0))
        for color, label in [(COLOR_PAST, "Прошлое"), (COLOR_CURRENT, "Сейчас"), (COLOR_FUTURE, "Будущее")]:
            ctk.CTkFrame(legend, width=14, height=14, fg_color=color, corner_radius=3).pack(side="left", padx=(8, 4))
            ctk.CTkLabel(legend, text=label, font=ctk.CTkFont(size=11), text_color=COLOR_MUTED).pack(side="left")

        canvas_frame = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=12)
        canvas_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_rowconfigure(0, weight=1)

        self.canvas = Canvas(canvas_frame, bg="#1E293B", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.v_scroll = ctk.CTkScrollbar(canvas_frame, orientation="vertical", command=self.canvas.yview)
        self.v_scroll.grid(row=0, column=1, sticky="ns", pady=8)
        self.h_scroll = ctk.CTkScrollbar(canvas_frame, orientation="horizontal", command=self.canvas.xview)
        self.h_scroll.grid(row=1, column=0, sticky="ew", padx=8)
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)

        self.canvas.bind("<Configure>", lambda e: self.after(50, self._draw_grid))
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Leave>", self._hide_tooltip)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)

    def _draw_grid(self):
        if not self.birth_date or not self.stats:
            return
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 400)
        h = max(self.canvas.winfo_height(), 400)

        max_years = self.life_expectancy
        cols = 52
        rows = max_years + 1

        avail_w = w - 50
        avail_h = h - 40
        self.square_size = max(6, min(14, int(min(avail_w / cols, avail_h / rows) - self.gap)))
        cell = self.square_size + self.gap
        offset_x = 40
        offset_y = 30

        total_w = offset_x + cols * cell + 20
        total_h = offset_y + rows * cell + 20
        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))

        for col in range(cols):
            if col % 5 == 0 or col == 0:
                x = offset_x + col * cell + self.square_size / 2
                self.canvas.create_text(x, 12, text=str(col + 1), fill=COLOR_MUTED, font=("Segoe UI", 8))

        life_year = self.stats.get("life_year", 0)
        week_of = self.stats.get("week_of_life_year", 0)

        for row in range(rows):
            y = offset_y + row * cell
            if row % 5 == 0 or row == 0:
                self.canvas.create_text(18, y + self.square_size / 2, text=str(row), fill=COLOR_MUTED, font=("Segoe UI", 9), anchor="e")

            for col in range(cols):
                x = offset_x + col * cell
                is_past = (row < life_year) or (row == life_year and col < week_of)
                is_current = (row == life_year and col == week_of)
                key = (row, col)
                event_color = self.week_colors.get(key)

                if is_current:
                    fill = COLOR_CURRENT
                elif event_color:
                    fill = event_color
                elif is_past:
                    fill = COLOR_PAST
                else:
                    fill = COLOR_FUTURE

                tag = f"sq_{row}_{col}"
                self.canvas.create_rectangle(
                    x, y, x + self.square_size, y + self.square_size,
                    fill=fill, outline="", tags=(tag, "square")
                )
                if is_current:
                    self.canvas.create_rectangle(
                        x - 1, y - 1, x + self.square_size + 1, y + self.square_size + 1,
                        outline="#FBBF24", width=2, tags=(tag,)
                    )
                # Temporary highlight when navigating from events list
                if self._highlight_week and self._highlight_week == (row, col):
                    self.canvas.create_rectangle(
                        x - 2, y - 2, x + self.square_size + 2, y + self.square_size + 2,
                        outline="#F472B6", width=3, tags=(tag, "highlight")
                    )

        self._grid_meta = {
            "offset_x": offset_x, "offset_y": offset_y,
            "cell": cell, "sq": self.square_size,
            "rows": rows, "cols": cols,
        }

        if self.stats:
            pct = self.stats["percent_lived"]
            self.info_label.configure(
                text=f"Возраст: {self.stats['years']} лет\n"
                     f"Прожито: {self.stats['weeks_lived']} нед.\n"
                     f"Осталось: {self.stats['weeks_remaining']} нед.\n"
                     f"Прогресс: {pct:.1f}%"
            )

    def _hit_test(self, event) -> Optional[Tuple[int, int]]:
        meta = self._grid_meta
        if not meta:
            return None
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        col = int((cx - meta["offset_x"]) // meta["cell"])
        row = int((cy - meta["offset_y"]) // meta["cell"])
        if 0 <= row < meta["rows"] and 0 <= col < meta["cols"]:
            lx = (cx - meta["offset_x"]) % meta["cell"]
            ly = (cy - meta["offset_y"]) % meta["cell"]
            if lx <= meta["sq"] and ly <= meta["sq"]:
                return row, col
        return None

    def _on_canvas_motion(self, event):
        hit = self._hit_test(event)
        if hit:
            self._show_tooltip(event, *hit)
        else:
            self._hide_tooltip()

    def _ensure_tooltip(self):
        """Single reusable tooltip window — avoids create/destroy on every mouse move."""
        if self.tooltip is not None:
            try:
                if self.tooltip.winfo_exists():
                    return
            except tk.TclError:
                self.tooltip = None
        self.tooltip = tk.Toplevel(self)
        self.tooltip.wm_overrideredirect(True)
        try:
            self.tooltip.wm_attributes("-topmost", True)
        except tk.TclError:
            pass
        self._tooltip_label = tk.Label(
            self.tooltip, text="", justify="left",
            background="#1E293B", foreground="#E2E8F0",
            relief="solid", borderwidth=1,
            font=("Segoe UI", 10), padx=8, pady=6
        )
        self._tooltip_label.pack()
        self.tooltip.withdraw()

    def _show_tooltip(self, event, row: int, col: int):
        if not self.birth_date:
            return
        start, end = date_for_life_week(self.birth_date, row, col)
        life_y = self.stats.get("life_year", 0)
        week_of = self.stats.get("week_of_life_year", 0)
        if row < life_y or (row == life_y and col < week_of):
            status = "Прошедшая"
        elif row == life_y and col == week_of:
            status = "Текущая"
        else:
            status = "Будущая"
        events = self._get_events_cached(row, col)
        ev_text = ""
        if events:
            ev_text = "\n" + "\n".join(f"• {e['title']}" for e in events[:3])
            if len(events) > 3:
                ev_text += f"\n… ещё {len(events)-3}"
        text = (
            f"Возраст: {row} лет, неделя {col+1}\n"
            f"{start.strftime('%d.%m.%Y')} – {end.strftime('%d.%m.%Y')}\n"
            f"Статус: {status}{ev_text}"
        )
        self._ensure_tooltip()
        self._tooltip_label.configure(text=text)
        self.tooltip.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 12}")
        self.tooltip.deiconify()
        self.tooltip.lift()

    def _hide_tooltip(self, event=None):
        if self.tooltip is not None:
            try:
                if self.tooltip.winfo_exists():
                    self.tooltip.withdraw()
            except tk.TclError:
                self.tooltip = None

    def _on_canvas_click(self, event):
        hit = self._hit_test(event)
        if hit:
            self._open_week_dialog(*hit)

    def _on_mousewheel(self, event):
        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            self.canvas.yview_scroll(-3, "units")
        else:
            self.canvas.yview_scroll(3, "units")

    def _scroll_to_current(self):
        if not self.stats or not self._grid_meta:
            return
        meta = self._grid_meta
        y = meta["offset_y"] + self.stats["life_year"] * meta["cell"]
        total = meta["offset_y"] + meta["rows"] * meta["cell"]
        self.canvas.yview_moveto(max(0, (y - 100) / max(1, total)))

    def _jump_to_year(self):
        try:
            y = int(self.age_jump.get())
            if 0 <= y <= self.life_expectancy and self._grid_meta:
                meta = self._grid_meta
                total = meta["offset_y"] + meta["rows"] * meta["cell"]
                pos = (meta["offset_y"] + y * meta["cell"]) / max(1, total)
                self.canvas.yview_moveto(pos)
        except ValueError:
            pass

    def _open_week_dialog(self, life_year: int, week: int, edit_event: Optional[Dict] = None):
        start, end = date_for_life_week(self.birth_date, life_year, week)
        cats = get_categories()
        cat_by_id = {c["id"]: c for c in cats}
        cat_names = [c["name"] for c in cats]
        name_to_id = {c["name"]: c["id"] for c in cats}

        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Неделя {week+1} • {life_year} лет")
        dialog.geometry("500x620")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=f"{start.strftime('%d.%m.%Y')} – {end.strftime('%d.%m.%Y')}",
            font=ctk.CTkFont(size=14), text_color=COLOR_MUTED
        ).pack(pady=(16, 4))

        list_frame = ctk.CTkScrollableFrame(dialog, height=140)
        list_frame.pack(fill="x", padx=16, pady=8)

        form_title = ctk.CTkLabel(dialog, text="Новое событие", font=ctk.CTkFont(size=14, weight="bold"))
        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=8)
        form_title.pack(anchor="w", padx=16)

        title_entry = ctk.CTkEntry(form, placeholder_text="Название события")
        title_entry.pack(fill="x", pady=4)
        note_entry = ctk.CTkTextbox(form, height=70)
        note_entry.pack(fill="x", pady=4)

        cat_var = ctk.StringVar(value=cats[0]["id"] if cats else "")
        cat_menu = ctk.CTkOptionMenu(
            form, values=cat_names,
            command=lambda n: cat_var.set(name_to_id.get(n, ""))
        )
        cat_menu.pack(fill="x", pady=4)

        color_var = ctk.StringVar(value="#3B82F6")
        color_frame = ctk.CTkFrame(form, fg_color="transparent")
        color_frame.pack(fill="x", pady=4)
        for c in ["#3B82F6", "#8B5CF6", "#06B6D4", "#F59E0B", "#10B981", "#EF4444", "#EC4899", "#84CC16"]:
            ctk.CTkButton(
                color_frame, text="", width=24, height=24,
                fg_color=c, hover_color=c, corner_radius=4,
                command=lambda col=c: color_var.set(col)
            ).pack(side="left", padx=2)

        editing_id: List[Optional[str]] = [None]

        def load_into_form(ev: Dict):
            editing_id[0] = ev["id"]
            form_title.configure(text="Редактирование события")
            title_entry.delete(0, "end")
            title_entry.insert(0, ev.get("title") or "")
            note_entry.delete("1.0", "end")
            note_entry.insert("1.0", ev.get("note") or "")
            cid = ev.get("category_id")
            if cid and cid in cat_by_id:
                cat_menu.set(cat_by_id[cid]["name"])
                cat_var.set(cid)
            if ev.get("color"):
                color_var.set(ev["color"])

        def clear_form():
            editing_id[0] = None
            form_title.configure(text="Новое событие")
            title_entry.delete(0, "end")
            note_entry.delete("1.0", "end")
            if cats:
                cat_menu.set(cats[0]["name"])
                cat_var.set(cats[0]["id"])
            color_var.set("#3B82F6")

        def refresh_list():
            for w in list_frame.winfo_children():
                w.destroy()
            # Invalidate week cache once, then read (fills cache for tooltips too)
            self._events_cache.pop((life_year, week), None)
            evs = self._get_events_cached(life_year, week)
            if not evs:
                ctk.CTkLabel(list_frame, text="Нет событий", text_color=COLOR_MUTED).pack()
            for ev in evs:
                rowf = ctk.CTkFrame(list_frame, fg_color="#334155", corner_radius=6)
                rowf.pack(fill="x", pady=3)
                ctk.CTkLabel(rowf, text=ev["title"], font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(side="left", padx=8, pady=6)
                btn_frame = ctk.CTkFrame(rowf, fg_color="transparent")
                btn_frame.pack(side="right", padx=4)
                ctk.CTkButton(
                    btn_frame, text="✎", width=28, height=28,
                    fg_color="transparent", hover_color="#6366F1",
                    command=lambda e=ev: load_into_form(e)
                ).pack(side="left", padx=2)
                ctk.CTkButton(
                    btn_frame, text="✕", width=28, height=28,
                    fg_color="transparent", hover_color="#EF4444",
                    command=lambda eid=ev["id"]: (
                        delete_event(eid),
                        self._events_cache.pop((life_year, week), None),
                        refresh_list(),
                        self.refresh_data()
                    )
                ).pack(side="left", padx=2)

        refresh_list()

        def save():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("Ошибка", "Введите название")
                return
            note = note_entry.get("1.0", "end").strip()
            if editing_id[0]:
                update_event(
                    editing_id[0],
                    title=title,
                    note=note,
                    category_id=cat_var.get() or None,
                    color=color_var.get(),
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                )
            else:
                add_event(
                    title=title, note=note, category_id=cat_var.get() or None,
                    color=color_var.get(), week_year=life_year, week_number=week,
                    start_date=start.isoformat(), end_date=end.isoformat(),
                )
            self._events_cache.pop((life_year, week), None)
            clear_form()
            refresh_list()
            self.refresh_data()

        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", pady=8)
        ctk.CTkButton(btn_row, text="Сохранить", command=save, fg_color=COLOR_ACCENT).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="Очистить", command=clear_form).pack(side="left", padx=4)
        ctk.CTkButton(dialog, text="Закрыть", command=dialog.destroy).pack(pady=8)

        if edit_event:
            load_into_form(edit_event)

    def _build_stats_view(self):
        frame = self.views["stats"]
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(frame, text="Статистика жизни", font=ctk.CTkFont(size=22, weight="bold"), text_color=COLOR_TEXT).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 8))
        self.stats_container = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.stats_container.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)

    def _render_stats(self):
        for w in self.stats_container.winfo_children():
            w.destroy()
        if not self.stats:
            ctk.CTkLabel(self.stats_container, text="Укажите дату рождения в настройках").pack()
            return
        s = self.stats
        cards = [
            ("Возраст", f"{s['years']} лет {s['months']} мес. {s['days']} дн."),
            ("Прожито недель", f"{s['weeks_lived']:,}".replace(",", " ")),
            ("Осталось недель", f"{s['weeks_remaining']:,}".replace(",", " ")),
            ("Процент жизни", f"{s['percent_lived']:.1f}%"),
            ("Прожито дней", f"{s['days_lived']:,}".replace(",", " ")),
            ("Осталось дней", f"{s['days_remaining']:,}".replace(",", " ")),
            ("До дня рождения", f"{s['days_to_next_birthday']} дн. ({s['weeks_to_next_birthday']} нед.)"),
            ("С последнего ДР", f"{s['days_since_last_birthday']} дней"),
        ]
        grid = ctk.CTkFrame(self.stats_container, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        for i, (title, value) in enumerate(cards):
            card = ctk.CTkFrame(grid, fg_color=COLOR_CARD, corner_radius=12)
            card.grid(row=i // 2, column=i % 2, padx=8, pady=8, sticky="nsew")
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=13), text_color=COLOR_MUTED).pack(anchor="w", padx=16, pady=(12, 2))
            ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=22, weight="bold"), text_color=COLOR_TEXT).pack(anchor="w", padx=16, pady=(0, 12))
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        prog_frame = ctk.CTkFrame(self.stats_container, fg_color=COLOR_CARD, corner_radius=12)
        prog_frame.pack(fill="x", padx=8, pady=16)
        ctk.CTkLabel(prog_frame, text="Прогресс жизни", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=16, pady=(12, 4))
        bar = ctk.CTkProgressBar(prog_frame, height=18, progress_color=COLOR_ACCENT)
        bar.pack(fill="x", padx=16, pady=(0, 4))
        bar.set(s["percent_lived"] / 100)
        ctk.CTkLabel(prog_frame, text=f"{s['percent_lived']:.1f}%  •  до {s['end_date'].strftime('%d.%m.%Y')}", text_color=COLOR_MUTED).pack(anchor="w", padx=16, pady=(0, 12))

    def _build_events_view(self):
        frame = self.views["events"]
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text="События", font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, sticky="w")
        self.events_search = ctk.CTkEntry(header, placeholder_text="Поиск...", width=200)
        self.events_search.grid(row=0, column=1, padx=12, sticky="e")
        self.events_search.bind("<KeyRelease>", lambda e: self._render_events())
        self.events_cat_filter = ctk.CTkOptionMenu(header, values=["Все категории"], command=lambda _: self._render_events())
        self.events_cat_filter.grid(row=0, column=2, padx=4)
        self.events_list = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.events_list.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)

    def _render_events(self):
        for w in self.events_list.winfo_children():
            w.destroy()
        cats = get_categories()
        self.events_cat_filter.configure(values=["Все категории"] + [c["name"] for c in cats])
        search = self.events_search.get().strip()
        selected_cat = self.events_cat_filter.get()
        cat_id = next((c["id"] for c in cats if c["name"] == selected_cat), None) if selected_cat != "Все категории" else None
        events = get_all_events(search=search, category_id=cat_id)
        if not events:
            ctk.CTkLabel(self.events_list, text="Нет событий", text_color=COLOR_MUTED).pack(pady=40)
            return
        for ev in events:
            card = ctk.CTkFrame(self.events_list, fg_color=COLOR_CARD, corner_radius=10)
            card.pack(fill="x", pady=4)
            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=12, pady=10)
            ctk.CTkLabel(left, text=ev["title"], font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(anchor="w")
            meta = f"Год {ev['week_year']}, неделя {ev['week_number']+1}"
            if ev.get("category_name"):
                meta += f"  •  {ev['category_name']}"
            ctk.CTkLabel(left, text=meta, text_color=COLOR_MUTED, font=ctk.CTkFont(size=12)).pack(anchor="w")
            if ev.get("note"):
                note_preview = (ev["note"][:80] + "…") if len(ev.get("note") or "") > 80 else ev.get("note")
                ctk.CTkLabel(left, text=note_preview, text_color=COLOR_MUTED, font=ctk.CTkFont(size=11)).pack(anchor="w")
            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.pack(side="right", padx=8)
            ctk.CTkButton(
                btns, text="→", width=36, height=32,
                command=lambda y=ev["week_year"], w=ev["week_number"]: self._goto_week(y, w)
            ).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="✕", width=36, height=32, fg_color="#7F1D1D", hover_color="#EF4444",
                          command=lambda eid=ev["id"]: (delete_event(eid), self._render_events(), self.refresh_data())).pack(side="left", padx=2)

    def _goto_week(self, life_year: int, week: int = 0):
        """Switch to calendar, scroll to year and highlight the specific week."""
        self._highlight_week = (life_year, week)
        self._switch_view("calendar")
        self.after(150, lambda: self._jump_to_specific(life_year))
        # Clear highlight after a few seconds
        self.after(4000, self._clear_highlight)

    def _clear_highlight(self):
        if self._highlight_week:
            self._highlight_week = None
            if self.current_view == "calendar":
                self._draw_grid()

    def _jump_to_specific(self, year: int):
        if self._grid_meta:
            meta = self._grid_meta
            total = meta["offset_y"] + meta["rows"] * meta["cell"]
            pos = (meta["offset_y"] + year * meta["cell"]) / max(1, total)
            self.canvas.yview_moveto(max(0, pos - 0.05))

    def _build_settings_view(self):
        frame = self.views["settings"]
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text="Настройки", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", padx=24, pady=(20, 12))
        self.settings_form = ctk.CTkFrame(frame, fg_color=COLOR_CARD, corner_radius=12)
        self.settings_form.pack(fill="x", padx=24, pady=8)

    def _render_settings(self):
        for w in self.settings_form.winfo_children():
            w.destroy()
        form = self.settings_form
        ctk.CTkLabel(form, text="Дата рождения", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=16, pady=(16, 2))
        self.birth_entry = ctk.CTkEntry(form, placeholder_text="ГГГГ-ММ-ДД")
        self.birth_entry.pack(fill="x", padx=16, pady=4)
        if self.birth_date:
            self.birth_entry.insert(0, self.birth_date.isoformat())
        ctk.CTkLabel(form, text="Продолжительность жизни (лет)", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=16, pady=(12, 2))
        self.life_entry = ctk.CTkEntry(form)
        self.life_entry.pack(fill="x", padx=16, pady=4)
        self.life_entry.insert(0, str(self.life_expectancy))
        ctk.CTkLabel(form, text="Первый день недели", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=16, pady=(12, 2))
        self.fdow_var = ctk.StringVar(value="Понедельник" if self.first_day == 0 else "Воскресенье")
        ctk.CTkOptionMenu(form, values=["Понедельник", "Воскресенье"], variable=self.fdow_var).pack(fill="x", padx=16, pady=4)

        def save_settings():
            bd = parse_date(self.birth_entry.get().strip())
            if not bd:
                messagebox.showerror("Ошибка", "Неверный формат даты. Используйте ГГГГ-ММ-ДД")
                return
            try:
                le = int(self.life_entry.get().strip())
                if not (40 <= le <= 120):
                    raise ValueError
            except ValueError:
                messagebox.showerror("Ошибка", "Продолжительность жизни: число от 40 до 120")
                return
            fd = 0 if self.fdow_var.get() == "Понедельник" else 6
            set_setting("birth_date", bd.isoformat())
            set_setting("life_expectancy", str(le))
            set_setting("first_day_of_week", str(fd))
            set_setting("setup_completed", "1")
            self.birth_date = bd
            self.life_expectancy = le
            self.first_day = fd
            self.settings = get_all_settings()
            self.refresh_data()
            messagebox.showinfo("Сохранено", "Настройки обновлены")

        ctk.CTkButton(form, text="Сохранить", command=save_settings, fg_color=COLOR_ACCENT).pack(pady=16, padx=16)

        backup_frame = ctk.CTkFrame(self.views["settings"], fg_color=COLOR_CARD, corner_radius=12)
        backup_frame.pack(fill="x", padx=24, pady=16)
        ctk.CTkLabel(backup_frame, text="Резервное копирование", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=16, pady=(12, 8))

        def do_export():
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="life_calendar_backup.json")
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(export_data())
                messagebox.showinfo("Готово", f"Экспортировано в\n{path}")

        def do_import():
            path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
            if not path:
                return
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                backup = import_data(content)
                self.settings = get_all_settings()
                self.birth_date = parse_date(self.settings.get("birth_date", ""))
                self.life_expectancy = int(self.settings.get("life_expectancy", "90") or 90)
                self.first_day = int(self.settings.get("first_day_of_week", "0") or 0)
                self.refresh_data()
                msg = "Данные успешно импортированы."
                if backup:
                    msg += f"\n\nАвтоматическая резервная копия:\n{backup}"
                messagebox.showinfo("Готово", msg)
            except ValueError as e:
                messagebox.showerror("Ошибка импорта", str(e))
            except Exception as e:
                messagebox.showerror("Ошибка импорта", f"Не удалось импортировать:\n{e}")

        bf = ctk.CTkFrame(backup_frame, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(bf, text="Экспорт JSON", command=do_export).pack(side="left", padx=4)
        ctk.CTkButton(bf, text="Импорт JSON", command=do_import).pack(side="left", padx=4)

    def _show_setup_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Добро пожаловать в Life Calendar")
        dialog.geometry("420x380")
        dialog.transient(self)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)

        ctk.CTkLabel(dialog, text="Настройка", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(24, 8))
        ctk.CTkLabel(dialog, text="Укажите дату рождения, чтобы увидеть\nсвою жизнь в неделях", text_color=COLOR_MUTED, justify="center").pack(pady=4)
        ctk.CTkLabel(dialog, text="Дата рождения (ГГГГ-ММ-ДД)").pack(anchor="w", padx=32, pady=(16, 2))
        birth_e = ctk.CTkEntry(dialog, placeholder_text="1990-05-15")
        birth_e.pack(fill="x", padx=32, pady=4)
        ctk.CTkLabel(dialog, text="Ожидаемая продолжительность жизни").pack(anchor="w", padx=32, pady=(12, 2))
        life_e = ctk.CTkEntry(dialog)
        life_e.insert(0, "90")
        life_e.pack(fill="x", padx=32, pady=4)

        def finish():
            bd = parse_date(birth_e.get().strip())
            if not bd or bd > date.today():
                messagebox.showerror("Ошибка", "Введите корректную дату рождения в прошлом")
                return
            try:
                le = int(life_e.get().strip())
                if not (40 <= le <= 120):
                    raise ValueError
            except ValueError:
                messagebox.showerror("Ошибка", "Число от 40 до 120")
                return
            set_setting("birth_date", bd.isoformat())
            set_setting("life_expectancy", str(le))
            set_setting("setup_completed", "1")
            self.birth_date = bd
            self.life_expectancy = le
            self.settings = get_all_settings()
            dialog.destroy()
            self.refresh_data()

        ctk.CTkButton(dialog, text="Начать", command=finish, fg_color=COLOR_ACCENT, height=40).pack(pady=24, padx=32, fill="x")


def main():
    app = LifeCalendarApp()
    app.mainloop()


if __name__ == "__main__":
    main()
