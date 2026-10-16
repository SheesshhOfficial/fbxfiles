# Reproduce the pantry vertical slice

Store display name: **You want it You get it**. Technical Evergreen file prefixes are retained.

## Prerequisites

- Blender 4.3.2 was used for the authored scene and renders.
- Python 3 and Pillow are needed only to regenerate the label PNGs. The ten finished PNGs are already included and packed into the master Blender file.
- The label generator uses local URW P052 and Open Sans fonts, with DejaVu fallbacks. Its font paths are listed near the top of `textures/generate_labels.py`; adjust those paths if regenerating on another operating system.

## Exact authoring order

All paths below are relative to this version folder. Use your Blender executable path in place of `/usr/bin/blender`.

1. Optional label regeneration: `python textures/generate_labels.py`. It writes ten 600 × 850 product-label PNGs, individual JSON specs, `label_specs.json` and a contact sheet beside the generator in `textures/`.
2. `/usr/bin/blender -b -t 8 --python build_premium_slice.py`
3. `/usr/bin/blender -b -t 8 --python finalize_scene.py`
4. `/usr/bin/blender -b -t 8 --python complete_source_contract.py`
5. `/usr/bin/blender -b -t 8 --python refine_product_composition.py`
6. `/usr/bin/blender -b -t 8 --python pack_relative_assets.py`
7. `/usr/bin/blender -b -t 8 --python render_slice.py`

`python rebuild_slice.py --blender /path/to/blender --render` runs steps 2–7 in order. Without `--render`, it stops at the packed, source-complete Blender file. Run the sequence from the start when rebuilding: refinement scripts are ordered authoring stages and are not intended to be repeatedly applied to an arbitrary edited file.

The first builder saves a low-sample preview. Final rendering produces the product-detail and aisle approval pair at 1500 × 1100, up to 512 Cycles samples, adaptive threshold 0.015, eight CPU threads and no denoiser. The third, shelf-detail camera is available by adding `-- all` after the render script in a Blender command. `PREVIEW_*.png` files are not the final delivery renders.

## Portability verification

`pack_relative_assets.py` packs all ten textures and converts file references to `//textures/<sku>.png`.

For an isolated reopen check, copy only the master `.blend` into a temporary directory with no `textures/` subfolder, then run Blender on that copy with `--python check_isolated_reopen.py`. The read-only check forces each image's pixel buffer to load and verifies that all ten images are available from packed data despite missing external texture files. Results are written to `PACKED_REOPEN_VALIDATION.json` beside the validation script.

## Outputs and scope

- `EVERGREEN_PANTRY_VERTICAL_SLICE_v1.blend`
- `SLICE_01_AISLE_CYCLES.png`
- `SLICE_02_PRODUCT_DETAIL_CYCLES.png`
- `EXPORT_MANIFEST.json`
- `ASSET_COLLISION_QA.json`
- Texture packing/reopen reports and the separately supplied independent source audit

This sequence writes only inside this version folder. It does not export FBX, import into Unreal, change any Blueprint, or modify the previous full-store/layout project. Blender procedural materials still require an explicit Unreal bake/rebuild; Cycles light watts are not directly interchangeable with Unreal photometric units.
