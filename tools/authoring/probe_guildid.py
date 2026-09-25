import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
print("   Guild.get_id doc:", (unreal.Guild.get_id.__doc__ or "").strip().replace("\n", " ")[:160])
print("   Guild.get_stable_id doc:", (unreal.Guild.get_stable_id.__doc__ or "").strip().replace("\n", " ")[:160])
print("   ConanCharacter.get_guild doc:", (unreal.ConanCharacter.get_guild.__doc__ or "").strip().replace("\n", " ")[:160])
print("   UniqueID struct:", hasattr(unreal, "UniqueID"), "| StableId struct:", hasattr(unreal, "StableId"))
libs = [c for c in dir(unreal) if re.search(r"Library|FunctionLib", c) and re.search(r"Conan|Dreamworld|Guild|Unique|Stable", c)]
print("   conan libs:", libs[:20])
for c in libs:
    cls = getattr(unreal, c)
    ms = [m for m in dir(cls) if re.search(r"unique_id|stable_id|to_string|conv_", m)]
    if ms: print(f"      {c}: {ms[:15]}")
