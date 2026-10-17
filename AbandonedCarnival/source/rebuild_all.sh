#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python "$ROOT/source/make_textures.py"
blender -b -t 4 --python "$ROOT/source/build_carnival.py"
blender -b "$ROOT/blender/Moonfall_Carnival.blend" -t 2 --python "$ROOT/source/cleanup_scene.py"
blender -b "$ROOT/blender/Moonfall_Carnival.blend" -t 2 --python "$ROOT/source/polish_scene.py"
blender -b "$ROOT/blender/Moonfall_Carnival.blend" -t 2 --python "$ROOT/source/audit_geometry.py"
blender -b "$ROOT/blender/Moonfall_Carnival.blend" -t 6 --python "$ROOT/source/review_scene.py" -- --render Camera_Midway Camera_Arena Camera_Backstage Camera_Overview
