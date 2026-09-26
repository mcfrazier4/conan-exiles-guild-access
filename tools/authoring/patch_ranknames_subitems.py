"""One-off: author_v2_ranknames.py leaf targets also feed the four radial AddSubItem labels from RankToText
(they were text literals 'Recruit' / 'Member' / 'Officer' / 'Guild Master', so the wheel ignored clan names)."""
import os, ast
here = os.path.dirname(os.path.abspath(__file__)); p = os.path.join(here, "author_v2_ranknames.py"); s = open(p).read()
a = '''    print(f"   server sites rewired: {done}")'''
b = '''    print(f"   server sites rewired: {done}")
    LABELS = {"Recruit": 0, "Member": 1, "Officer": 2, "Guild Master": 3}
    for n in nodes_titled(ed, "AddSubItem"):
        lp = lib.find_input_pin(n, "label")
        if lp is None or list(PL.list_connected_pins(lp)): continue
        lit = PL.get_pin_value(lp) or ""; rank = next((v for k, v in LABELS.items() if f'"{k}"' in lit), None)
        if rank is None: continue
        rt = call(ed, f"{BPL_C}:RankToText", f"RankToText({rank})"); setval(rt, "Rank", str(rank)); connect(out(rt, "Result"), lp, f"sub-item {rank} label <- clan name"); done += 1
    print(f"   radial sub-item labels wired: {sum(1 for n in nodes_titled(ed, 'AddSubItem') if list(PL.list_connected_pins(lib.find_input_pin(n, 'label'))))}")'''
assert a in s; s = s.replace(a, b); ast.parse(s); open(p, "w").write(s); print("author_v2_ranknames.py patched")
