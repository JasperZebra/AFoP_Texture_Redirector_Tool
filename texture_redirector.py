"""
Texture Redirector
==================
Scans your game resource folder for .mgraphobject files,
shows them in the left panel, and mirrors your mod folder
contents in the right panel.

Place this script alongside AFOP_Gear_Key.json.
"""

import sys, os, json, re, shutil, threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
GEAR_JSON_PATH  = "AFOP_Gear_Key.json"
PREFS_JSON_PATH = "texture_redirector_prefs.json"

# Texture suffixes we care about renaming (others like dn_* are generic, skip)
TEXTURE_SUFFIXES = ("_d.dds", "_n.dds", "_m.dds", "_reg_mask.dds", "_mask.dds", "_region_mask.dds")

# ── Colours ────────────────────────────────────────────────────────────────────
BG       = "#0e0f14"
PANEL    = "#161822"
BORDER   = "#2a2d3e"
ACCENT   = "#4fc3f7"
ACCENT2  = "#80cbc4"
WARN     = "#ffb74d"
SUCCESS  = "#a5d6a7"
ERROR    = "#ef9a9a"
TEXT     = "#e8eaf6"
MUTED    = "#757997"
ENTRY_BG = "#1e2030"
BTN_BG   = "#263859"
BTN_HOV  = "#2e4470"
MONO     = "Consolas"


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def load_gear_data():
    p = get_base_dir() / GEAR_JSON_PATH
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f).get("gear", {})
    return {}


def load_prefs():
    p = get_base_dir() / PREFS_JSON_PATH
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_prefs(prefs):
    p = get_base_dir() / PREFS_JSON_PATH
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    except Exception:
        pass


def build_stem_index(gear_data):
    """mgraphobject stem (lowercase) -> enriched entry dict."""
    index = {}
    for slot, entries in gear_data.items():
        for entry in entries:
            for mg in entry.get("mgraphobject", []):
                index[mg.lower()] = {"slot": slot, **entry}
    return index


def scan_folder(folder: str):
    """Return list of Path objects for every .mgraphobject found recursively."""
    hits = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".mgraphobject"):
                hits.append(Path(root) / f)
    return hits


def find_textures_in_folder(folder: str, texture_names: list) -> dict:
    """
    Walk folder recursively and check which texture filenames exist.
    Returns { filename: Path|None } -- None means not found.
    """
    index = {}
    for root, _, files in os.walk(folder):
        for f in files:
            index[f.lower()] = Path(root) / f
    return {t: index.get(t.lower()) for t in texture_names}


def extract_dds_from_binary(mgraph_path: Path) -> list:
    """
    Parse a .mgraphobject binary and extract all embedded DDS filenames
    (just the filename, not the full path) that are targeted textures.
    Returns a deduplicated list preserving order of first appearance.
    """
    try:
        data = mgraph_path.read_bytes()
    except Exception:
        return []
    seen = set()
    results = []
    for m in re.finditer(rb'[^\x00]{4,512}\.dds\x00', data):
        try:
            full_path = m.group(0)[:-1].decode("ascii")
        except UnicodeDecodeError:
            continue
        fname = full_path.split("/")[-1].split("\\")[-1]
        if fname.lower() not in seen:
            seen.add(fname.lower())
            results.append(fname)
    return results


def is_targeted_texture(filename: str) -> bool:
    """Return True if this texture filename ends with a suffix we rename."""
    low = filename.lower()
    return any(low.endswith(s) for s in TEXTURE_SUFFIXES)


def get_texture_suffix(filename: str) -> str:
    """Return the matched suffix (e.g. '_d.dds') or '' if none."""
    low = filename.lower()
    for s in TEXTURE_SUFFIXES:
        if low.endswith(s):
            return s
    return ""


def new_texture_name(old_name: str, new_stem: str) -> tuple:
    """
    Build the new texture filename by replacing the stem before the suffix.
    e.g. old_name='g_res_torso_base_02a_d.dds', new_stem='mymod_top'
         -> 'mymod_top_d.dds'

    Returns (new_name, error_str). error_str is '' on success.
    The new name must be exactly the same byte length as the old one.
    """
    suffix = get_texture_suffix(old_name)
    if not suffix:
        return old_name, ""   # not a targeted texture, keep as-is

    new_name = new_stem + suffix
    if len(new_name.encode("ascii")) != len(old_name.encode("ascii")):
        diff = len(new_name) - len(old_name)
        sign = "+" if diff > 0 else ""
        return new_name, (
            f"'{old_name}' ({len(old_name)} chars)  ->  "
            f"'{new_name}' ({len(new_name)} chars)  [{sign}{diff}]"
        )
    return new_name, ""


def patch_binary_string(data: bytes, old_str: str, new_str: str) -> bytes:
    """
    Replace every null-terminated occurrence of old_str with new_str in binary data.
    new_str must be <= old_str in byte length; remainder is zero-padded.
    Raises ValueError if new_str is longer.
    """
    old_b = old_str.encode("ascii")
    new_b = new_str.encode("ascii")
    if len(new_b) > len(old_b):
        raise ValueError(f"New string longer than old: {new_str!r} > {old_str!r}")
    # Pad to same length with null bytes
    new_b_padded = new_b + b"\x00" * (len(old_b) - len(new_b))

    result = bytearray(data)
    search = old_b
    i = 0
    while True:
        idx = result.find(search, i)
        if idx == -1:
            break
        result[idx:idx + len(old_b)] = new_b_padded
        i = idx + len(old_b)
    return bytes(result)


def patch_mgraphobject(data: bytes, tex_renames: dict) -> bytes:
    """
    Patch a .mgraphobject binary, replacing every DDS path that contains
    a texture we're renaming.

    tex_renames: { old_filename_stem: new_filename_stem }
    e.g. { 'g_res_torso_base_02a_d': 'mymod_top_d' }

    We search for the full filename (with .dds) anywhere in the binary.
    """
    for old_name, new_name in tex_renames.items():
        if old_name == new_name:
            continue
        try:
            data = patch_binary_string(data, old_name, new_name)
        except ValueError as e:
            raise ValueError(f"Cannot patch '{old_name}' -> '{new_name}': {e}")
    return data


# ── Widgets ────────────────────────────────────────────────────────────────────

class FileList(tk.Frame):
    """Searchable, filterable list of .mgraphobject files."""

    def __init__(self, parent, stem_index, on_select=None, **kw):
        super().__init__(parent, bg=BG, **kw)
        self._stem_index = stem_index
        self._on_select  = on_select
        self._all_items  = []
        self._filtered   = []
        self._iid_map    = {}

        # Search bar
        sf = tk.Frame(self, bg=ENTRY_BG, highlightbackground=BORDER, highlightthickness=1)
        sf.pack(fill="x", pady=(0, 5))
        tk.Label(sf, text="⌕", bg=ENTRY_BG, fg=MUTED,
                 font=("Segoe UI", 11)).pack(side="left", padx=(7, 2))
        self._sv = tk.StringVar()
        self._sv.trace_add("write", lambda *_: self._refresh())
        tk.Entry(sf, textvariable=self._sv, bg=ENTRY_BG, fg=TEXT,
                 insertbackground=ACCENT, relief="flat",
                 font=("Segoe UI", 9), bd=0
                 ).pack(side="left", fill="x", expand=True, pady=6, padx=(0, 6))

        # Slot filter + count
        fr = tk.Frame(self, bg=BG)
        fr.pack(fill="x", pady=(0, 5))
        tk.Label(fr, text="Slot:", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        self._slot_var = tk.StringVar(value="ALL SLOTS")
        self._slot_cb  = ttk.Combobox(fr, textvariable=self._slot_var,
                                       values=["ALL SLOTS"], state="readonly",
                                       width=12, font=("Segoe UI", 9))
        self._slot_cb.pack(side="left", padx=(5, 0))
        self._slot_cb.bind("<<ComboboxSelected>>", lambda _: self._refresh())
        self._count_var = tk.StringVar()
        tk.Label(fr, textvariable=self._count_var, bg=BG, fg=MUTED,
                 font=("Segoe UI", 8)).pack(side="right")

        # Treeview as a single-line-per-item list
        wrap = tk.Frame(self, bg=BORDER, highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(fill="both", expand=True)
        sb = tk.Scrollbar(wrap, bg=PANEL, troughcolor=BG, activebackground=ACCENT)
        sb.pack(side="right", fill="y")
        self._tv = ttk.Treeview(wrap, style="FileList.Treeview",
                                 columns=("display",), show="tree",
                                 yscrollcommand=sb.set, selectmode="browse")
        self._tv.column("#0",      width=0,   stretch=False)
        self._tv.column("display", width=300, stretch=True)
        self._tv.pack(side="left", fill="both", expand=True)
        sb.config(command=self._tv.yview)
        self._tv.bind("<<TreeviewSelect>>", self._on_tv_select)
        self._tv.tag_configure("name_row", foreground=TEXT,  font=("Segoe UI", 9, "bold"))
        self._tv.tag_configure("custom",   foreground=WARN,  font=("Segoe UI", 9, "bold"))

    def load(self, paths: list):
        slots_seen = set()
        items = []
        for p in sorted(paths, key=lambda x: x.stem.lower()):
            stem  = p.stem.lower()
            entry = self._stem_index.get(stem, {})
            slot  = entry.get("slot", "Custom").upper()
            slots_seen.add(slot)
            items.append({
                "path":         p,
                "stem":         p.stem,
                "filename":     p.name,
                "slot":         slot,
                "ui_names":     entry.get("ui_names", []),
                "textures":     entry.get("textures", [])[:-1],
                "models":       entry.get("models", []),
                "mgraphobject": entry.get("mgraphobject", []),
            })
        self._all_items = items
        slots = ["ALL SLOTS"] + sorted(s.upper() for s in slots_seen)
        self._slot_cb.config(values=slots)
        self._slot_var.set("ALL SLOTS")
        self._refresh()

    def _refresh(self):
        q    = self._sv.get().strip().lower()
        slot = self._slot_var.get()
        self._filtered = [
            i for i in self._all_items
            if (slot == "ALL SLOTS" or i["slot"] == slot)
            and (not q
                 or q in i["stem"].lower()
                 or any(q in n.lower() for n in i["ui_names"]))
        ]
        for row in self._tv.get_children():
            self._tv.delete(row)
        self._iid_map = {}
        for idx, item in enumerate(self._filtered):
            if item["ui_names"]:
                label = f"[{item['slot'].upper()}]  {item['ui_names'][0]}  ({item['stem']})"
                tag   = "name_row"
            else:
                label = f"[CUSTOM]  ({item['stem']})"
                tag   = "custom"
            iid = self._tv.insert("", "end", values=(label,), tags=(tag,))
            self._iid_map[iid] = idx
        self._count_var.set(f"{len(self._filtered)} files")

    def _on_tv_select(self, _):
        sel = self._tv.selection()
        if not sel:
            return
        idx = self._iid_map.get(sel[0])
        if idx is not None and self._on_select:
            self._on_select(self._filtered[idx])

    def get_selected(self):
        sel = self._tv.selection()
        if not sel:
            return None
        idx = self._iid_map.get(sel[0])
        return self._filtered[idx] if idx is not None else None

    def clear(self):
        self._all_items = []
        self._filtered  = []
        self._iid_map   = {}
        for row in self._tv.get_children():
            self._tv.delete(row)
        self._count_var.set("")


class InfoCard(tk.Frame):
    """Detail panel for a selected .mgraphobject entry."""

    def __init__(self, parent, title, title_color, **kw):
        super().__init__(parent, bg=PANEL, highlightbackground=BORDER,
                         highlightthickness=1, **kw)
        hdr = tk.Frame(self, bg=PANEL)
        hdr.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(hdr, text=title, bg=PANEL, fg=title_color,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self._slot_lbl = tk.Label(hdr, text="", bg=PANEL, fg=MUTED,
                                   font=("Segoe UI", 8))
        self._slot_lbl.pack(side="right")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        self._text = tk.Text(self, bg=PANEL, fg=TEXT, relief="flat",
                              font=(MONO, 10), bd=0, state="disabled",
                              wrap="word", padx=10, pady=8,
                              highlightthickness=0, height=9)
        self._text.pack(fill="both", expand=True)
        self._text.tag_config("key",     foreground=MUTED)
        self._text.tag_config("val",     foreground=TEXT)
        self._text.tag_config("acc",     foreground=ACCENT,  font=(MONO, 10, "bold"))
        self._text.tag_config("acc2",    foreground=ACCENT2)
        self._text.tag_config("warn",    foreground=WARN)
        self._text.tag_config("found",   foreground=SUCCESS)
        self._text.tag_config("missing", foreground=ERROR)
        self.clear()

    def clear(self):
        self._slot_lbl.config(text="")
        self._write([("key", "No file selected.")])

    def show(self, item: dict, texture_results: dict = None):
        self._slot_lbl.config(text=item["slot"])
        lines = [("key", "File:\n"), ("acc", f"  {item['filename']}\n")]
        if item["ui_names"]:
            lines += [("key", "\nKnown as:\n")]
            for n in item["ui_names"]:
                lines += [("val", f"  {n}\n")]
        else:
            lines += [("key", "\n"), ("warn", "  This is a custom file.\n")]
        if item["textures"]:
            lines += [("key", "\nTextures:\n")]
            for t in item["textures"]:
                if texture_results is None:
                    lines += [("acc2", f"  {t}\n")]
                elif texture_results.get(t):
                    lines += [("found", f"  ✓  {t}\n")]
                else:
                    lines += [("missing", f"  ✗  {t}\n")]
            if texture_results is not None:
                found  = sum(1 for v in texture_results.values() if v)
                total  = len(texture_results)
                tag    = "found" if found == total else ("warn" if found else "missing")
                lines += [("key", "\n"), (tag, f"  {found}/{total} found\n")]
        self._write(lines)

    def _write(self, segs):
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        for tag, txt in segs:
            self._text.insert("end", txt, tag)
        self._text.config(state="disabled")


# ── Main App ───────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AFoP Texture Redirector | Made By: Jasper_Zebra | Version 1.0")
        self.geometry("1400x860")
        self.minsize(1000, 640)
        self.configure(bg=BG)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox",
                         fieldbackground=ENTRY_BG, background=ENTRY_BG,
                         foreground=TEXT, selectbackground=BTN_BG,
                         selectforeground=ACCENT, bordercolor=BORDER,
                         arrowcolor=ACCENT, relief="flat")
        style.map("TCombobox", fieldbackground=[("readonly", ENTRY_BG)])
        style.configure("FileList.Treeview",
                         background=ENTRY_BG, fieldbackground=ENTRY_BG,
                         foreground=TEXT, rowheight=26,
                         borderwidth=0, relief="flat", indent=0)
        style.configure("FileList.Treeview.Heading",
                         background=PANEL, foreground=MUTED,
                         font=("Segoe UI", 8), relief="flat")
        style.map("FileList.Treeview",
                  background=[("selected", BTN_BG)],
                  foreground=[("selected", ACCENT)])

        self._gear_data       = load_gear_data()
        self._stem_index      = build_stem_index(self._gear_data)
        self._prefs           = load_prefs()
        self._sel_res         = None
        self._sel_mod         = None
        self._texture_results = {}

        self._build_ui()
        self._auto_restore()

    # ── UI ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Title bar
        bar = tk.Frame(self, bg=PANEL, height=48)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text="TEXTURE REDIRECTOR",
                 bg=PANEL, fg=ACCENT, font=(MONO, 13, "bold"),
                 padx=16).pack(side="left", fill="y")
        tk.Label(bar, text="Avatar: Frontiers of Pandora  ·  texture mod utility",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9)
                 ).pack(side="left", fill="y")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # Path rows
        self._res_var = tk.StringVar(value=self._prefs.get("resource_folder", ""))
        self._mod_var = tk.StringVar(value=self._prefs.get("mod_folder", ""))
        self._make_path_row("Resource folder  (game files root):",
                             self._res_var, self._browse_resource)
        self._make_path_row("Mod output folder:",
                             self._mod_var, self._browse_mod)
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # Main body
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True)

        # ── Left: resource files
        left = tk.Frame(main, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=12)

        lhdr = tk.Frame(left, bg=BG)
        lhdr.pack(fill="x", pady=(0, 6))
        tk.Label(lhdr, text="RESOURCE FOLDER",
                 bg=BG, fg=ACCENT,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self._res_badge = tk.Label(lhdr, text="Not scanned",
                                    bg=BG, fg=MUTED, font=("Segoe UI", 8))
        self._res_badge.pack(side="right")

        self._res_list = FileList(left, self._stem_index,
                                   on_select=self._on_res_select)
        self._res_list.pack(fill="both", expand=True)

        tk.Frame(main, bg=BORDER, width=1).pack(side="left", fill="y", pady=12)

        # ── Centre: cards + rename + actions
        mid = tk.Frame(main, bg=BG, width=320)
        mid.pack(side="left", fill="both", padx=6, pady=12)
        mid.pack_propagate(False)

        self._res_card = InfoCard(mid, "RESOURCE FILE", ACCENT)
        self._res_card.pack(fill="both", expand=True, pady=(0, 6))

        # ── Rename panel
        rename_frame = tk.Frame(mid, bg=PANEL, highlightbackground=BORDER,
                                 highlightthickness=1)
        rename_frame.pack(fill="x", pady=(0, 6))

        rename_hdr = tk.Frame(rename_frame, bg=PANEL)
        rename_hdr.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(rename_hdr, text="NEW GRAPH FILE NAME", bg=PANEL, fg=WARN,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self._mg_len_lbl = tk.Label(rename_hdr, text="", bg=PANEL, fg=MUTED,
                                     font=(MONO, 8))
        self._mg_len_lbl.pack(side="right")

        tk.Frame(rename_frame, bg=BORDER, height=1).pack(fill="x")

        entry_row = tk.Frame(rename_frame, bg=PANEL)
        entry_row.pack(fill="x", padx=10, pady=(8, 4))
        self._new_mg_var = tk.StringVar()
        self._new_mg_var.trace_add("write", self._on_mg_name_change)
        tk.Entry(entry_row, textvariable=self._new_mg_var,
                 bg=ENTRY_BG, fg=TEXT,
                 insertbackground=ACCENT, relief="flat",
                 font=(MONO, 10), bd=4
                 ).pack(fill="x")

        # Derived texture names preview
        tk.Frame(rename_frame, bg=BORDER, height=1).pack(fill="x", pady=(4, 0))
        tex_hdr = tk.Frame(rename_frame, bg=PANEL)
        tex_hdr.pack(fill="x", padx=10, pady=(6, 2))
        tk.Label(tex_hdr, text="DERIVED TEXTURE NAMES", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        self._tex_len_lbl = tk.Label(tex_hdr, text="", bg=PANEL, fg=MUTED,
                                      font=(MONO, 8))
        self._tex_len_lbl.pack(side="right")
        self._tex_preview = tk.Text(rename_frame, bg=PANEL, fg=ACCENT2,
                                     font=(MONO, 8), relief="flat", bd=0,
                                     state="disabled", height=4, padx=10,
                                     highlightthickness=0)
        self._tex_preview.tag_config("ok",  foreground=ACCENT2)
        self._tex_preview.tag_config("err", foreground=ERROR)
        self._tex_preview.pack(fill="x", pady=(0, 8))

        # ── Buttons
        tk.Button(mid, text="⤓  COPY & RENAME TO MOD FOLDER",
                  bg=BTN_BG, fg=ACCENT,
                  activebackground=BTN_HOV, activeforeground=ACCENT,
                  relief="flat", font=(MONO, 10, "bold"),
                  cursor="hand2", pady=10,
                  command=self._copy_to_mod
                  ).pack(fill="x", pady=(0, 4))

        tk.Button(mid, text="↺  Refresh panels",
                  bg=PANEL, fg=MUTED,
                  activebackground=BTN_HOV, activeforeground=TEXT,
                  relief="flat", font=("Segoe UI", 8),
                  cursor="hand2", pady=6,
                  command=self._refresh_both
                  ).pack(fill="x")

        tk.Frame(main, bg=BORDER, width=1).pack(side="left", fill="y", pady=12)

        # ── Right: mod files
        right = tk.Frame(main, bg=BG)
        right.pack(side="left", fill="both", expand=True, padx=(6, 12), pady=12)

        rhdr = tk.Frame(right, bg=BG)
        rhdr.pack(fill="x", pady=(0, 6))
        tk.Label(rhdr, text="MOD FOLDER",
                 bg=BG, fg=SUCCESS,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self._mod_badge = tk.Label(rhdr, text="Not set",
                                    bg=BG, fg=MUTED, font=("Segoe UI", 8))
        self._mod_badge.pack(side="right")

        self._mod_list = FileList(right, self._stem_index,
                                   on_select=self._on_mod_select)
        self._mod_list.pack(fill="both", expand=True)

        # Status bar
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        self._status_var = tk.StringVar(value="Set your resource and mod folders to begin.")
        self._status_lbl = tk.Label(self, textvariable=self._status_var,
                                     bg=PANEL, fg=MUTED,
                                     font=("Segoe UI", 8), anchor="w",
                                     padx=12, pady=5)
        self._status_lbl.pack(fill="x")

    def _make_path_row(self, label, var, cmd):
        row = tk.Frame(self, bg=PANEL, height=42)
        row.pack(fill="x")
        row.pack_propagate(False)
        tk.Label(row, text=label, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9), padx=12).pack(side="left", fill="y")
        tk.Entry(row, textvariable=var, bg=ENTRY_BG, fg=TEXT,
                 insertbackground=ACCENT, relief="flat",
                 font=(MONO, 8), bd=4
                 ).pack(side="left", fill="both", expand=True, pady=7)
        tk.Button(row, text="Browse...", bg=BTN_BG, fg=TEXT,
                  activebackground=BTN_HOV, activeforeground=ACCENT,
                  relief="flat", font=("Segoe UI", 9), padx=10,
                  cursor="hand2", command=cmd
                  ).pack(side="left", padx=(6, 12), pady=7)

    # ── Stem change / validation ───────────────────────────────────────────────

    def _derive_texture_names(self, new_mg_stem: str) -> list:
        """
        Given a new graph file stem, derive new texture filenames.
        Finds the longest common prefix between the old graph stem and the
        first texture stem, then swaps that prefix in every texture stem.
        Returns list of (old_tex_name, new_tex_name) for targeted textures.
        """
        item = self._sel_res
        if not item:
            return []
        old_mg_stem = item["path"].stem
        targeted    = [t for t in item.get("textures", []) if is_targeted_texture(t)]
        if not targeted:
            return []

        first_tex_stem = targeted[0][: -len(get_texture_suffix(targeted[0]))]
        prefix_len = 0
        for i in range(min(len(old_mg_stem), len(first_tex_stem))):
            if old_mg_stem[i] == first_tex_stem[i]:
                prefix_len = i + 1
            else:
                break

        old_prefix = old_mg_stem[:prefix_len]
        new_prefix = new_mg_stem[:prefix_len] if len(new_mg_stem) >= prefix_len else new_mg_stem

        pairs = []
        for t in targeted:
            suffix   = get_texture_suffix(t)
            tex_stem = t[: -len(suffix)]
            if tex_stem.startswith(old_prefix):
                new_tex_name = new_prefix + tex_stem[len(old_prefix):] + suffix
            else:
                new_tex_name = new_mg_stem + suffix  # fallback
            pairs.append((t, new_tex_name))
        return pairs

    def _on_mg_name_change(self, *_):
        """Live-validate new graph name and show derived texture names."""
        new_mg = self._new_mg_var.get().strip()
        item   = self._sel_res

        self._tex_preview.config(state="normal")
        self._tex_preview.delete("1.0", "end")

        if not item or not new_mg:
            self._mg_len_lbl.config(text="")
            self._tex_len_lbl.config(text="")
            self._tex_preview.config(state="disabled")
            return

        # Graph name length check
        old_mg = item["path"].stem
        diff   = len(new_mg) - len(old_mg)
        sign   = "+" if diff > 0 else ""
        self._mg_len_lbl.config(
            text=f"{len(new_mg)} chars  ({sign}{diff})" if diff != 0 else f"{len(new_mg)} chars  ✓",
            fg=ERROR if diff != 0 else SUCCESS)

        # Derive and preview texture names
        pairs = self._derive_texture_names(new_mg)
        err_count = sum(1 for old_t, new_t in pairs if len(new_t) != len(old_t))
        for old_t, new_t in pairs:
            tag = "err" if len(new_t) != len(old_t) else "ok"
            self._tex_preview.insert("end", f"  {new_t}\n", tag)

        self._tex_len_lbl.config(
            text=f"{err_count} length error(s)" if err_count else "✓ all match",
            fg=ERROR if err_count else SUCCESS)
        self._tex_preview.config(state="disabled")

    # ── Folder browsing ────────────────────────────────────────────────────────

    def _browse_resource(self):
        d = filedialog.askdirectory(title="Select Game Resource Folder",
                                     initialdir=self._res_var.get() or None)
        if d:
            self._res_var.set(d)
            self._prefs["resource_folder"] = d
            save_prefs(self._prefs)
            self._scan_resource(d)

    def _browse_mod(self):
        d = filedialog.askdirectory(title="Select Mod Output Folder",
                                     initialdir=self._mod_var.get() or None)
        if d:
            self._mod_var.set(d)
            self._prefs["mod_folder"] = d
            save_prefs(self._prefs)
            self._scan_mod(d)

    # ── Scanning ───────────────────────────────────────────────────────────────

    def _auto_restore(self):
        res = self._res_var.get().strip()
        mod = self._mod_var.get().strip()
        if res and os.path.isdir(res):
            self._scan_resource(res)
        if mod and os.path.isdir(mod):
            self._scan_mod(mod)

    def _scan_resource(self, folder):
        self._res_badge.config(text="Scanning...", fg=WARN)
        self._set_status("Scanning resource folder...")
        def worker():
            paths = scan_folder(folder)
            self.after(0, self._finish_resource_scan, paths)
        threading.Thread(target=worker, daemon=True).start()

    def _finish_resource_scan(self, paths):
        self._res_list.load(paths)
        n = len(paths)
        self._res_badge.config(
            text=f"{n} file{'s' if n != 1 else ''} found",
            fg=SUCCESS if n else WARN)
        self._set_status(
            f"Resource folder scanned -- {n} .mgraphobject file(s) found.",
            color=SUCCESS if n else WARN)

    def _scan_mod(self, folder):
        self._mod_badge.config(text="Scanning...", fg=WARN)
        def worker():
            paths = scan_folder(folder)
            self.after(0, self._finish_mod_scan, paths)
        threading.Thread(target=worker, daemon=True).start()

    def _finish_mod_scan(self, paths):
        self._mod_list.load(paths)
        n = len(paths)
        self._mod_badge.config(
            text=f"{n} file{'s' if n != 1 else ''}" if n else "Empty",
            fg=SUCCESS if n else MUTED)

    def _refresh_both(self):
        res = self._res_var.get().strip()
        mod = self._mod_var.get().strip()
        if res and os.path.isdir(res):
            self._scan_resource(res)
        if mod and os.path.isdir(mod):
            self._scan_mod(mod)

    # ── Selection callbacks ────────────────────────────────────────────────────

    def _on_res_select(self, item):
        self._sel_res         = item
        self._texture_results = {}
        self._res_card.show(item, texture_results=None)
        self._set_status(
            f"Resource: {item['filename']}  [{item['slot']}]  -- searching textures...")
        # Pre-fill with the current graph file stem
        self._new_mg_var.set(item["path"].stem)
        res = self._res_var.get().strip()

        if item["slot"] == "CUSTOM":
            # No JSON entry — extract DDS names from the binary itself
            def worker():
                dds_names = extract_dds_from_binary(item["path"])
                # Drop the last entry (generic fabric/detail normal, same as JSON items)
                if dds_names:
                    dds_names = dds_names[:-1]
                # Update the item's texture list so the rest of the logic works
                item["textures"] = dds_names
                results = find_textures_in_folder(res, dds_names) if res and os.path.isdir(res) else {}
                self.after(0, self._on_texture_search_done, item, results)
            threading.Thread(target=worker, daemon=True).start()
        else:
            # Known item — use texture list from JSON
            textures = item.get("textures", [])
            if res and os.path.isdir(res) and textures:
                def worker():
                    results = find_textures_in_folder(res, textures)
                    self.after(0, self._on_texture_search_done, item, results)
                threading.Thread(target=worker, daemon=True).start()
            else:
                self._res_card.show(item, texture_results={})

    def _on_texture_search_done(self, item, results):
        if self._sel_res is not item:
            return
        self._texture_results = results
        self._res_card.show(item, texture_results=results)
        found = sum(1 for v in results.values() if v)
        total = len(results)
        self._set_status(
            f"Resource: {item['filename']}  [{item['slot']}]  -- {found}/{total} textures found",
            color=SUCCESS if found == total else (WARN if found else ERROR))

    def _on_mod_select(self, item):
        self._sel_mod = item
        self._set_status(f"Mod: {item['filename']}  [{item['slot']}]")

    # ── Copy & rename ──────────────────────────────────────────────────────────

    def _copy_to_mod(self):
        item = self._sel_res
        if not item:
            messagebox.showwarning("Nothing selected",
                                   "Select a file in the Resource Folder panel first.")
            return
        mod = self._mod_var.get().strip()
        if not mod:
            messagebox.showerror("No mod folder", "Set a Mod Output Folder first.")
            return

        new_mg_stem = self._new_mg_var.get().strip()
        if not new_mg_stem:
            messagebox.showerror("No name", "Enter a new graph file name.")
            return

        res_root    = Path(self._res_var.get().strip())
        mod_root    = Path(mod)
        src         = item["path"]
        old_mg_stem = src.stem

        # ── Derive texture rename map from graph name
        tex_pairs = self._derive_texture_names(new_mg_stem)  # [(old, new), ...]
        length_errors = [
            f"'{o}' ({len(o)})  ->  '{n}' ({len(n)})"
            for o, n in tex_pairs if len(n) != len(o)
        ]
        if length_errors:
            messagebox.showerror(
                "Length mismatch",
                "Derived texture names must be exactly the same length as originals.\n\n"
                + "\n".join(length_errors))
            return

        tex_rename_map = {o: n for o, n in tex_pairs}  # old_filename -> new_filename

        # ── Graph file length warning
        new_mg_name = new_mg_stem + src.suffix
        if len(new_mg_stem) != len(old_mg_stem):
            diff = len(new_mg_stem) - len(old_mg_stem)
            sign = "+" if diff > 0 else ""
            if not messagebox.askyesno(
                "Graph file name length mismatch",
                f"The graph filename has a different length:\n\n"
                f"  Old: '{old_mg_stem}'  ({len(old_mg_stem)} chars)\n"
                f"  New: '{new_mg_stem}'  ({len(new_mg_stem)} chars)  [{sign}{diff}]\n\n"
                f"This may cause issues if the filename is referenced elsewhere. Continue anyway?"):
                return

        # ── Determine output paths — new files go in the same folder as originals
        dst_mgraph = src.parent / new_mg_name

        # Texture destinations: same folder the original texture lives in, renamed
        tex_copies = []  # (src_path, dst_path, old_name, new_name)
        for old_name, new_name in tex_rename_map.items():
            tex_src = self._texture_results.get(old_name)
            if tex_src is None:
                continue  # not found on disk, skip
            dst_tex = tex_src.parent / new_name
            tex_copies.append((tex_src, dst_tex, old_name, new_name))

        # ── Overwrite check
        all_dsts = [dst_mgraph] + [d for _, d, _, _ in tex_copies]
        existing = [d for d in all_dsts if d.exists()]
        if existing:
            names = "\n".join(f"  {p.name}" for p in existing)
            if not messagebox.askyesno(
                "Overwrite?",
                f"These files already exist in the mod folder:\n\n{names}\n\nOverwrite?"):
                return

        # ── Read and patch the .mgraphobject binary
        try:
            mg_data = src.read_bytes()
        except Exception as e:
            messagebox.showerror("Read error", f"Could not read {src.name}:\n{e}")
            return

        try:
            # Patch every targeted texture filename reference inside the binary
            for old_name, new_name in tex_rename_map.items():
                mg_data = patch_binary_string(mg_data, old_name, new_name)
        except ValueError as e:
            messagebox.showerror("Patch error", str(e))
            return

        # ── Execute all writes
        ok, failed = [], []

        # Write patched + renamed .mgraphobject
        try:
            dst_mgraph.write_bytes(mg_data)
            ok.append(dst_mgraph.name)
        except Exception as e:
            failed.append(f"{dst_mgraph.name}: {e}")

        # Copy textures (renamed)
        for tex_src, tex_dst, old_name, new_name in tex_copies:
            try:
                shutil.copy2(tex_src, tex_dst)
                ok.append(f"{old_name} -> {new_name}")
            except Exception as e:
                failed.append(f"{old_name}: {e}")

        if ok and not failed:
            self._set_status(
                f"Done -- {len(ok)} file(s) written with renamed textures.",
                color=SUCCESS)
        elif ok:
            self._set_status(f"Done with errors -- {len(failed)} failed.", color=WARN)
            messagebox.showwarning("Partial success", "Failed:\n" + "\n".join(failed))
        else:
            self._set_status("Copy failed.", color=ERROR)
            messagebox.showerror("Copy failed", "\n".join(failed))

        self._scan_mod(mod)

    # ── Status ─────────────────────────────────────────────────────────────────

    def _set_status(self, msg, color=MUTED):
        self._status_var.set(msg)
        self._status_lbl.config(fg=color)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    App().mainloop()