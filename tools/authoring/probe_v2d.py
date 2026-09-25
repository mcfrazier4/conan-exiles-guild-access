"""READ-ONLY: guild id accessors, map/array variable creation, runtime-widget nodes."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
wait_registry()
base = set(dir(unreal.Actor))
sec("Guild: full surface")
print("  ", sorted(d for d in dir(unreal.Guild) if not d.startswith("_") and d not in base))
for fn in ("get_stable_id", "get_guild_id", "guild_id", "get_owner", "is_officer", "get_guild_members"):
    f = getattr(unreal.Guild, fn, None); print(f"   --- {fn}: {(f.__doc__ or '').strip().replace(chr(10), ' ')[:220] if f else 'MISSING'}")
sec("ConanCharacter: guild accessors")
print("  ", [d for d in dir(unreal.ConanCharacter) if re.search(r"guild|clan|stable", d)])
sec("variable types: map / array / string")
print("   map<string,string>:", lib.get_map_type(lib.get_basic_type_by_name("string"), lib.get_basic_type_by_name("string")))
print("   map<string,bool>:", lib.get_map_type(lib.get_basic_type_by_name("string"), lib.get_basic_type_by_name("bool")))
print("   array<string>:", lib.get_array_type(lib.get_basic_type_by_name("string")))
sec("nodes for the runtime table + map ops (searched in BPC_GA_Player graph)")
pl = unreal.load_asset(f"{LOCAL}/BPC_GA_Player"); ped = GE.get_graph_editor_by_name(pl, "EventGraph")
for nm in ("ConstructObjectfromClass", "GetAllActorsOfClass", "AddChildtoUniformGrid", "AssignOnCheckStateChanged", "SetIsChecked", "SetText", "MapFind", "MapAdd", "Map|Find", "Map|Add", "Contains", "Format"):
    print(f"   {nm}:", available(ped, [], nm)[:5])
sec("done (read-only)")
