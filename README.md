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
- **Mod Output Folder** — this is your "workshop" folder **(your editied files will go in here)**.

### Step 2 — Find your file
Browse the **left panel** to find the `.mgraphobject` you want to redirect. Use the filters to narrow things down:
- 🔍 **Search bar** — filter by **filename** or **in-game** item name
- **Type dropdown** — filter by object type **(Gear, Weapon, Character, Prop, etc.)**
- **Package dropdown** — filter by content package **(base_game, dlc1, dlc2, dlc3, rogue, etc.)**

Each entry is colour-coded so you can tell at a glance what **type** and **package** it belongs to:

| Color | Type |
|--------|------|
| 🟣 Lavender | Gear |
| 🔴 Red-pink | Weapon |
| 🟢 Teal | Character |
| 🟠 Amber | Prop |
| 🔵 Cyan | Effect |
| 🟩 Green | Building |

| Color | Package |
|--------|---------|
| 🔵 Sky blue | base_game |
| 🟢 Green | dlc1 |
| 🟠 Orange | dlc2 |
| 🩷 Pink | dlc3 |
| 🟣 Purple | rogue |
| 🩵 Cyan | snowdrop |

### Step 3 — Name your output file
Type a new stem in the **NEW GRAPH FILE NAME** box. The tool will:
- Show a live character count and flag if the length doesn't match the original
- Automatically derive new texture filenames based on your new stem
- Let you check/uncheck individual textures to include or skip
- Allow **manual naming** per texture if the auto-derived name isn't right

> ⚠️ Texture and graph filenames must be the **same byte length** as the originals. The tool will warn you before writing anything if there's a mismatch.

**Gear swap only mode** — tick this checkbox if you only want to rename the `.mgraphobject` file itself without touching any textures **(useful when swapping one gear piece for another).**

### Step 4 — Copy to mod folder
Click **`⤓ COPY & RENAME TO MOD FOLDER`**. The tool will:
1. Read the source `.mgraphobject` binary
2. Patch all internal DDS path references to point to your new texture names
3. Write the renamed `.mgraphobject` to your mod folder
4. Copy and rename all found textures to their correct subfolder paths

The right panel shows everything currently in your mod folder so you can see what's been written.

---

## Features

- **Dual-panel browser** — resource folder on the left, mod folder on the right
- **Colour-coded lists** — type and package colours match the AFoP Gear Swap tool for a consistent look across your toolkit
- **Type + Package filters** — quickly narrow down thousands of files to exactly what you need
- **Auto texture discovery** — scans the resource folder and shows which textures are found or missing
- **Binary DDS parsing** — reads texture paths directly from unknown `.mgraphobject` files, no data file needed
- **Live rename preview** — see derived texture names and length validation before committing
- **Per-texture controls** — individually enable/disable or manually name each texture
- **Slot mismatch warning** — flags if the target graph file belongs to a different slot than the source, so you know before writing
- **Undo/Redo** — `Ctrl+Z` / `Ctrl+Y` in the name entry field
- **Preferences saved** — remembers your folder paths between sessions
