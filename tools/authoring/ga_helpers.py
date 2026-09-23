"""Shared helpers for the GuildAccess headless authoring scripts."""
import os, sys, time, unreal

lib, GE, PL = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary
MODE = os.environ.get("GA_MODE", "dry").lower()
LOCAL = "/Game/Mods/GuildAccess/Local"
DISK_LOCAL = r"E:\ClaudeCode\conan-exiles\guild-access\GuildAccess\Local"
DISK_CONTENT = r"E:\ClaudeCode\conan-exiles\guild-access\GuildAccess\Content"
failures = []

def sec(t): print("\n======== " + t + " ========")
def check(ok, msg):
    print(("   OK   " if ok else "   FAIL ") + msg)
    if not ok: failures.append(msg)
    return ok
def title(n):
    try: return lib.get_node_title(n)
    except Exception: return n.get_class().get_name()
def pins(n): return [f"{'in' if 'INPUT' in str(PL.get_pin_direction(p)) else 'out'} {PL.get_pin_name(p)}" for p in lib.list_all_pins(n)]
def connect(a, b, label):
    ok = bool(a is not None and b is not None and PL.try_create_connection(a, b))
    return check(ok, f"connect {label}")
def setval(node, pin, val, label=None):
    p = lib.find_input_pin(node, pin) if node is not None else None
    ok = bool(p is not None and PL.set_pin_value(p, val))
    return check(ok, label or f"{title(node) if node else '?'}.{pin} = {val[:50]!r}")
def call(ed, path, label=None):
    n = None
    try: n = ed.add_call_function_node(path)
    except Exception as e: print(f"      {path!r} raised {type(e).__name__}: {str(e)[:100]}")
    check(n is not None, f"node {label or path.split(':')[-1]}")
    return n
def call_first(ed, paths, label):
    for p in paths:
        try: n = ed.add_call_function_node(p)
        except Exception: n = None
        if n is not None:
            check(True, f"node {label} via {p!r}"); return n
    check(False, f"node {label}: none of {paths}"); return None
def nodes_titled(ed, t): return [n for n in ed.list_all_nodes() if title(n) == t]
def available(ed, ctx, *subs):
    names = [str(a) for a in ed.list_available_nodes(list(ctx))]
    return [n for n in names if all(s.lower() in n.lower() for s in subs)]
def create_by_search(ed, ctx, subs, label, prefer=None, exact=None):
    hits = available(ed, ctx, *subs)
    print(f"      candidates for {label}: {hits[:8]}")
    if not hits:
        check(False, f"{label}: no available node matches {subs}"); return None
    name = None
    if exact and exact in hits: name = exact
    if name is None and prefer:
        for p in prefer:
            for h in hits:
                if h.lower().endswith(p.lower()): name = h; break
            if name: break
    name = name or sorted(hits, key=len)[0]
    n = ed.create_node_from_name(name, unreal.Vector2D(0, 0), list(ctx))
    check(n is not None, f"{label}: created from {name!r}")
    if n is not None: print(f"      -> [{n.get_class().get_name()}] {title(n)!r} {pins(n)}")
    return n
def new_nodes(ed, before): return [n for n in ed.list_all_nodes() if n.get_name() not in before]
def snapshot(ed): return {n.get_name() for n in ed.list_all_nodes()}
def as_pin(cast_node):
    outs = [p for p in lib.list_output_pins(cast_node) if str(PL.get_pin_name(p)).startswith("As")]
    return outs[0] if outs else None
def exec_in(n): return lib.find_execute_pin(n)
def then_out(n): return lib.find_then_pin(n)
def dump(ed, name):
    print(f"   --- dump {name} ---")
    for n in ed.list_all_nodes():
        print(f"   NODE [{n.get_class().get_name()}] {title(n)!r}")
        for p in lib.list_all_pins(n):
            d = "in " if "INPUT" in str(PL.get_pin_direction(p)) else "out"
            conns = [f"{title(PL.get_owning_node(c))}.{PL.get_pin_name(c)}" for c in PL.list_connected_pins(p)]
            v = PL.get_pin_value(p)
            if v or conns: print(f"      {d} {str(PL.get_pin_name(p)):24} val={v!r:40} -> {conns}")
def text_lit(key, value): return f'NSLOCTEXT("GuildAccess", "{key}", "{value}")'
_ar_waited = False
def wait_registry():
    global _ar_waited
    if _ar_waited: return
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    t0 = time.time(); ar.wait_for_completion(); _ar_waited = True
    print(f"   (asset registry scan complete after {time.time()-t0:.1f}s; Local assets: {[str(a.asset_name) for a in ar.get_assets_by_path(LOCAL, recursive=True)]})")
def load_or_create(path, parent):
    wait_registry()
    bp = unreal.load_asset(path)
    if bp: print(f"   {path}: exists, reusing"); return bp, False
    bp = lib.create_blueprint_asset_with_parent(path, parent)
    if bp is None:
        print("   BlueprintEditorLibrary creation refused; falling back to AssetTools + BlueprintFactory")
        try:
            factory = unreal.BlueprintFactory()
            factory.set_editor_property("parent_class", parent)
            pkg_path, name = path.rsplit("/", 1)
            bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, pkg_path, unreal.Blueprint, factory)
        except Exception as e:
            print("   AssetTools fallback raised", type(e).__name__, str(e)[:120]); bp = None
    check(bp is not None, f"created {path} (parent {parent.static_class().get_name()})")
    return bp, True
def compile_ok(bp, ed_list, label):
    ok = lib.compile_blueprint(bp)
    check(ok, f"compile {label}")
    for ed, gname in ed_list:
        errs = list(ed.list_nodes_with_errors())
        check(len(errs) == 0, f"{label}::{gname}: no error nodes")
        for n in errs:
            try: print("      error node:", title(n), n.error_msg)
            except Exception: print("      error node:", title(n))
def save(bp, disk_file, label):
    st0 = os.stat(disk_file) if os.path.exists(disk_file) else None
    r = unreal.EditorLoadingAndSavingUtils.save_packages([bp.get_outermost()], False)
    print(f"   save_packages({label}) -> {r}")
    ok = os.path.exists(disk_file) and (st0 is None or os.stat(disk_file).st_mtime > st0.st_mtime)
    when = time.strftime('%H:%M:%S', time.localtime(os.stat(disk_file).st_mtime)) if os.path.exists(disk_file) else 'missing'
    check(ok, f"{label} written to disk ({when}, {os.path.getsize(disk_file) if os.path.exists(disk_file) else 0} B)")
def result(dry_note=True):
    sec("RESULT: " + ("ALL OK" if not failures else f"{len(failures)} FAILURE(S)") + (" (dry run, nothing saved)" if MODE == "dry" and dry_note else ""))
    for f in failures: print("   -", f)
    sys.exit(0 if not failures else 1)
