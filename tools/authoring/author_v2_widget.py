"""v2 stage 4a - the Clan Ranks panel logic (W_GA_ClanRanks). Run WITH -ModDevKit. GA_MODE=dry|real. Idempotent.

Skeleton made in the GUI: Canvas root, TitleText (TextBlock), PermGrid (UniformGridPanel), CloseButton (Button).
Event Construct builds the table at runtime from BPC_GA_Player's cache:
  header row : 4 EditableTextBox (rank names; editable only for the guild master) -> OnTextCommitted -> Server_ServerSetRankName_0
  rows       : for each shown permission, a label + 4 CheckBox (enabled for GM, never for the GM column)
  any change : rebuild CachedAllowed from the cells -> Server_ServerSetTable_0
  CloseButton: RemoveFromParent + game input mode
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *

W_PATH = f"{LOCAL}/W_GA_ClanRanks"
BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"; PL_C = f"{LOCAL}/BPC_GA_Player.BPC_GA_Player_C"
SHOWN_PERMS = [0, 5]            # Dismantle, Set access rank - the ones that are enforced
M = "/Script/Engine.KismetMathLibrary:"; T = "/Script/Engine.KismetTextLibrary:"
FORLOOP = "/Engine/EditorBlueprintResources/StandardMacros.StandardMacros:ForLoop"
byte_t, bool_t, int_t = [lib.get_basic_type_by_name(x) for x in ("byte", "bool", "int")]

sec(f"mode = {MODE}")
wait_registry()
w = unreal.load_asset(W_PATH); check(w is not None, "loaded W_GA_ClanRanks")
ed = GE.get_graph_editor_by_name(w, "EventGraph"); check(ed is not None, "EventGraph")
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def pin(n, name): return pin_exact_in(n, name)
def selfpin(n): return lib.find_self_pin(n) or pin_exact_in(n, "self")
def construct(cls_path, label):
    n = create_by_search(ed, [], ("ConstructObjectfromClass",), f"Construct {label}", exact="Game|ConstructObjectfromClass")
    check(PL.set_pin_value(pin(n, "Class"), cls_path), f"{label}: class"); return n
def to_text_from_string(str_pin):
    n = call(ed, T + "Conv_StringToText", "StringToText"); connect(str_pin, pin(n, "InString"), "str -> text"); return out(n, "ReturnValue")
def add_to_grid(widget_pin, row, col, tail):
    a = call(ed, "/Script/UMG.UniformGridPanel:AddChildToUniformGrid", "AddChildToUniformGrid")
    connect(out(grid), selfpin(a), "PermGrid -> Add"); connect(widget_pin, pin(a, "Content"), "widget -> Add"); setval(a, "InRow", str(row)); setval(a, "InColumn", str(col))
    connect(tail, exec_in(a), "-> AddChildToUniformGrid"); return then_out(a)
def array_get(arr_pin, idx):
    g = create_by_search(ed, [arr_pin], ("Array", "Get"), "Array Get", prefer=["|Get(acopy)"])
    connect(arr_pin, pin_exact_in(g, "Array") or pin_exact_in(g, "TargetArray"), "array -> Get")
    ip = pin_exact_in(g, "Dimension 1") or pin_exact_in(g, "Index")
    if isinstance(idx, int): PL.set_pin_value(ip, str(idx))
    else: connect(idx, ip, "index -> Get")
    return out(g)
def array_add(arr_pin, item_pin):
    a = create_by_search(ed, [arr_pin], ("Array", "Add"), "Array Add", exact="Utilities|Array|Add")
    connect(arr_pin, pin_exact_in(a, "TargetArray"), "array -> Add"); connect(item_pin, pin_exact_in(a, "NewItem"), "item -> Add"); return a

if nodes_titled(ed, "AddChildToUniformGrid"):
    print("   panel logic exists; leaving as is")
else:
    for nm, t in (("Cells", lib.get_array_type(lib.get_object_reference_type(unreal.CheckBox))), ("CellIdx", lib.get_array_type(int_t)), ("Comp", lib.get_object_reference_type(unreal.load_class(None, PL_C)))):
        if nm not in [str(v) for v in lib.list_member_variable_names(w)]: check(lib.add_member_variable(w, nm, t), f"var {nm}")
    lib.compile_blueprint(w)
    grid = ed.add_get_member_variable_node("PermGrid"); check(grid is not None, "Get PermGrid (widget variable)")
    title_n = ed.add_get_member_variable_node("TitleText"); close_n = ed.add_get_member_variable_node("CloseButton")
    check(title_n is not None and close_n is not None, "Get TitleText / CloseButton")
    ev = [n for n in ed.list_all_nodes() if title(n) == "Event Construct"]; check(len(ev) == 1, "Event Construct"); ev = ev[0]
    tail = then_out(ev)
    # component
    gop = create_by_search(ed, [], ("GetOwningPlayer",), "GetOwningPlayer", prefer=["|GetOwningPlayer"])
    gcb = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(Player)"); connect(out(gop, "ReturnValue"), pin(gcb, "self"), "PC -> gcb"); setval(gcb, "ComponentClass", PL_C)
    sc = ed.add_set_member_variable_node("Comp"); connect(out(gcb, "ReturnValue"), pin(sc, "Comp"), "component -> Comp"); connect(tail, exec_in(sc), "-> Set Comp"); tail = then_out(sc)
    comp = ed.add_get_member_variable_node("Comp")
    names = ed.add_get_member_variable_node("CachedNames", PL_C); connect(out(comp), selfpin(names), "comp -> CachedNames")
    allowed = ed.add_get_member_variable_node("CachedAllowed", PL_C); connect(out(comp), selfpin(allowed), "comp -> CachedAllowed")
    myrank = ed.add_get_member_variable_node("CachedMyRank", PL_C); connect(out(comp), selfpin(myrank), "comp -> CachedMyRank")
    is_gm = call(ed, M + "EqualEqual_ByteByte", "MyRank==3"); connect(out(myrank), pin(is_gm, "A"), "rank"); setval(is_gm, "B", "3")
    # title
    st = call(ed, "/Script/UMG.TextBlock:SetText", "SetText(title)"); connect(out(title_n), selfpin(st), "TitleText -> SetText"); setval(st, "InText", text_lit("ClanRanksTitle", "Clan Ranks"))
    connect(tail, exec_in(st), "-> title"); tail = then_out(st)
    # header: 4 editable rank names
    for r in range(4):
        box = construct("/Script/UMG.EditableTextBox", f"name box {r}")
        connect(tail, exec_in(box), f"-> construct box {r}"); tail = then_out(box); bp_ = out(box, "ReturnValue")
        stx = call(ed, "/Script/UMG.EditableTextBox:SetText", f"SetText(box {r})"); connect(bp_, selfpin(stx), "box -> SetText"); connect(to_text_from_string(array_get(out(names), r)), pin(stx, "InText"), f"name[{r}]")
        connect(tail, exec_in(stx), "-> SetText"); tail = then_out(stx)
        en = call(ed, "/Script/UMG.Widget:SetIsEnabled", f"SetIsEnabled(box {r})"); connect(bp_, selfpin(en), "box"); connect(out(is_gm, "ReturnValue"), pin(en, "bInIsEnabled"), "GM?"); connect(tail, exec_in(en), "-> enable"); tail = then_out(en)
        tail = add_to_grid(bp_, 0, r + 1, tail)
        before = snapshot(ed)
        asg = create_by_search(ed, [bp_], ("Assign", "OnTextCommitted"), f"Assign OnTextCommitted [{r}]", exact="TextBox|Event|AssignOnTextCommitted")
        h = [n for n in new_nodes(ed, before) if n.get_class().get_name() == "K2Node_CustomEvent"]; check(len(h) == 1, f"commit handler {r}"); h = h[0]
        sp = selfpin(asg)
        if sp is not None and not list(PL.list_connected_pins(sp)): connect(bp_, sp, "box -> Assign.self")
        connect(tail, exec_in(asg), "-> Assign"); tail = then_out(asg)
        lib.compile_blueprint(w)
        rpc = call(ed, f"{PL_C}:Server_ServerSetRankName_0", "ServerSetRankName"); connect(out(comp), selfpin(rpc), "comp -> rpc"); setval(rpc, "Rank", str(r))
        t2s = call(ed, T + "Conv_TextToString", "TextToString"); connect(out(h, "Text"), pin(t2s, "InText"), "committed text"); connect(out(t2s, "ReturnValue"), pin(rpc, "Name"), "name")
        connect(then_out(h), exec_in(rpc), f"commit[{r}] -> rpc")
    # rows
    cells = ed.add_get_member_variable_node("Cells"); cellidx = ed.add_get_member_variable_node("CellIdx")
    shared_event = None
    for row, perm in enumerate(SHOWN_PERMS, start=1):
        lab = construct("/Script/UMG.TextBlock", f"label {perm}"); connect(tail, exec_in(lab), "-> construct label"); tail = then_out(lab)
        ptt = call(ed, f"{BPL_C}:PermToText", "PermToText"); setval(ptt, "Perm", str(perm))
        stl = call(ed, "/Script/UMG.TextBlock:SetText", f"SetText(label {perm})"); connect(out(lab, "ReturnValue"), selfpin(stl), "label"); connect(out(ptt, "Result"), pin(stl, "InText"), "perm text")
        connect(tail, exec_in(stl), "-> SetText"); tail = then_out(stl)
        tail = add_to_grid(out(lab, "ReturnValue"), row, 0, tail)
        for rank in range(4):
            cb = construct("/Script/UMG.CheckBox", f"cell {perm}/{rank}"); connect(tail, exec_in(cb), "-> construct cell"); tail = then_out(cb); cp = out(cb, "ReturnValue")
            sic = call(ed, "/Script/UMG.CheckBox:SetIsChecked", "SetIsChecked"); connect(cp, selfpin(sic), "cell"); connect(array_get(out(allowed), perm * 4 + rank), pin(sic, "InIsChecked"), "allowed[i]")
            connect(tail, exec_in(sic), "-> SetIsChecked"); tail = then_out(sic)
            en = call(ed, "/Script/UMG.Widget:SetIsEnabled", "SetIsEnabled(cell)"); connect(cp, selfpin(en), "cell")
            if rank == 3: setval(en, "bInIsEnabled", "false")
            else: connect(out(is_gm, "ReturnValue"), pin(en, "bInIsEnabled"), "GM?")
            connect(tail, exec_in(en), "-> enable"); tail = then_out(en)
            tail = add_to_grid(cp, row, rank + 1, tail)
            a1 = array_add(out(cells), cp); connect(tail, exec_in(a1), "-> Cells.Add"); tail = then_out(a1)
            a2 = array_add(out(cellidx), None) if False else None
            a2 = create_by_search(ed, [out(cellidx)], ("Array", "Add"), "CellIdx Add", exact="Utilities|Array|Add"); connect(out(cellidx), pin_exact_in(a2, "TargetArray"), "CellIdx -> Add"); PL.set_pin_value(pin_exact_in(a2, "NewItem"), str(perm * 4 + rank))
            connect(tail, exec_in(a2), "-> CellIdx.Add"); tail = then_out(a2)
            if shared_event is None:
                before = snapshot(ed)
                asg = create_by_search(ed, [cp], ("Assign", "OnCheckStateChanged"), "Assign OnCheckStateChanged", exact="CheckBox|Event|AssignOnCheckStateChanged")
                h = [n for n in new_nodes(ed, before) if n.get_class().get_name() == "K2Node_CustomEvent"]; check(len(h) == 1, "check handler"); shared_event = h[0]
                sp = selfpin(asg)
                if sp is not None and not list(PL.list_connected_pins(sp)): connect(cp, sp, "cell -> Assign.self")
                connect(tail, exec_in(asg), "-> Assign"); tail = then_out(asg)
            else:
                bnd = create_by_search(ed, [cp], ("BindEventto", "OnCheckStateChanged"), "Bind OnCheckStateChanged", exact="CheckBox|Event|BindEventtoOnCheckStateChanged")
                sp = selfpin(bnd)
                if sp is not None and not list(PL.list_connected_pins(sp)): connect(cp, sp, "cell -> Bind.self")
                connect(out(shared_event, "OutputDelegate"), pin(bnd, "Delegate"), "handler -> Bind"); connect(tail, exec_in(bnd), "-> Bind"); tail = then_out(bnd)
    # shared change handler: CachedAllowed[CellIdx[i]] = Cells[i].IsChecked, then send the table
    lp = None
    try: lp = ed.add_macro_node(FORLOOP)
    except Exception: pass
    check(lp is not None, "ForLoop")
    n_cells = len(SHOWN_PERMS) * 4
    PL.set_pin_value(pin_exact_in(lp, "FirstIndex"), "0"); PL.set_pin_value(pin_exact_in(lp, "LastIndex"), str(n_cells - 1))
    connect(then_out(shared_event), pin_exact_in(lp, "execute"), "handler -> ForLoop"); idx = pin_exact_out(lp, "Index")
    comp2 = ed.add_get_member_variable_node("Comp"); allowed2 = ed.add_get_member_variable_node("CachedAllowed", PL_C); connect(out(comp2), selfpin(allowed2), "comp -> CachedAllowed")
    cells2 = ed.add_get_member_variable_node("Cells"); cellidx2 = ed.add_get_member_variable_node("CellIdx")
    cell_i = array_get(out(cells2), idx); idx_i = array_get(out(cellidx2), idx)
    isc = call(ed, "/Script/UMG.CheckBox:IsChecked", "IsChecked"); connect(cell_i, selfpin(isc), "cell[i]")
    setel = create_by_search(ed, [out(allowed2)], ("Array", "SetArrayElem"), "Array Set", exact="Utilities|Array|SetArrayElem"); print("   Array Set pins:", pins(setel))
    connect(out(allowed2), pin_exact_in(setel, "TargetArray"), "CachedAllowed -> Set"); connect(idx_i, pin_exact_in(setel, "Index"), "idx"); connect(out(isc, "ReturnValue"), pin_exact_in(setel, "Item"), "checked")
    connect(pin_exact_out(lp, "LoopBody"), exec_in(setel), "body -> Set")
    rpc = call(ed, f"{PL_C}:Server_ServerSetTable_0", "ServerSetTable"); connect(out(comp2), selfpin(rpc), "comp -> rpc")
    allowed3 = ed.add_get_member_variable_node("CachedAllowed", PL_C); connect(out(comp2), selfpin(allowed3), "comp"); connect(out(allowed3), pin(rpc, "Allowed"), "table -> rpc")
    connect(pin_exact_out(lp, "Completed"), exec_in(rpc), "Completed -> ServerSetTable")
    # close button
    before = snapshot(ed)
    asg = create_by_search(ed, [out(close_n)], ("Assign", "OnClicked"), "Assign OnClicked", exact="Button|Event|AssignOnClicked")
    h = [n for n in new_nodes(ed, before) if n.get_class().get_name() == "K2Node_CustomEvent"]; check(len(h) == 1, "click handler"); h = h[0]
    sp = selfpin(asg)
    if sp is not None and not list(PL.list_connected_pins(sp)): connect(out(close_n), sp, "CloseButton -> Assign.self")
    connect(tail, exec_in(asg), "-> Assign OnClicked"); tail = then_out(asg)
    rfp = call(ed, "/Script/UMG.Widget:RemoveFromParent", "RemoveFromParent"); connect(then_out(h), exec_in(rfp), "click -> RemoveFromParent")
    gop2 = create_by_search(ed, [], ("GetOwningPlayer",), "GetOwningPlayer", prefer=["|GetOwningPlayer"])
    imode = call(ed, "/Script/UMG.WidgetBlueprintLibrary:SetInputMode_GameOnly", "SetInputModeGameOnly"); connect(out(gop2, "ReturnValue"), pin(imode, "PlayerController"), "PC"); connect(then_out(rfp), exec_in(imode), "-> game input")
    smc = ed.add_set_member_variable_node("bShowMouseCursor", "/Script/Engine.PlayerController"); check(smc is not None, "Set bShowMouseCursor")
    if smc is not None:
        print("   Set bShowMouseCursor pins:", pins(smc)); connect(out(gop2, "ReturnValue"), selfpin(smc), "PC"); PL.set_pin_value(pin_exact_in(smc, "bShowMouseCursor"), "false"); connect(then_out(imode), exec_in(smc), "-> hide cursor")

sec("compile")
compile_ok(w, [(ed, "EventGraph")], "W_GA_ClanRanks")
if MODE == "real" and not failures: save(w, os.path.join(DISK_LOCAL, "W_GA_ClanRanks.uasset"), "W_GA_ClanRanks")
elif MODE == "real": print("   NOT SAVING: failures above")
result()
