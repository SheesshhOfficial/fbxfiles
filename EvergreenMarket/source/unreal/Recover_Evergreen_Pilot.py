import sys, importlib, json
from pathlib import Path
import unreal

package = r"C:\Art\Evergreen_Market_Unreal_Handoff"
source = Path(package) / "source"
for name in ("import_supermarket_unreal.py", "setup_market_collision.py", "setup_prop_actor_pilot.py"):
    if not (source / name).is_file():
        raise RuntimeError("Missing current helper: " + str(source / name))
sys.path.insert(0, str(source))
import import_supermarket_unreal as em
import setup_market_collision as ec
import setup_prop_actor_pilot as ep
for module in (em, ec, ep):
    if Path(module.__file__).resolve().parent != source.resolve():
        raise RuntimeError("A different helper folder is already loaded. Restart Unreal and retry: " + str(module.__file__))
    importlib.reload(module)

level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if level.is_in_play_in_editor():
    raise RuntimeError("Stop Play before continuing.")
current_level = level.get_current_level()
if current_level is None:
    raise RuntimeError("Open your successful original WalkTest map first.")
current_map = current_level.get_path_name().split(".")[0]
reports_root = Path(unreal.Paths.project_saved_dir()).resolve() / "EvergreenHandoff"
if not reports_root.is_dir():
    raise RuntimeError("No Evergreen reports found in this project: " + str(reports_root))

def read_reports(filename):
    found = []
    for path in sorted(reports_root.rglob(filename)):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as error:
            print("Skipping unreadable report:", str(path), str(error))
            continue
        if isinstance(data, dict):
            found.append((path, data))
    return found

matches = [(p, d) for p, d in read_reports("prop_pilot_report.json")
           if d.get("status") == "failed_partial_pilot_copy" and d.get("target_map") == current_map]
if len(matches) != 1:
    raise RuntimeError("Expected exactly one failed pilot report for the currently open map; found " + str(len(matches)))
failed_pilot_report = str(matches[0][0])
failed_data = matches[0][1]
walk_map = failed_data.get("source_map")
matches = [(p, d) for p, d in read_reports("collision_report.json")
           if d.get("status") == "verified_collision_persistence" and d.get("target_map") == walk_map]
if len(matches) != 1:
    raise RuntimeError("Expected exactly one successful collision report for the OPEN original WalkTest map; found " + str(len(matches)) + ". Current map: " + current_map)
collision_path, collision_data = matches[0]
matches = [(p, d) for p, d in read_reports("import_report.json")
           if d.get("schema") == em.SCHEMA and d.get("phase") == "full"
           and d.get("status") == "verified_persistence"
           and d.get("map_path") == collision_data.get("source_map")]
if len(matches) != 1:
    raise RuntimeError("Expected exactly one successful Full report matching this WalkTest's source; found " + str(len(matches)))
full_report = str(matches[0][0])
collision_report = str(collision_path)
print("Open map:", current_map)
print("Full report:", full_report)
print("Collision report:", collision_report)
print("Failed pilot report:", failed_pilot_report)
pilot_plan = ep.run(package, full_report, collision_report, failed_pilot_report=failed_pilot_report)
print("DRY RUN ONLY. Review four props and 568 collision boxes. No map was changed.")
