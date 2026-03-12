![GitHub release (latest by date)](https://img.shields.io/github/v/release/JasperZebra/AFoP_Texture_Redirector_Tool?style=for-the-badge&logo=github&color=00ffff&logoColor=white&labelColor=1a4d66)
![Total Downloads](https://img.shields.io/github/downloads/JasperZebra/AFoP_Texture_Redirector_Tool/total?style=for-the-badge&logo=github&color=00ffff&logoColor=white&labelColor=1a4d66)
![Platform](https://img.shields.io/badge/platform-windows-00ffff?style=for-the-badge&logo=windows&logoColor=00ffff&labelColor=1a4d66)
![Made for](https://img.shields.io/badge/made%20for-Avatar:_Frontiers_of_Pandora-00ffff?style=for-the-badge&logo=gamepad&logoColor=00ffff&labelColor=1a4d66)
![Tool Type](https://img.shields.io/badge/type-texture%20redirector-00ffff?style=for-the-badge&logo=package&logoColor=00ffff&labelColor=1a4d66)

# Texture Redirector
### Avatar: Frontiers of Pandora — Modding Tool

<img width="1397" height="1033" alt="image" src="https://github.com/user-attachments/assets/e3230e57-7322-435b-8c72-0aa566e29582" />

A GUI tool for redirecting `.mgraphobject` texture references. Pick a game file, give it a new name, and the tool copies it to your mod folder with all internal texture paths automatically patched — no hex editing required.

---

## How to Use

### Step 1 — Set your folders
- **Resource Folder** — your game's unpacked resource directory **(root of game dir, "AFOP" folder).**
- **Mod Output Folder** — this is your "workshop" folder **(your edited files will go in here)**.

### Step 2 — Find your file
Browse the **left panel** to find the `.mgraphobject` you want to redirect. Use the filters to narrow things down:
- 🔍 **Search bar** — filter by **filename** or **in-game** item name
- **Slot dropdown** — filter by object slot **(Gear, Weapon, Character, Prop, etc.)**
- **Package dropdown** — filter by content package **(base_game, dlc1, dlc2, dlc3, rogue, etc.)**

> 💡 **Tip:** Right-click any entry in the list to copy its filename stem to your clipboard.

Each entry is colour-coded so you can tell at a glance what **slot** and **package** it belongs to:

| Color | Slot |
|--------|------|
| 🟣 Lavender | Gear |
| 🔴 Red-pink | Weapon |
| 🟢 Teal | Character |
| 🟠 Amber | Prop |
| 🔵 Cyan | Effect |
| 🟩 Green | Building |
| 🩷 Pink | Player Realization |
| 🟡 Yellow | Light |
| ⬜ Light blue-grey | Interior / Interior Walls |
| ⚫ Grey | Road / Road Parts / Sidewalk / Walls |
| 🤎 Taupe | Microdetail |

| Color | Package |
|--------|---------|
| 🔵 Sky blue | base_game |
| 🟢 Green | dlc1 |
| 🟠 Orange | dlc2 |
| 🩷 Pink | dlc3 |
| 🟣 Purple | rogue |
| 🩵 Cyan | snowdrop |
| 🤎 Taupe | vendor |

When you select a file, the **centre panel** shows its details — including which textures were found on disk (shown in green) or are missing (shown in red). The tool reads texture paths **directly from the binary** of the `.mgraphobject` file, so this list always reflects what's actually embedded, not just what the index guesses. If no embedded textures are found, it falls back to deriving standard names (`_d`, `_n`, `_m`, `_reg_mask`) from the graph filename.

### Step 3 — Name your output file
Type a new stem in the **NEW GRAPH FILE NAME** box. The tool will:
- Show a live character count and flag if the length doesn't match the original
- Automatically derive new texture filenames based on your new stem
- Warn you if the target filename belongs to a different slot than the source

The **DERIVED TEXTURE NAMES** section below the name field shows every texture that will be renamed. Each row has two checkboxes:

| Checkbox | Label | What it does |
|----------|-------|--------------|
| ☑ (left) | **linked** | Auto-derive this texture's name from the new graph stem. Only shown for textures that are related to the graph file. Uncheck to skip this texture and leave it unchanged. |
| ☑ (right) | **edit** | Enable manual naming for this texture. Unchecks "linked" and lets you type a custom stem directly in the row. The field turns red if the length doesn't match the original. |

> ⚠️ Texture and graph filenames must be the **same byte length** as the originals. The tool will warn you before writing anything if there's a mismatch. A length diff badge (e.g. `+2`) is shown next to any row with a length error.

**Gear swap only mode** — tick this checkbox if you only want to rename the `.mgraphobject` file itself without touching any textures **(useful when swapping one gear piece for another).** In this mode, the length check for the graph filename is also skipped.

### Step 4 — Copy to mod folder
Click **`⤓ COPY & RENAME TO MOD FOLDER`**. The tool will:
1. Read the source `.mgraphobject` binary
2. Patch all internal DDS path references to point to your new texture names (preserving the original folder structure)
3. Write the renamed `.mgraphobject` to your mod folder
4. Copy and rename all found textures into their correct subfolder paths within the mod folder

If any output files already exist, the tool will ask before overwriting.

The right panel shows everything currently in your mod folder. Use the **↺ Refresh panels** button to rescan both folders at any time if you've made changes outside the tool.

---

## Features

- **Dual-panel browser** — resource folder on the left, mod folder on the right
- **Colour-coded lists** — slot and package colours match the AFoP Gear Swap tool for a consistent look across your toolkit
- **Slot + Package filters** — quickly narrow down thousands of files to exactly what you need
- **Right-click to copy** — right-click any list entry to copy its filename stem to your clipboard
- **Auto texture discovery** — scans the resource folder and shows which textures are found or missing
- **Binary DDS parsing** — reads texture paths directly from the `.mgraphobject` binary; falls back to guessing standard names if none are found
- **Live rename preview** — see derived texture names and length validation before committing
- **Per-texture controls** — individually link/unlink or manually name each texture via two-checkbox rows
- **Slot mismatch warning** — flags if the target graph file belongs to a different slot than the source, so you know before writing
- **Folder structure preservation** — textures are copied to the correct subfolder paths, not just dumped in the mod root
- **Undo/Redo** — `Ctrl+Z` / `Ctrl+Y` (or `Ctrl+Shift+Z`) in the name entry field
- **Preferences saved** — remembers your folder paths between sessions