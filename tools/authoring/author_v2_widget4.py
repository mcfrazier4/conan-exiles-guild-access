"""v2 - Clan Ranks panel, fourth version: lives under the 'Ranks' tab of the clan window, styled like the roster.
Run WITH -ModDevKit. GA_MODE=dry|real. Rebuilds the EventGraph from scratch every run.

Construct:
  PermGrid's canvas slot is anchored to fill (left/right padding 20 like the roster content), min row height 44
  header  : per rank a W_FCEditableTextBlock (vanilla editable text; GM only) or a GeneralText FS_Text_Heading_5 tinted like the
            roster header; visibility picks one
  rows    : GeneralText label (FS_Text_Body_4, roster tint) + 4 WBP_ButtonCheckbox (toggled from the cache; enabled for GM except the GM column)
  every vanilla widget is registered with Host.SetupNewChild so the window's input routing reaches it
SaveNow (custom event, called by the clan window when it closes): if GM -> names -> Server_ServerSetRankName_0 x4; table -> Server_ServerSetTable_0
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
W_PATH = f"{LOCAL}/W_GA_ClanRanks"
BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"; PL_C = f"{LOCAL}/BPC_GA_Player.BPC_GA_Player_C"
CHK_C = "/Game/UI/Widgets/Buttons/WBP_ButtonCheckbox.WBP_ButtonCheckbox_C"; EDIT_C = "/Game/UI/Framework/W_FCEditableTextBlock.W_FCEditableTextBlock_C"
GT = "/Script/ConanSandbox.GeneralText"; ST_HEAD = "/Game/UI/Styling/Texts/FS_Text_Heading_5.FS_Text_Heading_5_C"; ST_BODY = "/Game/UI/Styling/Texts/FS_Text_Body_4.FS_Text_Body_4_C"
TINT = "(SpecifiedColor=(R=0.854993,G=0.775822,B=0.637597,A=0.700000),ColorUseRule=UseColor_Specified)"
SHOWN_PERMS = [0, 5]
M = "/Script/Engine.KismetMathLibrary:"; T = "/Script/Engine.KismetTextLibrary:"
FORLOOP = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForLoop"
byte_t, bool_t, int_t = [lib.get_basic_type_by_name(x) for x in ("byte", "bool", "int")]
sec(f"mode = {MODE}")
wait_registry()
w = unreal.load_asset(W_PATH); check(w is not None, "loaded W_GA_ClanRanks"); ed = GE.get_graph_editor_by_name(w, "EventGraph")
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def pin(n, name): return pin_exact_in(n, name)
def selfpin(n): return lib.find_self_pin(n) or pin_exact_in(n, "self")
def first_param(n):
    """first input pin that is neither exec nor self (for C++ params whose names vary)"""
    return next((p for p in lib.list_input_pins(n) if str(PL.get_pin_name(p)) not in ("self", "execute")), None)
def create_widget(cls_path, owner_pin, label):
    n = create_by_search(ed, [], ("CreateWidget",), f"CreateWidget {label}", exact="UserInterface|CreateWidget")
    check(PL.set_pin_value(pin(n, "Class"), cls_path), f"{label}: class"); connect(owner_pin, pin(n, "OwningPlayer"), f"{label}: owner"); return n
def construct(cls_path, label):
    n = create_by_search(ed, [], ("ConstructObjectfromClass",), f"Construct {label}", exact="Game|ConstructObjectfromClass")
    check(PL.set_pin_value(pin(n, "Class"), cls_path), f"{label}: class"); return n
def styled_text(style_cls, label, tail):
    """ConstructObject(GeneralText) -> SetTextStyle(style via LoadClass + class cast) -> tint. Returns (text pin, tail)."""
    n = construct(GT, label); connect(tail, exec_in(n), f"-> {label}"); tail = then_out(n); tp = out(n, "ReturnValue")
    ld = call(ed, "/Script/Engine.KismetSystemLibrary:LoadClassAsset_Blocking", f"LoadClass({label})"); lp = next((p for p in lib.list_input_pins(ld) if "Class" in str(PL.get_pin_name(p))), None)
    check(lp is not None and PL.set_pin_value(lp, style_cls), f"{label}: style class literal"); connect(tail, exec_in(ld), "-> LoadClass"); tail = then_out(ld)
    cast = create_by_search(ed, [out(ld, "ReturnValue")], ("Casting", "CastToTextStyleDataAssetClass"), f"class cast ({label})", exact="Utilities|Casting|CastToTextStyleDataAssetClass")
    connect(out(ld, "ReturnValue"), first_param(cast), "class -> cast"); connect(tail, exec_in(cast), "-> cast"); tail = then_out(cast)
    ss = call(ed, "/Script/ConanSandbox.GeneralText:SetTextStyle", f"SetTextStyle({label})"); connect(tp, selfpin(ss), "text"); connect(as_pin(cast), first_param(ss), "cast -> style"); connect(tail, exec_in(ss), "-> SetTextStyle"); tail = then_out(ss)
    co = call(ed, "/Script/UMG.TextBlock:SetColorAndOpacity", f"tint({label})"); connect(tp, selfpin(co), "text"); check(PL.set_pin_value(first_param(co), TINT), f"{label}: tint literal"); connect(tail, exec_in(co), "-> tint"); tail = then_out(co)
    return tp, tail
def setup_child(widget_pin, tail, label):
    h = ed.add_get_member_variable_node("Host"); s = call(ed, "/Script/ConanSandbox.RootWidget:SetupNewChild", f"SetupNewChild({label})")
    connect(out(h), selfpin(s), "Host"); connect(widget_pin, pin(s, "child"), "child"); connect(tail, exec_in(s), "-> SetupNewChild"); return then_out(s)
def set_vis(widget_pin, vis, tail, label):
    v = call(ed, "/Script/UMG.Widget:SetVisibility", f"SetVisibility({label})"); connect(widget_pin, selfpin(v), label); setval(v, "InVisibility", vis); connect(tail, exec_in(v), f"-> {label} {vis}"); return then_out(v)
def center(text_pin, tail, label):
    jc = ed.add_set_member_variable_node("Justification", "/Script/UMG.TextBlock"); check(jc is not None, f"Set Justification {label}"); connect(text_pin, selfpin(jc), label); PL.set_pin_value(pin_exact_in(jc, "Justification"), "Center"); connect(tail, exec_in(jc), "-> center"); return then_out(jc)
def add_to_grid(widget_pin, row, col, tail, halign="Center"):
    a = call(ed, "/Script/UMG.UniformGridPanel:AddChildToUniformGrid", "AddChildToUniformGrid")
    connect(out(grid), selfpin(a), "PermGrid -> Add"); connect(widget_pin, pin(a, "Content"), "widget -> Add"); setval(a, "InRow", str(row)); setval(a, "InColumn", str(col))
    connect(tail, exec_in(a), "-> AddChildToUniformGrid"); tail = then_out(a)
    ha = call(ed, "/Script/UMG.UniformGridSlot:SetHorizontalAlignment", "slot HAlign"); connect(out(a, "ReturnValue"), selfpin(ha), "slot"); setval(ha, "InHorizontalAlignment", halign); connect(tail, exec_in(ha), "-> HAlign"); tail = then_out(ha)
    va = call(ed, "/Script/UMG.UniformGridSlot:SetVerticalAlignment", "slot VAlign"); connect(out(a, "ReturnValue"), selfpin(va), "slot"); setval(va, "InVerticalAlignment", "Center"); connect(tail, exec_in(va), "-> VAlign"); return then_out(va)
def array_get(arr_pin, idx):
    g = create_by_search(ed, [arr_pin], ("Array", "Get"), "Array Get", prefer=["|Get(acopy)"])
    connect(arr_pin, pin_exact_in(g, "Array") or pin_exact_in(g, "TargetArray"), "array -> Get")
    ip = pin_exact_in(g, "Dimension 1") or pin_exact_in(g, "Index")
    if isinstance(idx, int): PL.set_pin_value(ip, str(idx))
    else: connect(idx, ip, "index -> Get")
    return out(g)
def array_add(arr_pin, item_pin=None, literal=None):
    a = create_by_search(ed, [arr_pin], ("Array", "Add"), "Array Add", exact="Utilities|Array|Add")
    connect(arr_pin, pin_exact_in(a, "TargetArray"), "array -> Add")
    if item_pin is not None: connect(item_pin, pin_exact_in(a, "NewItem"), "item -> Add")
    else: PL.set_pin_value(pin_exact_in(a, "NewItem"), literal)
    return a

# ---- rebuild: drop everything except the event nodes
keep = {n.get_name() for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_Event"}
ed.remove_nodes([n for n in ed.list_all_nodes() if n.get_name() not in keep]); print("   graph cleared (events kept)")
for nm in ("Cells", "CellIdx", "Boxes", "Comp", "Host"):
    if nm in [str(v) for v in lib.list_member_variable_names(w)]: print(f"   removing old var {nm} ->", ed.remove_member_variable(nm))
lib.compile_blueprint(w)
for nm, t in (("Cells", lib.get_array_type(lib.get_object_reference_type(unreal.FLXButtonBase))), ("CellIdx", lib.get_array_type(int_t)), ("Boxes", lib.get_array_type(lib.get_object_reference_type(unreal.FCEditableTextBase))), ("Comp", lib.get_object_reference_type(unreal.load_class(None, PL_C))), ("Host", lib.get_object_reference_type(unreal.GuildViewBase))):
    check(lib.add_member_variable(w, nm, t), f"var {nm}")
lib.compile_blueprint(w)
grid = ed.add_get_member_variable_node("PermGrid"); check(grid is not None, "Get PermGrid")
title_n = ed.add_get_member_variable_node("TitleText"); close_n = ed.add_get_member_variable_node("CloseButton")
ev = [n for n in ed.list_all_nodes() if title(n) == "Event Construct"][0]; tail = then_out(ev)
gop = create_by_search(ed, [], ("GetOwningPlayer",), "GetOwningPlayer", prefer=["|GetOwningPlayer"]); pc = out(gop, "ReturnValue")
gcb = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(Player)"); connect(pc, pin(gcb, "self"), "PC -> gcb"); setval(gcb, "ComponentClass", PL_C)
sc = ed.add_set_member_variable_node("Comp"); connect(out(gcb, "ReturnValue"), pin(sc, "Comp"), "-> Comp"); connect(tail, exec_in(sc), "-> Set Comp"); tail = then_out(sc)
comp = ed.add_get_member_variable_node("Comp")
names = ed.add_get_member_variable_node("CachedNames", PL_C); connect(out(comp), selfpin(names), "comp -> CachedNames")
allowed = ed.add_get_member_variable_node("CachedAllowed", PL_C); connect(out(comp), selfpin(allowed), "comp -> CachedAllowed")
myrank = ed.add_get_member_variable_node("CachedMyRank", PL_C); connect(out(comp), selfpin(myrank), "comp -> CachedMyRank")
is_gm = call(ed, M + "EqualEqual_ByteByte", "MyRank==3"); connect(out(myrank), pin(is_gm, "A"), "rank"); setval(is_gm, "B", "3")
tail = set_vis(out(title_n), "Collapsed", tail, "TitleText"); tail = set_vis(out(close_n), "Collapsed", tail, "CloseButton")
# ---- layout: anchor PermGrid to fill its canvas; rows at least 44 px like roster entries
cs = call(ed, "/Script/UMG.WidgetLayoutLibrary:SlotAsCanvasSlot", "SlotAsCanvasSlot(PermGrid)"); connect(out(grid), first_param(cs), "PermGrid")
an = call(ed, "/Script/UMG.CanvasPanelSlot:SetAnchors", "SetAnchors(fill)"); connect(out(cs, "ReturnValue"), selfpin(an), "slot"); check(PL.set_pin_value(first_param(an), "(Minimum=(X=0.000000,Y=0.000000),Maximum=(X=1.000000,Y=1.000000))"), "anchors literal"); connect(tail, exec_in(an), "-> anchors"); tail = then_out(an)
of = call(ed, "/Script/UMG.CanvasPanelSlot:SetOffsets", "SetOffsets(20,0,20,0)"); connect(out(cs, "ReturnValue"), selfpin(of), "slot"); check(PL.set_pin_value(first_param(of), "(Left=20.000000,Top=0.000000,Right=20.000000,Bottom=0.000000)"), "offsets literal"); connect(tail, exec_in(of), "-> offsets"); tail = then_out(of)
mh = call(ed, "/Script/UMG.UniformGridPanel:SetMinDesiredSlotHeight", "SetMinDesiredSlotHeight(44)"); connect(out(grid), selfpin(mh), "PermGrid"); PL.set_pin_value(first_param(mh), "44.0"); connect(tail, exec_in(mh), "-> min height"); tail = then_out(mh)
boxes = ed.add_get_member_variable_node("Boxes"); cells = ed.add_get_member_variable_node("Cells"); cellidx = ed.add_get_member_variable_node("CellIdx")
# ---- header row: rank names
for r in range(4):
    s2t = call(ed, T + "Conv_StringToText", f"StringToText {r}"); connect(array_get(out(names), r), pin(s2t, "InString"), f"name[{r}]")
    box = create_widget(EDIT_C, pc, f"name box {r}"); connect(tail, exec_in(box), "-> box"); tail = then_out(box); bp_ = out(box, "ReturnValue")
    stx = call(ed, "/Script/ConanSandbox.FCEditableTextBase:SetText", f"SetText(box {r})"); connect(bp_, selfpin(stx), "box"); connect(out(s2t, "ReturnValue"), first_param(stx), "text"); connect(tail, exec_in(stx), "-> SetText"); tail = then_out(stx)
    tail = add_to_grid(bp_, 0, r + 1, tail, halign="Fill"); tail = setup_child(bp_, tail, f"box {r}")
    a = array_add(out(boxes), bp_); connect(tail, exec_in(a), "-> Boxes.Add"); tail = then_out(a)
    hp, tail = styled_text(ST_HEAD, f"heading {r}", tail)
    sth = call(ed, "/Script/UMG.TextBlock:SetText", f"SetText(heading {r})"); connect(hp, selfpin(sth), "heading"); connect(out(s2t, "ReturnValue"), pin(sth, "InText"), "text"); connect(tail, exec_in(sth), "-> SetText"); tail = then_out(sth)
    tail = center(hp, tail, f"heading {r}"); tail = add_to_grid(hp, 0, r + 1, tail)
    br = ed.add_branch_node(); connect(out(is_gm, "ReturnValue"), lib.find_condition_pin(br), "GM?"); connect(tail, exec_in(br), "-> Branch GM")
    t1 = set_vis(bp_, "Visible", then_out(br), f"box {r}"); t1 = set_vis(hp, "Collapsed", t1, f"heading {r}")
    t2 = set_vis(bp_, "Collapsed", lib.find_else_pin(br), f"box {r}"); t2 = set_vis(hp, "Visible", t2, f"heading {r}")
    jn = call(ed, "/Script/UMG.Widget:SetIsEnabled", f"join {r}"); connect(bp_, selfpin(jn), "box"); setval(jn, "bInIsEnabled", "true")
    connect(t1, exec_in(jn), "GM -> join"); connect(t2, exec_in(jn), "other -> join"); tail = then_out(jn)
# ---- permission rows
for row, perm in enumerate(SHOWN_PERMS, start=1):
    lp_, tail = styled_text(ST_BODY, f"label {perm}", tail)
    ptt = call(ed, f"{BPL_C}:PermToText", "PermToText"); setval(ptt, "Perm", str(perm))
    stl = call(ed, "/Script/UMG.TextBlock:SetText", f"SetText(label {perm})"); connect(lp_, selfpin(stl), "label"); connect(out(ptt, "Result"), pin(stl, "InText"), "text"); connect(tail, exec_in(stl), "-> SetText"); tail = then_out(stl)
    tail = add_to_grid(lp_, row, 0, tail, halign="Left")
    for rank in range(4):
        cw = create_widget(CHK_C, pc, f"cell {perm}/{rank}"); connect(tail, exec_in(cw), "-> CreateWidget"); tail = then_out(cw); cp = out(cw, "ReturnValue")
        tog = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetIsToggledOn", "SetIsToggledOn"); connect(cp, selfpin(tog), "cell"); connect(array_get(out(allowed), perm * 4 + rank), pin(tog, "NewIsToggledOn"), "allowed[i]"); setval(tog, "ShouldSendEvent", "false"); setval(tog, "IsInstantTransition", "true")
        connect(tail, exec_in(tog), "-> SetIsToggledOn"); tail = then_out(tog)
        en = call(ed, "/Script/UMG.Widget:SetIsEnabled", "enable cell"); connect(cp, selfpin(en), "cell")
        if rank == 3: setval(en, "bInIsEnabled", "false")
        else: connect(out(is_gm, "ReturnValue"), pin(en, "bInIsEnabled"), "GM?")
        connect(tail, exec_in(en), "-> enable"); tail = then_out(en)
        tail = add_to_grid(cp, row, rank + 1, tail); tail = setup_child(cp, tail, f"cell {perm}/{rank}")
        a1 = array_add(out(cells), cp); connect(tail, exec_in(a1), "-> Cells.Add"); tail = then_out(a1)
        a2 = array_add(out(cellidx), literal=str(perm * 4 + rank)); connect(tail, exec_in(a2), "-> CellIdx.Add"); tail = then_out(a2)
# ---- SaveNow: GM only; names, then the table
sn = ed.add_custom_event_node("SaveNow"); check(sn is not None, "custom event SaveNow")
comp2 = ed.add_get_member_variable_node("Comp"); myrank2 = ed.add_get_member_variable_node("CachedMyRank", PL_C); connect(out(comp2), selfpin(myrank2), "comp")
gm2 = call(ed, M + "EqualEqual_ByteByte", "MyRank==3 (save)"); connect(out(myrank2), pin(gm2, "A"), "rank"); setval(gm2, "B", "3")
brs = ed.add_branch_node(); connect(out(gm2, "ReturnValue"), lib.find_condition_pin(brs), "GM?"); connect(then_out(sn), exec_in(brs), "SaveNow -> GM?"); t = then_out(brs)
boxes2 = ed.add_get_member_variable_node("Boxes")
for r in range(4):
    gt = call(ed, "/Script/ConanSandbox.FCEditableTextBase:GetText", f"GetText(box {r})"); connect(array_get(out(boxes2), r), selfpin(gt), "box")
    t2s = call(ed, T + "Conv_TextToString", "TextToString"); connect(out(gt, "ReturnValue"), pin(t2s, "InText"), "text")
    rpc = call(ed, f"{PL_C}:Server_ServerSetRankName_0", f"ServerSetRankName {r}"); connect(out(comp2), selfpin(rpc), "comp"); setval(rpc, "Rank", str(r)); connect(out(t2s, "ReturnValue"), pin(rpc, "Name"), "name")
    connect(t, exec_in(rpc), f"-> set name {r}"); t = then_out(rpc)
lp = ed.add_macro_node(FORLOOP); check(lp is not None, "ForLoop"); n_cells = len(SHOWN_PERMS) * 4
PL.set_pin_value(pin_exact_in(lp, "FirstIndex"), "0"); PL.set_pin_value(pin_exact_in(lp, "LastIndex"), str(n_cells - 1)); connect(t, pin_exact_in(lp, "execute"), "-> ForLoop"); idx = pin_exact_out(lp, "Index")
allowed2 = ed.add_get_member_variable_node("CachedAllowed", PL_C); connect(out(comp2), selfpin(allowed2), "comp")
cells2 = ed.add_get_member_variable_node("Cells"); cellidx2 = ed.add_get_member_variable_node("CellIdx")
isc = call(ed, "/Script/ConanSandbox.FLXButtonBase:GetIsToggledOn", "GetIsToggledOn"); connect(array_get(out(cells2), idx), selfpin(isc), "cell[i]")
setel = create_by_search(ed, [out(allowed2)], ("Array", "SetArrayElem"), "Array Set", exact="Utilities|Array|SetArrayElem")
connect(out(allowed2), pin_exact_in(setel, "TargetArray"), "CachedAllowed -> Set"); connect(array_get(out(cellidx2), idx), pin_exact_in(setel, "Index"), "idx"); connect(out(isc, "ReturnValue"), pin_exact_in(setel, "Item"), "toggled")
connect(pin_exact_out(lp, "LoopBody"), exec_in(setel), "body -> Set")
rpc = call(ed, f"{PL_C}:Server_ServerSetTable_0", "ServerSetTable"); connect(out(comp2), selfpin(rpc), "comp"); allowed3 = ed.add_get_member_variable_node("CachedAllowed", PL_C); connect(out(comp2), selfpin(allowed3), "comp"); connect(out(allowed3), pin(rpc, "Allowed"), "table")
connect(pin_exact_out(lp, "Completed"), exec_in(rpc), "Completed -> ServerSetTable")
sec("compile")
compile_ok(w, [(ed, "EventGraph")], "W_GA_ClanRanks")
if MODE == "real" and not failures: save(w, os.path.join(DISK_LOCAL, "W_GA_ClanRanks.uasset"), "W_GA_ClanRanks")
elif MODE == "real": print("   NOT SAVING: failures above")
result()
