![GitHub release (latest by date)](https://img.shields.io/github/v/release/JasperZebra/AFoP_Texture_Redirector_Tool?style=for-the-badge&logo=github&color=00ffff&logoColor=white&labelColor=1a4d66)
![Total Downloads](https://img.shields.io/github/downloads/JasperZebra/AFoP_Texture_Redirector_Tool/total?style=for-the-badge&logo=github&color=00ffff&logoColor=white&labelColor=1a4d66)
![Platform](https://img.shields.io/badge/platform-windows-00ffff?style=for-the-badge&logo=windows&logoColor=00ffff&labelColor=1a4d66)
![Made for](https://img.shields.io/badge/made%20for-Avatar:_Frontiers_of_Pandora-00ffff?style=for-the-badge&logo=gamepad&logoColor=00ffff&labelColor=1a4d66)
![Tool Type](https://img.shields.io/badge/type-texture%20redirector-00ffff?style=for-the-badge&logo=package&logoColor=00ffff&labelColor=1a4d66)

# Texture Redirector
### Avatar: Frontiers of Pandora — Modding Tool

<img width="1402" height="895" alt="image" src="https://github.com/user-attachments/assets/5ddb7c5a-cfa1-41bc-917d-71691ef6d7d3" />

A GUI tool for redirecting `.mgraphobject` texture references, letting you copy and rename gear files from your game's resource folder into your mod output folder with all internal texture paths automatically patched.

## Features

- **Dual-panel browser** — resource folder on the left, mod output folder on the right
- **Searchable file lists** with slot filter (Head, Torso, Legs, etc.) and live result count
- **Auto texture discovery** — scans the resource folder and shows which textures are found or missing per file
- **Live rename preview** — type a new graph file stem and instantly see the derived texture names with length validation before you commit
- **Binary patching** — rewrites internal DDS path references inside the `.mgraphobject` file so the game picks up your renamed textures
- **Custom file support** — extracts DDS references directly from unknown binaries not present in the gear key
- **Preferences saved** — remembers your last resource and mod folder paths between sessions

## Usage
1. **Set Resource Folder** — point it at your game's unpacked resource directory.
2. **Set Mod Output Folder** — point it at the folder your mod packer reads from.
3. **Select a file** in the left panel — textures will be located automatically.
4. **Enter a new name** in the rename box — the tool previews the derived texture names and flags any length mismatches.
5. **Click `COPY & RENAME TO MOD FOLDER`** — the patched `.mgraphobject` and all found textures are written to the output folder.

> ⚠️ Texture and graph filenames must match the original byte length. The tool will warn you if they don't.

