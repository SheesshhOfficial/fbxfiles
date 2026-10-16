"""Reassemble the exact verified Blender scene from the repository's binary parts."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / "SnipersAim_Parts_Manifest.json").read_text())
OUTPUT = ROOT / MANIFEST["filename"]

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

if OUTPUT.exists():
    if OUTPUT.stat().st_size == MANIFEST["size"] and digest(OUTPUT) == MANIFEST["sha256"]:
        print(f"Already verified: {OUTPUT}")
        raise SystemExit(0)
    raise SystemExit(f"Refusing to overwrite a different existing file: {OUTPUT}")

for part in MANIFEST["parts"]:
    p = ROOT / part["filename"]
    if not p.is_file():
        raise SystemExit(f"Missing part: {p.name}. Pull the repository again.")
    if p.stat().st_size != part["size"] or digest(p) != part["sha256"]:
        raise SystemExit(f"Part checksum mismatch: {p.name}")

temporary = OUTPUT.with_suffix(OUTPUT.suffix + ".reassembling")
if temporary.exists():
    raise SystemExit(f"Temporary file already exists; inspect or move it first: {temporary}")
with temporary.open("xb") as target:
    for part in MANIFEST["parts"]:
        with (ROOT / part["filename"]).open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                target.write(block)
if temporary.stat().st_size != MANIFEST["size"] or digest(temporary) != MANIFEST["sha256"]:
    raise SystemExit(f"Final checksum mismatch; output retained for inspection: {temporary}")
if OUTPUT.exists():
    raise SystemExit("Output appeared during reassembly; refusing to overwrite it.")
temporary.rename(OUTPUT)
print(f"Created and SHA256-verified: {OUTPUT}")
