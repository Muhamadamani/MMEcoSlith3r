"""MM Eco Slith3r — tkinter GUI front-end  |  Shaping Matter Lab

Workflow:
  1. Browse a VTU file  → Preview shows all materials inside it.
  2. Choose mode        → Single material  OR  Multimaterial.
  3. Click Generate     → G-code saved to output/<timestamp>_<name>/.

Launch:
    python3 -m slith3r_python.gui
    python3 gui.py          (from the slith3r_python/ directory)
"""

from __future__ import annotations

import io
import os
import platform
import queue
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk

_HERE   = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

_GC_DIR         = Path(_PARENT) / 'slith3r' / 'begin_endGcodes'
_DEFAULT_BEGIN  = str(_GC_DIR / 'begin_text.gcode')           if (_GC_DIR / 'begin_text.gcode').exists()           else ''
_DEFAULT_END    = str(_GC_DIR / 'end_text.gcode')             if (_GC_DIR / 'end_text.gcode').exists()             else ''
_DEFAULT_TC_M1  = str(_GC_DIR / 'T2_to_T1_tool_change.gcode') if (_GC_DIR / 'T2_to_T1_tool_change.gcode').exists() else ''
_DEFAULT_TC_M2  = str(_GC_DIR / 'T1_to_T2_tool_change.gcode') if (_GC_DIR / 'T1_to_T2_tool_change.gcode').exists() else ''

# ── platform font ─────────────────────────────────────────────────────────────
_SYS = platform.system()
_FONT_UI   = ('SF Pro Text',   11) if _SYS == 'Darwin' else ('Segoe UI', 10)
_FONT_BOLD = ('SF Pro Text',   11, 'bold') if _SYS == 'Darwin' else ('Segoe UI', 10, 'bold')
_FONT_HEAD = ('SF Pro Display', 13, 'bold') if _SYS == 'Darwin' else ('Segoe UI', 12, 'bold')
_FONT_SMALL = ('SF Pro Text',  10) if _SYS == 'Darwin' else ('Segoe UI', 9)
_FONT_MONO  = ('SF Mono', 10) if _SYS == 'Darwin' else ('Consolas', 10)

# Apple color palette
_BG          = '#f5f5f7'    # page background
_CARD_BG     = '#ffffff'    # card/panel background
_BORDER      = '#d2d2d7'    # subtle border
_BLUE        = '#0071e3'    # primary action
_BLUE_DARK   = '#0051a2'    # hover
_RED         = '#ff3b30'    # destructive / stop
_RED_DARK    = '#cc2e26'
_GREEN       = '#34c759'    # success
_LABEL_SEC   = '#6e6e73'    # secondary label
_LABEL_PRI   = '#1d1d1f'    # primary label


# ── stdout redirect ───────────────────────────────────────────────────────────

class _QueueWriter(io.TextIOBase):
    def __init__(self, q: queue.Queue) -> None:
        self._q = q

    def write(self, text: str) -> int:
        if text:
            self._q.put(text)
        return len(text)

    def flush(self) -> None:
        pass


def _browse_file(entry: ttk.Entry, filetypes=None) -> None:
    path = filedialog.askopenfilename(filetypes=filetypes or [('All files', '*.*')])
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)


# ── styled card frame ─────────────────────────────────────────────────────────

class _Card(tk.Frame):
    """A white card with a subtle border and rounded appearance."""
    def __init__(self, parent, title='', **kw):
        super().__init__(parent, bg=_CARD_BG,
                         highlightbackground=_BORDER, highlightthickness=1,
                         **kw)
        if title:
            hdr = tk.Frame(self, bg=_CARD_BG)
            hdr.pack(fill='x', padx=14, pady=(10, 0))
            tk.Label(hdr, text=title, font=_FONT_BOLD,
                     bg=_CARD_BG, fg=_LABEL_PRI).pack(side='left')
            tk.Frame(self, bg=_BORDER, height=1).pack(fill='x', padx=14, pady=(6, 0))


class _SectionLabel(tk.Label):
    def __init__(self, parent, text, **kw):
        super().__init__(parent, text=text.upper(), font=_FONT_SMALL,
                         bg=_BG, fg=_LABEL_SEC, **kw)


# ── main window ───────────────────────────────────────────────────────────────

class SlitherGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MM Eco Slith3r")
        self.configure(bg=_BG)
        self.resizable(True, True)
        self.minsize(1080, 740)

        self._log_queue: queue.Queue              = queue.Queue()
        self._gen_thread: threading.Thread | None = None
        self._last_run_dir: Path | None           = None
        self._orig_stdout                         = sys.stdout
        self._vtu_data: dict | None               = None

        self._apply_style()
        self._build_ui()
        self._poll_log()

    def _apply_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass

        style.configure('.', font=_FONT_UI, background=_BG, foreground=_LABEL_PRI)
        style.configure('TFrame',       background=_BG)
        style.configure('TLabel',       background=_BG, foreground=_LABEL_PRI,
                        font=_FONT_UI)
        style.configure('TEntry',       fieldbackground='white', foreground=_LABEL_PRI,
                        font=_FONT_UI, bordercolor=_BORDER, lightcolor=_BORDER,
                        darkcolor=_BORDER)
        style.configure('TButton',      font=_FONT_UI, padding=(8, 4))
        style.configure('TCheckbutton', background=_BG, foreground=_LABEL_PRI,
                        font=_FONT_UI)
        style.configure('TRadiobutton', background=_CARD_BG, foreground=_LABEL_PRI,
                        font=_FONT_UI)

    # ── UI layout ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # title bar
        title_bar = tk.Frame(self, bg=_CARD_BG,
                             highlightbackground=_BORDER, highlightthickness=1)
        title_bar.pack(fill='x')

        # logo
        self._logo_img = None
        try:
            from PIL import Image, ImageTk
            _logo_path = Path(_HERE) / 'logo.png'
            if _logo_path.exists():
                _pil = Image.open(_logo_path).convert('RGBA').resize((36, 36), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(_pil)
                tk.Label(title_bar, image=self._logo_img,
                         bg=_CARD_BG).pack(side='left', padx=(14, 4), pady=8)
        except Exception:
            pass

        tk.Label(title_bar, text='MM Eco Slith3r', font=_FONT_HEAD,
                 bg=_CARD_BG, fg=_LABEL_PRI).pack(side='left', padx=(0, 10), pady=10)
        tk.Label(title_bar, text='Multimaterial Toolpath Generator',
                 font=_FONT_SMALL, bg=_CARD_BG, fg=_LABEL_SEC).pack(side='left', pady=10)
        tk.Label(title_bar, text='·',
                 font=_FONT_SMALL, bg=_CARD_BG, fg=_BORDER).pack(side='left', padx=6, pady=10)
        tk.Label(title_bar, text='Shaping Matter Lab',
                 font=_FONT_SMALL, bg=_CARD_BG, fg=_LABEL_SEC).pack(side='left', pady=10)

        # action buttons — top-right in title bar
        btn_area = tk.Frame(title_bar, bg=_CARD_BG)
        btn_area.pack(side='right', padx=18, pady=8)

        self._btn_stop = tk.Button(
            btn_area, text='Stop',
            font=_FONT_BOLD, bg='#fca5a5', fg='#7f1d1d', bd=0,
            activebackground='#f87171', activeforeground='#450a0a',
            padx=18, pady=6, relief='flat', cursor='hand2',
            state='disabled', command=self._on_stop)
        self._btn_stop.pack(side='right', padx=(6, 0))

        self._btn_gen = tk.Button(
            btn_area, text='Generate G-code',
            font=_FONT_BOLD, bg='#86efac', fg='#14532d', bd=0,
            activebackground='#4ade80', activeforeground='#052e16',
            padx=18, pady=6, relief='flat', cursor='hand2',
            command=self._on_generate)
        self._btn_gen.pack(side='right')

        # main content
        content = tk.Frame(self, bg=_BG)
        content.pack(fill='both', expand=True, padx=16, pady=12)

        left = tk.Frame(content, bg=_BG, width=420)
        left.pack(side='left', fill='y', padx=(0, 12))
        left.pack_propagate(False)

        right = tk.Frame(content, bg=_BG)
        right.pack(side='left', fill='both', expand=True)

        # log strip at bottom
        log_card = _Card(self)
        log_card.pack(fill='x', padx=16, pady=(0, 12))
        log_hdr = tk.Frame(log_card, bg=_CARD_BG)
        log_hdr.pack(fill='x', padx=10, pady=(8, 4))
        tk.Label(log_hdr, text='Console', font=_FONT_BOLD,
                 bg=_CARD_BG, fg=_LABEL_PRI).pack(side='left')
        tk.Button(log_hdr, text='Clear', font=_FONT_SMALL,
                  bg=_CARD_BG, fg=_LABEL_SEC, bd=0, padx=6, pady=2,
                  activebackground=_BG, cursor='hand2',
                  command=self._clear_log).pack(side='right')
        self._log_text = scrolledtext.ScrolledText(
            log_card, height=7, font=_FONT_MONO,
            state='disabled', wrap='word',
            bg='#1d1d1f', fg='#e5e5ea',
            insertbackground='white', relief='flat')
        self._log_text.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self._build_left(left)
        self._build_right(right)

    # ── left panel ────────────────────────────────────────────────────────────

    def _build_left(self, parent: tk.Frame) -> None:
        GC_FT = [('G-code', '*.gcode'), ('All', '*.*')]

        # scrollable canvas
        canvas = tk.Canvas(parent, bg=_BG, highlightthickness=0)
        sb     = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        inner    = tk.Frame(canvas, bg=_BG)
        inner_id = canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>',
                   lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',
                    lambda e: canvas.itemconfig(inner_id, width=e.width))
        canvas.bind_all('<MouseWheel>',
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))

        P = 6   # inner card padding

        # ── VTU file ──────────────────────────────────────────────────────────
        _SectionLabel(inner, text='File').pack(anchor='w', padx=2, pady=(0, 4))
        vtu_card = _Card(inner, title='VTU File')
        vtu_card.pack(fill='x', pady=(0, 12))

        body = tk.Frame(vtu_card, bg=_CARD_BG)
        body.pack(fill='x', padx=14, pady=10)

        file_row = tk.Frame(body, bg=_CARD_BG)
        file_row.pack(fill='x', pady=(0, 6))
        self._e_vtu = ttk.Entry(file_row, font=_FONT_SMALL)
        self._e_vtu.pack(side='left', fill='x', expand=True, padx=(0, 6))
        tk.Button(file_row, text='Browse…', font=_FONT_UI,
                  bg=_CARD_BG, fg=_BLUE, bd=0, padx=8, pady=4,
                  activebackground=_BG, cursor='hand2',
                  command=self._browse_vtu).pack(side='right')

        self._det_label = tk.Label(
            body, text='Select a VTU file to detect materials.',
            font=_FONT_SMALL, bg=_CARD_BG, fg=_LABEL_SEC,
            wraplength=350, justify='left', anchor='w')
        self._det_label.pack(fill='x', pady=(0, 6))

        tk.Button(body, text='Preview in panel →', font=_FONT_UI,
                  bg=_BLUE, fg='white', bd=0, padx=12, pady=5,
                  activebackground=_BLUE_DARK, activeforeground='white',
                  cursor='hand2', relief='flat',
                  command=self._preview_vtu).pack(anchor='w')

        # ── Mode ──────────────────────────────────────────────────────────────
        _SectionLabel(inner, text='Mode').pack(anchor='w', padx=2, pady=(0, 4))
        mode_card = _Card(inner, title='Processing Mode')
        mode_card.pack(fill='x', pady=(0, 12))

        mbody = tk.Frame(mode_card, bg=_CARD_BG)
        mbody.pack(fill='x', padx=14, pady=10)

        self._mode_var = tk.StringVar(value='multi')
        ttk.Radiobutton(mbody, text='Multimaterial  (two extruders, tool change)',
                        variable=self._mode_var, value='multi',
                        style='TRadiobutton').pack(anchor='w', pady=(0, 4))
        ttk.Radiobutton(mbody, text='Single material  (one extruder)',
                        variable=self._mode_var, value='single',
                        style='TRadiobutton').pack(anchor='w', pady=(0, 8))

        # Separator
        tk.Frame(mbody, bg=_BORDER, height=1).pack(fill='x', pady=(0, 8))

        # Material names
        grid = tk.Frame(mbody, bg=_CARD_BG)
        grid.pack(fill='x')
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(3, weight=1)

        tk.Label(grid, text='Material 1 name', font=_FONT_SMALL,
                 bg=_CARD_BG, fg=_LABEL_SEC).grid(
            row=0, column=0, sticky='w', padx=(0, 6), pady=3)
        self._e_mat1_name = ttk.Entry(grid, width=12, font=_FONT_UI)
        self._e_mat1_name.insert(0, 'mat1')
        self._e_mat1_name.grid(row=0, column=1, sticky='ew', padx=(0, 14), pady=3)

        tk.Label(grid, text='Material 2 name', font=_FONT_SMALL,
                 bg=_CARD_BG, fg=_LABEL_SEC).grid(
            row=0, column=2, sticky='w', padx=(0, 6), pady=3)
        self._e_mat2_name = ttk.Entry(grid, width=12, font=_FONT_UI)
        self._e_mat2_name.insert(0, 'mat2')
        self._e_mat2_name.grid(row=0, column=3, sticky='ew', pady=3)

        # ── Output ────────────────────────────────────────────────────────────
        _SectionLabel(inner, text='Output').pack(anchor='w', padx=2, pady=(0, 4))
        out_card = _Card(inner, title='Output Folder')
        out_card.pack(fill='x', pady=(0, 12))

        obody = tk.Frame(out_card, bg=_CARD_BG)
        obody.pack(fill='x', padx=14, pady=10)

        out_row = tk.Frame(obody, bg=_CARD_BG)
        out_row.pack(fill='x', pady=(0, 4))
        tk.Label(out_row, text='Base dir', font=_FONT_SMALL,
                 bg=_CARD_BG, fg=_LABEL_SEC).pack(side='left', padx=(0, 6))
        self._e_out_dir = ttk.Entry(out_row, font=_FONT_UI)
        self._e_out_dir.insert(0, 'output')
        self._e_out_dir.pack(side='left', fill='x', expand=True, padx=(0, 6))
        tk.Button(out_row, text='…', font=_FONT_UI,
                  bg=_CARD_BG, fg=_BLUE, bd=0, padx=6,
                  activebackground=_BG, cursor='hand2',
                  command=lambda: (d := filedialog.askdirectory()) and
                  (self._e_out_dir.delete(0, tk.END) or
                   self._e_out_dir.insert(0, d))).pack(side='right')
        tk.Label(obody, text='Saves to: <base>/<timestamp>_<case>/<case>.gcode',
                 font=_FONT_SMALL, bg=_CARD_BG, fg=_LABEL_SEC).pack(anchor='w')

        # ── G-code wrappers ───────────────────────────────────────────────────
        _SectionLabel(inner, text='G-code Wrappers').pack(anchor='w', padx=2, pady=(0, 4))
        gc_card = _Card(inner, title='G-code Files  (Prusa XL defaults pre-filled)')
        gc_card.pack(fill='x', pady=(0, 12))

        gcbody = tk.Frame(gc_card, bg=_CARD_BG)
        gcbody.pack(fill='x', padx=14, pady=10)
        gcbody.columnconfigure(1, weight=1)

        def _gc_row(row, label, default):
            tk.Label(gcbody, text=label, font=_FONT_SMALL,
                     bg=_CARD_BG, fg=_LABEL_SEC).grid(
                row=row, column=0, sticky='w', padx=(0, 8), pady=3)
            e = ttk.Entry(gcbody, font=_FONT_SMALL)
            e.insert(0, default)
            e.grid(row=row, column=1, sticky='ew', padx=(0, 6), pady=3)
            tk.Button(gcbody, text='…', font=_FONT_SMALL,
                      bg=_CARD_BG, fg=_BLUE, bd=0, padx=4,
                      activebackground=_BG, cursor='hand2',
                      command=lambda en=e: _browse_file(en, GC_FT)).grid(
                row=row, column=2, pady=3)
            return e

        self._e_begin_g  = _gc_row(0, 'Begin G-code',   _DEFAULT_BEGIN)
        self._e_end_g    = _gc_row(1, 'End G-code',     _DEFAULT_END)
        self._e_tc_mat1  = _gc_row(2, 'TC → Material 1 (T2→T1)', _DEFAULT_TC_M1)
        self._e_tc_mat2  = _gc_row(3, 'TC → Material 2 (T1→T2)', _DEFAULT_TC_M2)
        tk.Label(gcbody, text='Tool-change files only used in Multimaterial mode.',
                 font=_FONT_SMALL, bg=_CARD_BG, fg=_LABEL_SEC).grid(
            row=4, column=0, columnspan=3, sticky='w', pady=(6, 0))

        # ── Print parameters ──────────────────────────────────────────────────
        _SectionLabel(inner, text='Print Parameters').pack(anchor='w', padx=2, pady=(0, 4))
        par_card = _Card(inner, title='Parameters')
        par_card.pack(fill='x', pady=(0, 12))

        pbody = tk.Frame(par_card, bg=_CARD_BG)
        pbody.pack(fill='x', padx=14, pady=10)
        pbody.columnconfigure(1, weight=1)

        params = [
            ('Print thickness (mm)',    '_thickness_mm',    '10.0'),
            ('Upper spacing (mm)',      'upperbound',       '0.6'),
            ('Lower spacing (mm)',      'lowerbound',       '0.4'),
            ('Layer height (mm)',       'layer_height',     '0.2'),
            ('Integration step (mm)',   '_integ_step',      '0.3'),
            ('Print speed (mm/min)',    'print_speed',      '1200'),
            ('Travel speed (mm/min)',   'travel_speed',     '4500'),
            ('Travel threshold (mm)',   'thresh_traveldist', '2.0'),
            ('Retract dist (mm)',       'retract_dist',     '0.8'),
            ('Retract spd (mm/min)',    'retract_speed',    '2100'),
            ('Unretract spd (mm/min)', 'unretract_speed',  '1500'),
            ('Z hop (mm)',              'z_hop',            '1.0'),
            ('Origin X (mm)',           'x_printstart',     '10.0'),
            ('Origin Y (mm)',           'y_printstart',     '10.0'),
        ]
        self._param_map: dict[str, ttk.Entry] = {}

        # row counter that accounts for separator rows
        grid_row = 0
        for i, (label, key, default) in enumerate(params):
            tk.Label(pbody, text=label, font=_FONT_SMALL,
                     bg=_CARD_BG, fg=_LABEL_SEC).grid(
                row=grid_row, column=0, sticky='w', padx=(0, 8), pady=2)
            e = ttk.Entry(pbody, width=9, font=_FONT_UI)
            e.insert(0, default)
            e.grid(row=grid_row, column=1, sticky='w', padx=(0, 4), pady=2)
            self._param_map[key] = e
            grid_row += 1
            # visual separator after thickness
            if i == 0:
                tk.Frame(pbody, bg=_BORDER, height=1).grid(
                    row=grid_row, column=0, columnspan=2,
                    sticky='ew', pady=(2, 6))
                grid_row += 1

        self._frame_bool_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(pbody, text='Print boundary frame',
                        variable=self._frame_bool_var).grid(
            row=grid_row, column=0, columnspan=2, sticky='w', pady=(6, 0))


    # ── right panel ───────────────────────────────────────────────────────────

    def _build_right(self, parent: tk.Frame) -> None:
        try:
            import matplotlib
            matplotlib.use('TkAgg')
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure

            btn_row = tk.Frame(parent, bg=_BG)
            btn_row.pack(fill='x', padx=0, pady=(0, 8))
            tk.Button(btn_row, text='Show last results →',
                      font=_FONT_UI, bg=_CARD_BG, fg=_BLUE, bd=0,
                      padx=10, pady=5, relief='flat', cursor='hand2',
                      activebackground=_BG,
                      command=self._show_last_results).pack(side='right')
            tk.Label(btn_row, text='Preview', font=_FONT_HEAD,
                     bg=_BG, fg=_LABEL_PRI).pack(side='left')

            vis_card = _Card(parent)
            vis_card.pack(fill='both', expand=True)

            self._fig = Figure(figsize=(7, 5), dpi=96)
            self._fig.patch.set_facecolor('#f5f5f7')
            self._ax  = self._fig.add_subplot(111)
            self._ax.set_facecolor('#f0f4f8')
            self._ax.set_title('Browse a VTU file and click Preview',
                               fontsize=11, color='#6e6e73')
            self._ax.axis('off')
            self._fig.tight_layout()

            self._mpl_canvas = FigureCanvasTkAgg(self._fig, master=vis_card)
            self._mpl_canvas.draw()
            self._mpl_canvas.get_tk_widget().pack(
                fill='both', expand=True, padx=8, pady=8)
            self._has_mpl = True
        except Exception as exc:
            self._has_mpl = False
            tk.Label(parent, text=f'Matplotlib unavailable:\n{exc}',
                     bg=_BG, fg='red', font=_FONT_UI).pack(padx=8, pady=8)
            self._ax = None

    # ── VTU controls ──────────────────────────────────────────────────────────

    def _browse_vtu(self) -> None:
        path = filedialog.askopenfilename(
            title='Select VTU file',
            filetypes=[('VTU files', '*.vtu'), ('All files', '*.*')])
        if not path:
            return
        self._e_vtu.delete(0, tk.END)
        self._e_vtu.insert(0, path)
        self._vtu_data = None
        self._det_label.configure(
            text='Click "Preview in panel" to inspect the file.',
            fg=_LABEL_SEC)

    def _preview_vtu(self) -> None:
        path = self._e_vtu.get().strip()
        if not path:
            self._log('Select a VTU file first.\n')
            return
        if not self._has_mpl:
            return

        def _load():
            try:
                from vtu_pipeline import parse_vtu
                self._log_queue.put(f'Parsing {Path(path).name} …\n')
                data = parse_vtu(path)
                self.after(0, lambda: self._on_preview_loaded(data))
            except Exception as exc:
                import traceback
                self._log_queue.put(f'Preview error: {exc}\n{traceback.format_exc()}\n')

        threading.Thread(target=_load, daemon=True).start()

    def _on_preview_loaded(self, data: dict) -> None:
        self._vtu_data = data
        has_two = data['has_two_materials']

        if has_two:
            d1 = data['density']
            d2 = data['density2']
            n1 = int((d1 > 0.5).sum())
            n2 = int((d2 > 0.5).sum())
            n_void = len(d1) - n1 - n2
            mat1 = self._e_mat1_name.get().strip() or 'mat1'
            mat2 = self._e_mat2_name.get().strip() or 'mat2'
            msg = (f'2 materials detected — '
                   f'{mat1}: {n1} elements  ·  '
                   f'{mat2}: {n2} elements  ·  '
                   f'void: {n_void}')
        else:
            d1    = data['density']
            n1    = int((d1 > 0.5).sum())
            n_vd  = int((d1 <= 0.5).sum())
            msg   = f'1 material detected — solid: {n1} elements  ·  void: {n_vd}'

        self._det_label.configure(text=msg, fg='#34c759')
        self._log(msg + '\n')
        self._draw_vtu_preview(data)

    def _draw_vtu_preview(self, data: dict) -> None:
        ax = self._ax
        ax.cla(); ax.set_facecolor('#1a1a2e'); ax.set_aspect('equal')
        self._fig.patch.set_facecolor('#1a1a2e')

        c  = data['centroids']
        d1 = data['density']
        d2 = data.get('density2')
        THR = 0.5

        mat1 = self._e_mat1_name.get().strip() or 'mat1'
        mat2 = self._e_mat2_name.get().strip() or 'mat2'

        if d2 is None:
            void_  = c[d1 <= THR]
            solid_ = c[d1  > THR]
            if len(void_):
                ax.scatter(void_[:, 0],  void_[:, 1],  c='#444466', s=1, linewidths=0)
            if len(solid_):
                ax.scatter(solid_[:, 0], solid_[:, 1], c='#5efc8d', s=3,
                           linewidths=0, label=f'{mat1} ({len(solid_)})')
        else:
            is1   = d1 > THR
            is2   = d2 > THR
            void_ = c[~is1 & ~is2]
            m1_   = c[is1]
            m2_   = c[is2]
            if len(void_):
                ax.scatter(void_[:, 0], void_[:, 1], c='#444466', s=1, linewidths=0)
            if len(m1_):
                ax.scatter(m1_[:, 0], m1_[:, 1], c='#5efc8d', s=3,
                           linewidths=0, label=f'{mat1} ({len(m1_)})')
            if len(m2_):
                ax.scatter(m2_[:, 0], m2_[:, 1], c='#63b3ed', s=3,
                           linewidths=0, label=f'{mat2} ({len(m2_)})')

        ax.legend(markerscale=5, loc='upper right', fontsize=8,
                  facecolor='#1a1a2e', labelcolor='white', edgecolor='none')
        ax.set_xlabel('x (mm)', color='#aaaacc', fontsize=9)
        ax.set_ylabel('y (mm)', color='#aaaacc', fontsize=9)
        ax.tick_params(colors='#aaaacc', labelsize=8)
        for spine in ax.spines.values():
            spine.set_edgecolor('#333355')
        n_mat = 2 if data['has_two_materials'] else 1
        ax.set_title(f'{Path(self._e_vtu.get()).name}  —  {n_mat} material(s)',
                     color='white', fontsize=10)
        self._fig.tight_layout()
        self._mpl_canvas.draw()

    # ── result display ────────────────────────────────────────────────────────

    def _show_last_results(self) -> None:
        if not self._has_mpl or self._last_run_dir is None:
            self._log('No completed run yet.\n'); return
        for fname in ['combined_courses.png', 'courses.png', 'streamlines_all.png']:
            p = self._last_run_dir / fname
            if p.exists():
                self._show_image_in_panel(p); return
        self._log('No result images found in last run directory.\n')

    def _show_image_in_panel(self, path: Path) -> None:
        try:
            import numpy as np
            from PIL import Image
            img = np.array(Image.open(path))
            ax  = self._ax
            ax.cla(); ax.imshow(img); ax.axis('off')
            ax.set_title(path.name, fontsize=10, color=_LABEL_PRI)
            self._fig.patch.set_facecolor('white')
            self._fig.tight_layout()
            self._mpl_canvas.draw()
        except Exception as e:
            self._log(f'Could not show image: {e}\n')

    def _make_line_callback(self):
        if not self._has_mpl:
            return None
        ax     = self._ax
        canvas = self._mpl_canvas
        inited = [False]

        def cb(xy, seed, n_added, lnum):
            def _draw():
                if not inited[0]:
                    ax.cla()
                    ax.set_facecolor('#1a1a2e')
                    ax.set_aspect('equal')
                    self._fig.patch.set_facecolor('#1a1a2e')
                    inited[0] = True
                ax.plot(xy[:, 0], xy[:, 1], '-', lw=0.5, alpha=0.7, color='#63b3ed')
                ax.plot(seed[0], seed[1], '.', ms=1.5, color='#fc8181')
                ax.set_title(f'Generating streamlines — {n_added}',
                             color='white', fontsize=10)
                ax.tick_params(colors='#aaaacc', labelsize=8)
                canvas.draw_idle()
            self.after(0, _draw)

        return cb

    # ── log ───────────────────────────────────────────────────────────────────

    def _log(self, text: str) -> None:
        self._log_text.configure(state='normal')
        self._log_text.insert('end', text)
        self._log_text.see('end')
        self._log_text.configure(state='disabled')

    def _clear_log(self) -> None:
        self._log_text.configure(state='normal')
        self._log_text.delete('1.0', 'end')
        self._log_text.configure(state='disabled')

    def _poll_log(self) -> None:
        try:
            while True:
                self._log(self._log_queue.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    # ── params ────────────────────────────────────────────────────────────────

    def _collect_params(self) -> tuple[dict, float, float]:
        opt = {}
        for key, entry in self._param_map.items():
            try:
                opt[key] = float(entry.get())
            except ValueError:
                opt[key] = 0.0
        integ_step   = opt.pop('_integ_step',  0.3)
        thickness_mm = opt.pop('_thickness_mm', 10.0)
        opt['frameBool'] = 1 if self._frame_bool_var.get() else 0
        return opt, integ_step, thickness_mm

    # ── generate ──────────────────────────────────────────────────────────────

    def _on_generate(self) -> None:
        if self._gen_thread and self._gen_thread.is_alive():
            return

        vtu_path = self._e_vtu.get().strip()
        if not vtu_path:
            self._log('ERROR: Browse and preview a VTU file first.\n'); return

        mode         = self._mode_var.get()
        mat1_name    = self._e_mat1_name.get().strip() or 'mat1'
        mat2_name    = self._e_mat2_name.get().strip() or 'mat2'
        prt_opt, integ_step, thickness_mm = self._collect_params()

        begin_g  = self._e_begin_g.get().strip()  or None
        end_g    = self._e_end_g.get().strip()    or None
        tc_mat1  = self._e_tc_mat1.get().strip()  or None
        tc_mat2  = self._e_tc_mat2.get().strip()  or None
        tc_files: dict | None = {}
        if tc_mat1: tc_files['mat1'] = tc_mat1
        if tc_mat2: tc_files['mat2'] = tc_mat2
        if not tc_files: tc_files = None

        base_dir  = self._e_out_dir.get().strip() or 'output'
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        case_name = Path(vtu_path).stem
        run_dir   = Path(base_dir) / f'{timestamp}_{case_name}'
        run_dir.mkdir(parents=True, exist_ok=True)
        self._last_run_dir = run_dir
        out_path           = str(run_dir / f'{case_name}.gcode')

        self._btn_gen.configure(state='disabled', bg='#d1d5db')
        self._btn_stop.configure(state='normal')
        self._log('\n' + '─' * 60 + '\n')
        self._log(f'Mode:  {"Multimaterial" if mode == "multi" else "Single material"}\n')
        self._log(f'VTU:   {Path(vtu_path).name}\n')
        self._log(f'Out:   {run_dir}\n')
        if mode == 'multi':
            self._log(f'Mat 1: {mat1_name}  ·  Mat 2: {mat2_name}\n')
        self._log(f'Thickness: {thickness_mm} mm\n\n')

        self._orig_stdout = sys.stdout
        sys.stdout = _QueueWriter(self._log_queue)

        line_cb = self._make_line_callback()

        def _run():
            try:
                if mode == 'single':
                    from vtu_pipeline import run_single_material_from_vtu
                    run_single_material_from_vtu(
                        vtu_path=vtu_path,
                        out_path=out_path,
                        prt_opt=prt_opt,
                        integ_step=integ_step,
                        n_max=200,
                        begin_gcode=begin_g,
                        end_gcode=end_g,
                        run_dir=run_dir,
                        line_callback=line_cb,
                    )
                else:
                    from vtu_pipeline import run_from_vtu
                    run_from_vtu(
                        vtu_path=vtu_path,
                        out_path=out_path,
                        prt_opt=prt_opt,
                        integ_step=integ_step,
                        n_max=200,
                        begin_gcode=begin_g,
                        end_gcode=end_g,
                        tool_change_files=tc_files,
                        mat1_name=mat1_name,
                        mat2_name=mat2_name,
                        thickness_mm=thickness_mm,
                        plot=False,
                        ax=None,
                        run_dir=run_dir,
                        line_callback=line_cb,
                    )
                self._log_queue.put(f'\n✓  Done  →  {run_dir}\n')
            except Exception as exc:
                import traceback
                self._log_queue.put(f'\nERROR: {exc}\n{traceback.format_exc()}\n')
            finally:
                self._finish_generate()

        self._gen_thread = threading.Thread(target=_run, daemon=True)
        self._gen_thread.start()

    def _on_stop(self) -> None:
        self._log('\n[Stop requested — current step finishes before stopping]\n')

    def _finish_generate(self) -> None:
        sys.stdout = self._orig_stdout
        self.after(0, self._restore_buttons)

    def _restore_buttons(self) -> None:
        self._btn_gen.configure(state='normal', bg='#86efac')
        self._btn_stop.configure(state='disabled')
        if self._has_mpl and self._last_run_dir is not None:
            for fname in ['combined_courses.png', 'courses.png', 'streamlines_all.png']:
                p = self._last_run_dir / fname
                if p.exists():
                    self._show_image_in_panel(p); break


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    SlitherGUI().mainloop()


if __name__ == '__main__':
    main()
