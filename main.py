"""
main.py
מפענח T9 עברי – ממשק משתמש גרפי
Hebrew T9 Decoder – Graphical User Interface

Entry point and full Tkinter GUI.
"""

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
import sys

from t9_decoder import decode_full, KEY_MAP
from hebrew_dict import load_dictionary_async, is_loaded, word_count

# ─── Palette ──────────────────────────────────────────────────────────────────
C = {
    "bg":         "#F5F7FA",
    "surface":    "#FFFFFF",
    "border":     "#D0D7DE",
    "primary":    "#1565C0",
    "primary_lt": "#E3F2FD",
    "secondary":  "#455A64",
    "success":    "#2E7D32",
    "error":      "#C62828",
    "warn":       "#F57F17",
    "text":       "#1A1A2E",
    "hint":       "#90A4AE",
    "numpad_bg":  "#ECEFF1",
}

KEY_LABELS: dict[str, str] = {
    "2": "ד ה ו",  "3": "א ב ג",  "4": "מ ם נ ן",  "5": "י כ ך ל",
    "6": "ז ח ט",  "7": "ר ש ת",  "8": "צ ץ ק",    "9": "ס ע פ ף",
    "0": "רווח",
}


# ─── Font helpers ─────────────────────────────────────────────────────────────

def _best_hebrew_font() -> str:
    available = set(tkFont.families())
    for name in ("David", "Narkisim", "Frank Ruehl", "Arial Hebrew", "Miriam"):
        if name in available:
            return name
    return "Arial"


# ─── Main application ─────────────────────────────────────────────────────────

class T9App:
    HEB_FONT: str = ""           # resolved at runtime

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        T9App.HEB_FONT = _best_hebrew_font()

        self.root.title("מפענח T9 עברי")
        self.root.configure(bg=C["bg"])
        self.root.resizable(True, True)
        self.root.minsize(620, 660)

        # State
        self._word_data:    list[dict] = []
        self._chosen_words: list[str | None] = []

        # Build
        self._style()
        self._build()
        self._center_window(730, 720)
        self._load_dict()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _style(self) -> None:
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Hint.TLabel", font=("Segoe UI", 8),
                    background=C["bg"], foreground=C["hint"])
        s.configure("Section.TLabel", font=("Segoe UI", 9, "bold"),
                    background=C["bg"], foreground=C["secondary"])

    def _center_window(self, w: int, h: int) -> None:
        self.root.update_idletasks()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── UI construction ───────────────────────────────────────────────────────

    def _build(self) -> None:
        wrap = tk.Frame(self.root, bg=C["bg"])
        wrap.pack(fill="both", expand=True, padx=16, pady=12)

        self._header(wrap)
        self._section_input(wrap)
        self._decode_button(wrap)
        self._section_output(wrap)
        self._section_alternatives(wrap)
        self._section_bottom(wrap)
        self._statusbar()

    def _header(self, p: tk.Frame) -> None:
        f = tk.Frame(p, bg=C["bg"])
        f.pack(fill="x", pady=(0, 8))
        tk.Label(f, text="מפענח T9 עברי",
                 font=("Segoe UI", 17, "bold"),
                 bg=C["bg"], fg=C["primary"]).pack(side="right")
        tk.Label(f, text="Hebrew T9 Decoder",
                 font=("Segoe UI", 10), bg=C["bg"], fg=C["hint"]).pack(
                     side="right", padx=(0, 10), pady=(6, 0))

    # ── Input section ─────────────────────────────────────────────────────────

    def _section_input(self, p: tk.Frame) -> None:
        box = self._lframe(p, "קלט")
        box.pack(fill="x", pady=(0, 6))

        row = tk.Frame(box, bg=C["bg"])
        row.pack(fill="x", padx=10, pady=(8, 4))

        self._input_var = tk.StringVar()
        self._input_var.trace_add("write", self._on_input_change)

        self._entry = tk.Entry(
            row, textvariable=self._input_var,
            font=("Courier New", 13), justify="left",
            relief="solid", bd=1, bg=C["surface"],
            highlightthickness=1, highlightcolor=C["primary"],
            fg=C["text"],
        )
        self._entry.pack(side="left", fill="x", expand=True, ipady=6)
        self._entry.bind("<Return>", lambda _: self._decode())

        tk.Button(row, text="✕ נקה",
                  font=("Segoe UI", 9), relief="flat",
                  bg=C["bg"], fg=C["secondary"], cursor="hand2",
                  padx=10, pady=6, activebackground=C["primary_lt"],
                  command=self._clear).pack(side="left", padx=(6, 0))

        tk.Label(box, bg=C["bg"], fg=C["hint"],
                 font=("Segoe UI", 8),
                 text="לדוגמה:  6725076270255037623  →  חתול שחור הלך ברחוב"
                 ).pack(anchor="e", padx=10, pady=(0, 8))

    # ── Decode button ─────────────────────────────────────────────────────────

    def _decode_button(self, p: tk.Frame) -> None:
        f = tk.Frame(p, bg=C["bg"])
        f.pack(pady=(0, 8))
        self._btn_decode = tk.Button(
            f, text="◀  פענח",
            font=("Segoe UI", 12, "bold"),
            bg=C["primary"], fg="white", relief="flat",
            cursor="hand2", padx=32, pady=9,
            state="disabled",
            activebackground="#1976D2", activeforeground="white",
            command=self._decode,
        )
        self._btn_decode.pack()

    # ── Output section ────────────────────────────────────────────────────────

    def _section_output(self, p: tk.Frame) -> None:
        box = self._lframe(p, "תוצאה")
        box.pack(fill="x", pady=(0, 6))

        ctrl = tk.Frame(box, bg=C["bg"])
        ctrl.pack(fill="x", padx=10, pady=(8, 2))

        self._btn_copy = tk.Button(
            ctrl, text="📋 העתק",
            font=("Segoe UI", 9), relief="flat",
            bg=C["bg"], fg=C["secondary"], cursor="hand2",
            padx=8, pady=4, activebackground=C["primary_lt"],
            command=self._copy,
        )
        self._btn_copy.pack(side="left")

        surf = tk.Frame(box, bg=C["surface"], relief="solid", bd=1,
                        highlightbackground=C["border"], highlightthickness=1)
        surf.pack(fill="x", padx=10, pady=(0, 10))

        self._result_txt = tk.Text(
            surf, font=(T9App.HEB_FONT, 20),
            height=3, wrap="word", relief="flat",
            bg=C["surface"], fg=C["text"],
            padx=14, pady=10, state="disabled", cursor="arrow",
        )
        self._result_txt.pack(fill="both")
        self._result_txt.tag_configure("rtl", justify="right")

    # ── Alternatives section ──────────────────────────────────────────────────

    def _section_alternatives(self, p: tk.Frame) -> None:
        self._alt_box = self._lframe(p, "חלופות")
        self._alt_box.pack(fill="x", pady=(0, 6))
        self._alt_inner = tk.Frame(self._alt_box, bg=C["bg"])
        self._alt_inner.pack(fill="x", padx=10, pady=8)
        ttk.Label(self._alt_inner, text="פענח רצף כדי לראות חלופות",
                  style="Hint.TLabel").pack()

    # ── Bottom: numpad + key map ──────────────────────────────────────────────

    def _section_bottom(self, p: tk.Frame) -> None:
        row = tk.Frame(p, bg=C["bg"])
        row.pack(fill="x", pady=(0, 4))
        self._numpad(row)
        self._keymap(row)

    def _numpad(self, p: tk.Frame) -> None:
        box = self._lframe(p, "מקלדת")
        box.pack(side="left", padx=(0, 8))
        inner = tk.Frame(box, bg=C["bg"])
        inner.pack(padx=10, pady=8)

        layout = [["1","2","3"],["4","5","6"],["7","8","9"],["⌫","0",""]]
        for row in layout:
            rf = tk.Frame(inner, bg=C["bg"])
            rf.pack(pady=2)
            for key in row:
                if key == "":
                    tk.Frame(rf, bg=C["bg"], width=46, height=1).pack(side="left", padx=2)
                    continue
                hint = " ".join(KEY_MAP.get(key, [])[:2]) if key not in ("0","⌫","1") else ""
                label = f"{key}\n{hint}" if hint else key
                cmd = self._backspace if key == "⌫" else (lambda k=key: self._append(k))
                tk.Button(
                    rf, text=label, font=(T9App.HEB_FONT, 8),
                    width=4, height=2, relief="flat",
                    bg=C["surface"], fg=C["text"], cursor="hand2",
                    activebackground=C["primary_lt"],
                    bd=1, highlightbackground=C["border"], highlightthickness=1,
                    command=cmd,
                ).pack(side="left", padx=2)

    def _keymap(self, p: tk.Frame) -> None:
        box = self._lframe(p, "מיפוי מקשים")
        box.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(box, bg=C["bg"])
        inner.pack(fill="both", padx=10, pady=8)

        col_a = tk.Frame(inner, bg=C["bg"])
        col_a.pack(side="left", fill="both", expand=True)
        col_b = tk.Frame(inner, bg=C["bg"])
        col_b.pack(side="left", fill="both", expand=True)

        items = list(KEY_LABELS.items())
        for i, (k, letters) in enumerate(items):
            parent = col_a if i < 5 else col_b
            r = tk.Frame(parent, bg=C["bg"])
            r.pack(fill="x", pady=1)
            tk.Label(r, text=f"{k}:", font=("Segoe UI", 9, "bold"),
                     bg=C["bg"], fg=C["primary"], width=2, anchor="w").pack(side="left")
            tk.Label(r, text=letters, font=(T9App.HEB_FONT, 10),
                     bg=C["bg"], fg=C["text"]).pack(side="left")

    # ── Status bar ────────────────────────────────────────────────────────────

    def _statusbar(self) -> None:
        bar = tk.Frame(self.root, bg="#ECEFF1", height=26)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self._status_dot = tk.Label(bar, text="●", bg="#ECEFF1", fg=C["warn"],
                                     font=("Segoe UI", 9))
        self._status_dot.pack(side="right", padx=(0, 6), pady=3)

        self._status_var = tk.StringVar(value="מאתחל...")
        tk.Label(bar, textvariable=self._status_var, bg="#ECEFF1",
                 fg=C["secondary"], font=("Segoe UI", 9),
                 anchor="e").pack(side="right", pady=3)

    # ── Dictionary loading ────────────────────────────────────────────────────

    def _load_dict(self) -> None:
        load_dictionary_async(
            progress_cb=lambda m: self.root.after(0, lambda msg=m: self._status_var.set(msg)),
            done_cb=lambda ok, m: self.root.after(0, lambda: self._on_dict_done(ok, m)),
        )

    def _on_dict_done(self, ok: bool, msg: str) -> None:
        self._status_var.set(msg)
        if ok:
            self._status_dot.config(fg=C["success"])
            self._btn_decode.config(state="normal")
        else:
            self._status_dot.config(fg=C["error"])
            self._btn_decode.config(
                text="⟳ נסה שוב", state="normal",
                command=self._retry_load,
            )

    def _retry_load(self) -> None:
        self._btn_decode.config(state="disabled", text="◀  פענח",
                                 command=self._decode)
        self._status_var.set("מנסה שוב...")
        self._load_dict()

    # ── Input interactions ────────────────────────────────────────────────────

    def _on_input_change(self, *_) -> None:
        val = self._input_var.get()
        clean = "".join(c for c in val if c.isdigit())
        if clean != val:
            self._input_var.set(clean)

    def _append(self, digit: str) -> None:
        self._input_var.set(self._input_var.get() + digit)
        self._entry.icursor(tk.END)

    def _backspace(self) -> None:
        v = self._input_var.get()
        if v:
            self._input_var.set(v[:-1])

    def _clear(self) -> None:
        self._input_var.set("")
        self._set_result("")
        self._refresh_alternatives([])

    # ── Decode ────────────────────────────────────────────────────────────────

    def _decode(self) -> None:
        seq = self._input_var.get().strip()
        if not seq:
            return
        if not is_loaded():
            self._status_var.set("המילון עדיין נטען, אנא המתן...")
            return

        result, word_data = decode_full(seq)
        self._word_data    = word_data
        self._chosen_words = [d["best"] for d in word_data]
        self._set_result(result)
        self._refresh_alternatives(word_data)

    def _set_result(self, text: str) -> None:
        self._result_txt.config(state="normal")
        self._result_txt.delete("1.0", tk.END)
        if text:
            self._result_txt.insert("1.0", text, "rtl")
        self._result_txt.config(state="disabled")

    # ── Alternatives ──────────────────────────────────────────────────────────

    def _refresh_alternatives(self, word_data: list[dict]) -> None:
        for w in self._alt_inner.winfo_children():
            w.destroy()

        if not word_data:
            ttk.Label(self._alt_inner, text="פענח רצף כדי לראות חלופות",
                      style="Hint.TLabel").pack()
            return

        for idx, data in enumerate(word_data):
            row = tk.Frame(self._alt_inner, bg=C["bg"])
            row.pack(fill="x", pady=2)

            tk.Label(row, text=f"{data['segment']}:",
                     font=("Courier New", 9), bg=C["bg"],
                     fg=C["hint"], anchor="w", width=9).pack(side="left")

            # Candidates: dict matches preferred, fallback to valid forms
            candidates = data["dictionary_matches"] or data["valid_candidates"][:6]

            if not candidates:
                tk.Label(row, text="[לא נמצא במילון]",
                         font=("Segoe UI", 9), bg=C["bg"],
                         fg=C["error"]).pack(side="right")
                continue

            chosen = self._chosen_words[idx] if idx < len(self._chosen_words) else None
            for word in candidates[:8]:
                selected = word == chosen
                btn = tk.Button(
                    row, text=word,
                    font=(T9App.HEB_FONT, 10, "bold" if selected else "normal"),
                    bg=C["primary_lt"] if selected else C["surface"],
                    fg=C["primary"] if selected else C["text"],
                    relief="flat", cursor="hand2",
                    padx=7, pady=2, bd=1,
                    highlightbackground=C["primary"] if selected else C["border"],
                    highlightthickness=1,
                    activebackground=C["primary_lt"],
                    command=lambda i=idx, w=word: self._pick(i, w),
                )
                btn.pack(side="right", padx=2)

    def _pick(self, word_idx: int, word: str) -> None:
        if word_idx < len(self._chosen_words):
            self._chosen_words[word_idx] = word
        result = " ".join(
            w if w else f"[?]" for w in self._chosen_words
        )
        self._set_result(result)
        self._refresh_alternatives(self._word_data)

    # ── Copy ──────────────────────────────────────────────────────────────────

    def _copy(self) -> None:
        text = self._result_txt.get("1.0", tk.END).strip()
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._btn_copy.config(text="✓ הועתק!")
        self.root.after(1800, lambda: self._btn_copy.config(text="📋 העתק"))

    # ── Helper ────────────────────────────────────────────────────────────────

    @staticmethod
    def _lframe(parent: tk.Frame, label: str) -> tk.Frame:
        """Create a labelled flat frame (replacement for ttk.LabelFrame with style control)."""
        outer = tk.Frame(parent, bg=C["border"], bd=0)
        # Title strip
        title_bar = tk.Frame(outer, bg=C["bg"])
        title_bar.pack(fill="x")
        tk.Label(title_bar, text=f"  {label}  ",
                 font=("Segoe UI", 8, "bold"),
                 bg=C["bg"], fg=C["secondary"]).pack(side="right")
        tk.Frame(title_bar, bg=C["border"], height=1).pack(fill="x", side="bottom")
        # Content area
        inner = tk.Frame(outer, bg=C["bg"])
        inner.pack(fill="both", expand=True)
        outer._content = inner   # type: ignore[attr-defined]
        return inner


# ─── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    root = tk.Tk()

    # Windows-only DPI awareness
    try:
        from ctypes import windll  # type: ignore
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # Ensure proper RTL rendering on Windows
    try:
        root.tk.call("tk", "scaling", 1.0)
    except Exception:
        pass

    app = T9App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
