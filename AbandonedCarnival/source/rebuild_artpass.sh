#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# Start from the checkpoint produced by rebuild_all.sh. Verified local CC0
# textures are dependencies; this reproducible art pass makes no network calls.
python "$ROOT/source/derive_weathered_surfaces.py"
python "$ROOT/source/make_ground_damage.py"
python "$ROOT/source/derive_canvas_surfaces.py"
blender -b "$ROOT/blender/Moonfall_Carnival.blend" -t 2 --python "$ROOT/source/midway_artpass.py"
for STEP in detail_midway_signage integrate_natural_vegetation integrate_natural_forest apply_scanned_surfaces assemble_artpass_props refine_ground_atmosphere refine_pavement_cracks refine_hero_props refine_leaf_materials refine_render_transport fix_bottle_uv_seam refine_continuous_asphalt refine_carousel_materials refine_themed_midway_props apply_backstage_refinement apply_arena_refinement refine_backstage_lighting refine_funhouse_roof apply_ticket_refinement refine_map_grasses finalize_review_source refine_entrance_verges optimize_vegetation_vertices restore_prop_smooth_normals refine_arena_safety_signs clean_evaluated_decorations; do
  blender -b "$ROOT/blender/Moonfall_Carnival_ArtPass.blend" -t 2 --python "$ROOT/source/$STEP.py"
done
blender -b "$ROOT/blender/Moonfall_Carnival_ArtPass.blend" -t 8 --python "$ROOT/source/render_final_midway.py"
