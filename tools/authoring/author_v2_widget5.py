"""v2 - Clan panel, fifth version: Ranks table + Permissions table styled like the roster, rename via a modal.
Run WITH -ModDevKit. GA_MODE=dry|real. Rebuilds the EventGraph from scratch every run. Needs W_GA_CellButton (author_v2_styled_buttons.py).

Layout (all built at runtime into the skeleton's canvas, PermGrid/TitleText/CloseButton collapsed):
  Root VerticalBox (anchored fill, 20 px side padding like the roster)
    RanksBox   : header [Badge | Rank Name | Ranking] + 4 rows (Guild Master first); the name cell is a W_GA_CellButton with
                 the vanilla pencil icon; rows are 44 px SizeBoxes with the roster's highlight material on alternate rows
    PermsScroll: ScrollBox > VerticalBox: header [Ability | badge+name x4] + 6 static rows of checkmark / dash
  Rename modal: built once, collapsed, parented to the clan window's root overlay: dim layer + panel (T_BgPanel) with
                 title, W_FCEditableTextBlock, Confirm / Cancel (vanilla buttons). Confirm -> Server_ServerSetRankName_0,
                 CachedNames[rank] updated, every name text refreshed.
Custom events: ShowRanks, ShowPerms (called by the tabs).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
W_PATH = f"{LOCAL}/W_GA_ClanRanks"
BPL_C = f"{LOCAL}/BPL_GuildAccess.BPL_GuildAccess_C"; PL_C = f"{LOCAL}/BPC_GA_Player.BPC_GA_Player_C"
CELL_C = f"{LOCAL}/W_GA_CellButton.W_GA_CellButton_C"; BTN_C = "/Game/UI/Widgets/Buttons/WBP_ButtonBase.WBP_ButtonBase_C"; EDIT_C = "/Game/UI/Framework/W_FCEditableTextBlock.W_FCEditableTextBlock_C"
GT = "/Script/ConanSandbox.GeneralText"
ST_HEAD = "/Game/UI/Styling/Texts/FS_Text_Heading_5.FS_Text_Heading_5_C"; ST_BODY = "/Game/UI/Styling/Texts/FS_Text_Body_4.FS_Text_Body_4_C"; ST_TITLE = "/Game/UI/Styling/Texts/FS_Text_Heading_3.FS_Text_Heading_3_C"
TINT = "(SpecifiedColor=(R=0.854993,G=0.775822,B=0.637597,A=0.700000),ColorUseRule=UseColor_Specified)"; TINT1 = "(SpecifiedColor=(R=0.854993,G=0.775822,B=0.637597,A=1.000000),ColorUseRule=UseColor_Specified)"
LIN = "(R=0.854993,G=0.775822,B=0.637597,A=1.000000)"
BADGES = ["/Game/UI/Textures/GUIs/Guild/T_Rank_Recruit.T_Rank_Recruit", "/Game/UI/Textures/GUIs/Guild/T_Rank_Member.T_Rank_Member", "/Game/UI/Textures/GUIs/Guild/T_Rank_Officer.T_Rank_Officer", "/Game/UI/Textures/GUIs/Guild/T_Rank_GuildMaster.T_Rank_GuildMaster"]
PENCIL = "/Game/UI/Textures/GUIs/Guild/T_EditButton.T_EditButton"; CHECK = "/Game/UI/Textures/Components/T_Checkmark.T_Checkmark"; BG = "/Game/UI/Textures/GUIs/Guild/T_BgPanel.T_BgPanel"
ROWFILL = "(R=0.000000,G=0.000000,B=0.000000,A=0.220000)"   # the roster's row bar, as a flat tint
# vanilla popup chrome, as Make Slate Brush pin values (pin name -> literal)
WIN_BG = {"ResourceObject": "/Game/UI/Textures/Backgrounds/T_UI_GeneralWindow_Background.T_UI_GeneralWindow_Background", "ImageSize": "(X=512.000000,Y=512.000000)", "Margin": "(Left=0.050000,Top=0.050000,Right=0.050000,Bottom=0.050000)", "Tiling": "Both", "DrawAs": "Image"}
FRAME_H = {"ResourceObject": "/Game/UI/Textures/Backgrounds/T_UI_Panel_Frame_TopBottom.T_UI_Panel_Frame_TopBottom", "ImageSize": "(X=512.000000,Y=32.000000)", "Margin": "(Left=0.000000,Top=0.250000,Right=0.000000,Bottom=0.250000)", "DrawAs": "Box"}
FRAME_V = {"ResourceObject": "/Game/UI/Textures/Backgrounds/T_UI_Panel_Frame_LeftRight.T_UI_Panel_Frame_LeftRight", "ImageSize": "(X=32.000000,Y=512.000000)", "Margin": "(Left=0.250000,Top=0.000000,Right=0.250000,Bottom=0.000000)", "DrawAs": "Box"}
BLOSSOM = {"ResourceObject": "/Game/UI/Materials/General/M_UI_Blossom_Blank.M_UI_Blossom_Blank", "DrawAs": "Image"}
FLOURISH = {"ResourceObject": "/Game/UI/Textures/Backgrounds/T_UI_Panel_Frame_Flourishes.T_UI_Panel_Frame_Flourishes", "ImageSize": "(X=64.000000,Y=128.000000)", "Margin": "(Left=0.250000,Top=0.250000,Right=0.250000,Bottom=0.250000)", "DrawAs": "Box"}
# permissions (Title Case); columns are ranks 3,2,1,0 = Guild Master, Officer, Member, Recruit
PERMS = [("Access Base", [1, 1, 1, 1]), ("Command Thralls", [1, 1, 1, 1]), ("Manage Members", [1, 1, 0, 0]), ("Welcome Message", [1, 1, 0, 0]), ("Manage Guild", [1, 0, 0, 0]), ("Set Access", [1, 0, 0, 0])]
COLS = [3, 2, 1, 0]
M = "/Script/Engine.KismetMathLibrary:"; T = "/Script/Engine.KismetTextLibrary:"
sec(f"mode = {MODE}")
wait_registry()
w = unreal.load_asset(W_PATH); check(w is not None, "loaded W_GA_ClanRanks"); ed = GE.get_graph_editor_by_name(w, "EventGraph")
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def pin(n, name): return pin_exact_in(n, name)
def selfpin(n): return lib.find_self_pin(n) or pin_exact_in(n, "self")
def first_param(n): return next((p for p in lib.list_input_pins(n) if str(PL.get_pin_name(p)) not in ("self", "execute")), None)
def fn(path, label, tail, **vals):
    """call a function in the exec chain; literal pin values from kwargs (pin name -> literal). Returns node; use .then via then_out"""
    n = call(ed, path, label)
    for k, v in vals.items(): check(PL.set_pin_value(pin(n, k), v), f"{label}.{k}")
    if tail is not None: connect(tail, exec_in(n), f"-> {label}")
    return n
def construct(cls_path, label, tail):
    n = create_by_search(ed, [], ("ConstructObjectfromClass",), f"Construct {label}", exact="Game|ConstructObjectfromClass")
    check(PL.set_pin_value(pin(n, "Class"), cls_path), f"{label}: class"); connect(tail, exec_in(n), f"-> {label}"); return out(n, "ReturnValue"), then_out(n)
def create_widget(cls_path, label, tail):
    n = create_by_search(ed, [], ("CreateWidget",), f"CreateWidget {label}", exact="UserInterface|CreateWidget")
    check(PL.set_pin_value(pin(n, "Class"), cls_path), f"{label}: class"); connect(pc, pin(n, "OwningPlayer"), "owner"); connect(tail, exec_in(n), f"-> {label}"); return out(n, "ReturnValue"), then_out(n)
def setup_child(widget_pin, tail, label):
    h = ed.add_get_member_variable_node("Host"); s = call(ed, "/Script/ConanSandbox.RootWidget:SetupNewChild", f"SetupNewChild({label})")
    connect(out(h), selfpin(s), "Host"); connect(widget_pin, pin(s, "child"), "child"); connect(tail, exec_in(s), "-> SetupNewChild"); return then_out(s)
def set_vis(widget_pin, vis, tail, label):
    v = call(ed, "/Script/UMG.Widget:SetVisibility", f"SetVisibility({label})"); connect(widget_pin, selfpin(v), label); setval(v, "InVisibility", vis); connect(tail, exec_in(v), f"-> {label} {vis}"); return then_out(v)
def styled_text(style_cls, tint, label, tail, text_pin=None, literal=None, justify=None):
    tp, tail = construct(GT, label, tail)
    ld = fn("/Script/Engine.KismetSystemLibrary:LoadClassAsset_Blocking", f"LoadClass({label})", tail); check(PL.set_pin_value(first_param(ld), style_cls), f"{label}: style literal"); tail = then_out(ld)
    cast = create_by_search(ed, [out(ld, "ReturnValue")], ("Casting", "CastToTextStyleDataAssetClass"), f"class cast ({label})", exact="Utilities|Casting|CastToTextStyleDataAssetClass")
    connect(out(ld, "ReturnValue"), first_param(cast), "class -> cast"); connect(tail, exec_in(cast), "-> cast"); tail = then_out(cast)
    ss = call(ed, "/Script/ConanSandbox.GeneralText:SetTextStyle", f"SetTextStyle({label})"); connect(tp, selfpin(ss), "text"); connect(as_pin(cast), first_param(ss), "style"); connect(tail, exec_in(ss), "-> SetTextStyle"); tail = then_out(ss)
    co = call(ed, "/Script/UMG.TextBlock:SetColorAndOpacity", f"tint({label})"); connect(tp, selfpin(co), "text"); check(PL.set_pin_value(first_param(co), tint), f"{label}: tint"); connect(tail, exec_in(co), "-> tint"); tail = then_out(co)
    st = call(ed, "/Script/UMG.TextBlock:SetText", f"SetText({label})"); connect(tp, selfpin(st), "text")
    if text_pin is not None: connect(text_pin, pin(st, "InText"), "text")
    else: setval(st, "InText", text_lit(label.replace(" ", ""), literal))
    connect(tail, exec_in(st), "-> SetText"); tail = then_out(st)
    if justify:
        jc = ed.add_set_member_variable_node("Justification", "/Script/UMG.TextBlock"); connect(tp, selfpin(jc), "text"); PL.set_pin_value(pin(jc, "Justification"), justify); connect(tail, exec_in(jc), "-> justify"); tail = then_out(jc)
    return tp, tail
def image(texture, w_, h_, label, tail, tint=None):
    """SizeBox(w x h)[Image(texture)] - the box pins the size, the image fills it. Returns (box pin, tail)."""
    ip, tail = construct("/Script/UMG.Image", label, tail)
    sb = call(ed, "/Script/UMG.Image:SetBrushFromTexture", f"SetBrush({label})"); connect(ip, selfpin(sb), "img"); check(PL.set_pin_value(pin(sb, "Texture"), texture), f"{label}: texture"); PL.set_pin_value(next((q for q in lib.list_input_pins(sb) if "Match" in str(PL.get_pin_name(q))), None), "false"); connect(tail, exec_in(sb), "-> brush"); tail = then_out(sb)
    if tint:
        co = call(ed, "/Script/UMG.Image:SetColorAndOpacity", f"tint({label})"); connect(ip, selfpin(co), "img"); check(PL.set_pin_value(first_param(co), tint), f"{label}: tint"); connect(tail, exec_in(co), "-> tint"); tail = then_out(co)
    bx, tail = construct("/Script/UMG.SizeBox", f"{label} box", tail)
    for f_, v_ in (("SetWidthOverride", w_), ("SetHeightOverride", h_)):
        n_ = call(ed, f"/Script/UMG.SizeBox:{f_}", f"{label} {f_}"); connect(bx, selfpin(n_), "box"); PL.set_pin_value(first_param(n_), f"{v_:.1f}"); connect(tail, exec_in(n_), f"-> {f_}"); tail = then_out(n_)
    a = call(ed, "/Script/UMG.PanelWidget:AddChild", f"{label} box <- image"); connect(bx, selfpin(a), "box"); connect(ip, pin(a, "Content"), "img"); connect(tail, exec_in(a), "-> add"); tail = then_out(a)
    return bx, tail
def hcell(hbox_pin, widget_pin, ratio, halign, tail, pad=None):
    a = call(ed, "/Script/UMG.HorizontalBox:AddChildToHorizontalBox", "AddChildToHorizontalBox"); connect(hbox_pin, selfpin(a), "hbox"); connect(widget_pin, pin(a, "Content"), "cell"); connect(tail, exec_in(a), "-> add cell"); tail = then_out(a); sl = out(a, "ReturnValue")
    s = call(ed, "/Script/UMG.HorizontalBoxSlot:SetSize", "cell size"); connect(sl, selfpin(s), "slot"); check(PL.set_pin_value(first_param(s), f"(Value={ratio:.6f},SizeRule=Fill)"), "cell size literal"); connect(tail, exec_in(s), "-> size"); tail = then_out(s)
    h = call(ed, "/Script/UMG.HorizontalBoxSlot:SetHorizontalAlignment", "cell halign"); connect(sl, selfpin(h), "slot"); setval(h, "InHorizontalAlignment", "HAlign_" + halign); connect(tail, exec_in(h), "-> halign"); tail = then_out(h)
    v = call(ed, "/Script/UMG.HorizontalBoxSlot:SetVerticalAlignment", "cell valign"); connect(sl, selfpin(v), "slot"); setval(v, "InVerticalAlignment", "VAlign_Center"); connect(tail, exec_in(v), "-> valign"); tail = then_out(v)
    if pad:
        p = call(ed, "/Script/UMG.HorizontalBoxSlot:SetPadding", "cell padding"); connect(sl, selfpin(p), "slot"); check(PL.set_pin_value(first_param(p), pad), "pad literal"); connect(tail, exec_in(p), "-> pad"); tail = then_out(p)
    return tail
def row(vbox_pin, label, tail, highlight, header=False):
    """SizeBox(44)[Overlay[highlight Image?, HorizontalBox]] appended to vbox. Returns (hbox pin, tail)."""
    sz, tail = construct("/Script/UMG.SizeBox", f"row box {label}", tail)
    if not header:
        ho = call(ed, "/Script/UMG.SizeBox:SetHeightOverride", "row height"); connect(sz, selfpin(ho), "sizebox"); PL.set_pin_value(first_param(ho), "40.0"); connect(tail, exec_in(ho), "-> height"); tail = then_out(ho)
    ov, tail = construct("/Script/UMG.Overlay", f"row overlay {label}", tail)
    sc = call(ed, "/Script/UMG.PanelWidget:AddChild", "sizebox <- overlay"); connect(sz, selfpin(sc), "sizebox"); connect(ov, pin(sc, "Content"), "overlay"); connect(tail, exec_in(sc), "-> add"); tail = then_out(sc)
    if highlight:
        hi, tail = construct("/Script/UMG.Image", f"highlight {label}", tail)
        bm = call(ed, "/Script/UMG.Image:SetColorAndOpacity", "row fill"); connect(hi, selfpin(bm), "img"); check(PL.set_pin_value(first_param(bm), ROWFILL), "row fill literal"); connect(tail, exec_in(bm), "-> fill"); tail = then_out(bm)
        hv = call(ed, "/Script/UMG.Widget:SetVisibility", "highlight hit-test"); connect(hi, selfpin(hv), "img"); setval(hv, "InVisibility", "SelfHitTestInvisible"); connect(tail, exec_in(hv), "-> vis"); tail = then_out(hv)
        ao = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", "overlay <- highlight"); connect(ov, selfpin(ao), "overlay"); connect(hi, pin(ao, "Content"), "img"); connect(tail, exec_in(ao), "-> add"); tail = then_out(ao)
        for f_, v_ in (("SetHorizontalAlignment", "HAlign_Fill"), ("SetVerticalAlignment", "VAlign_Fill")):
            s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); check(PL.set_pin_value(first_param(s), v_), f"{f_} {v_}"); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
        p = call(ed, "/Script/UMG.OverlaySlot:SetPadding", "highlight pad"); connect(out(ao, "ReturnValue"), selfpin(p), "slot"); PL.set_pin_value(first_param(p), "(Left=0.000000,Top=3.000000,Right=0.000000,Bottom=3.000000)"); connect(tail, exec_in(p), "-> pad"); tail = then_out(p)
    hb, tail = construct("/Script/UMG.HorizontalBox", f"row hbox {label}", tail)
    ao = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", "overlay <- hbox"); connect(ov, selfpin(ao), "overlay"); connect(hb, pin(ao, "Content"), "hbox"); connect(tail, exec_in(ao), "-> add"); tail = then_out(ao)
    for f_, v_ in (("SetHorizontalAlignment", "HAlign_Fill"), ("SetVerticalAlignment", "VAlign_Fill")):
        s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); check(PL.set_pin_value(first_param(s), v_), f"{f_} {v_}"); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
    av = call(ed, "/Script/UMG.VerticalBox:AddChildToVerticalBox", "vbox <- row"); connect(vbox_pin, selfpin(av), "vbox"); connect(sz, pin(av, "Content"), "row"); connect(tail, exec_in(av), "-> add row"); tail = then_out(av)
    if header:
        p = call(ed, "/Script/UMG.VerticalBoxSlot:SetPadding", "header pad"); connect(out(av, "ReturnValue"), selfpin(p), "slot"); PL.set_pin_value(first_param(p), "(Left=0.000000,Top=28.000000,Right=0.000000,Bottom=5.000000)"); connect(tail, exec_in(p), "-> pad"); tail = then_out(p)
    return hb, tail
def array_get(arr_pin, idx):
    g = create_by_search(ed, [arr_pin], ("Array", "Get"), "Array Get", prefer=["|Get(acopy)"])
    connect(arr_pin, pin_exact_in(g, "Array") or pin_exact_in(g, "TargetArray"), "array -> Get")
    ip = pin_exact_in(g, "Dimension 1") or pin_exact_in(g, "Index")
    if isinstance(idx, int): PL.set_pin_value(ip, str(idx))
    else: connect(idx, ip, "index -> Get")
    return out(g)
def array_add(arr_pin, item_pin, tail):
    a = create_by_search(ed, [arr_pin], ("Array", "Add"), "Array Add", exact="Utilities|Array|Add")
    connect(arr_pin, pin_exact_in(a, "TargetArray"), "array -> Add"); connect(item_pin, pin_exact_in(a, "NewItem"), "item -> Add"); connect(tail, exec_in(a), "-> Add"); return then_out(a)
def name_text(r):
    s2t = call(ed, T + "Conv_StringToText", f"name {r}"); connect(array_get(out(names), r), pin(s2t, "InString"), f"CachedNames[{r}]"); return out(s2t, "ReturnValue")
def assign(obj_pin, exact, label):
    before = snapshot(ed)
    asg = create_by_search(ed, [obj_pin], tuple(exact.split("|")[-1:]), label, exact=exact)
    h = [n for n in new_nodes(ed, before) if n.get_class().get_name() == "K2Node_CustomEvent"]; check(len(h) == 1, f"{label}: handler"); h = h[0] if h else None
    sp = selfpin(asg)
    if sp is not None and not list(PL.list_connected_pins(sp)): connect(obj_pin, sp, f"{label}: self")
    return asg, h

# ---- rebuild
keep = {n.get_name() for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_Event"}
ed.remove_nodes([n for n in ed.list_all_nodes() if n.get_name() not in keep]); print("   graph cleared (events kept)")
for nm in ("Cells", "CellIdx", "Boxes", "Comp", "Host", "RanksBox", "PermsScroll", "NameTexts", "HeadTexts", "CellButtons", "EditRank", "ModalRoot", "ModalEdit"):
    if nm in [str(v) for v in lib.list_member_variable_names(w)]: ed.remove_member_variable(nm)
lib.compile_blueprint(w)
gt_ref = lib.get_object_reference_type(unreal.GeneralText)
for nm, t in (("Comp", lib.get_object_reference_type(unreal.load_class(None, PL_C))), ("Host", lib.get_object_reference_type(unreal.GuildViewBase)), ("RanksBox", lib.get_object_reference_type(unreal.Widget)), ("PermsScroll", lib.get_object_reference_type(unreal.Widget)),
              ("NameTexts", lib.get_array_type(gt_ref)), ("HeadTexts", lib.get_array_type(gt_ref)), ("CellButtons", lib.get_array_type(lib.get_object_reference_type(unreal.FLXButtonBase))), ("EditRank", lib.get_basic_type_by_name("int")),
              ("ModalRoot", lib.get_object_reference_type(unreal.Widget)), ("ModalEdit", lib.get_object_reference_type(unreal.FCEditableTextBase))):
    check(lib.add_member_variable(w, nm, t), f"var {nm}")
lib.compile_blueprint(w)
grid = ed.add_get_member_variable_node("PermGrid"); title_n = ed.add_get_member_variable_node("TitleText"); close_n = ed.add_get_member_variable_node("CloseButton")
ev = [n for n in ed.list_all_nodes() if title(n) == "Event Construct"][0]; tail = then_out(ev)
gop = create_by_search(ed, [], ("GetOwningPlayer",), "GetOwningPlayer", prefer=["|GetOwningPlayer"]); pc = out(gop, "ReturnValue")
gcb = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(Player)"); connect(pc, pin(gcb, "self"), "PC -> gcb"); setval(gcb, "ComponentClass", PL_C)
sc = ed.add_set_member_variable_node("Comp"); connect(out(gcb, "ReturnValue"), pin(sc, "Comp"), "-> Comp"); connect(tail, exec_in(sc), "-> Set Comp"); tail = then_out(sc)
comp = ed.add_get_member_variable_node("Comp"); names = ed.add_get_member_variable_node("CachedNames", PL_C); connect(out(comp), selfpin(names), "comp -> CachedNames")
myrank = ed.add_get_member_variable_node("CachedMyRank", PL_C); connect(out(comp), selfpin(myrank), "comp -> CachedMyRank")
is_gm = call(ed, M + "EqualEqual_ByteByte", "MyRank==3"); connect(out(myrank), pin(is_gm, "A"), "rank"); setval(is_gm, "B", "3")
for n_, l_ in ((title_n, "TitleText"), (close_n, "CloseButton"), (grid, "PermGrid")): tail = set_vis(out(n_), "Collapsed", tail, l_)
# ---- root VerticalBox into the canvas, anchored fill
gp = call(ed, "/Script/UMG.Widget:GetParent", "GetParent(PermGrid)"); connect(out(grid), selfpin(gp), "PermGrid")
cast_c = create_by_search(ed, [out(gp, "ReturnValue")], ("Casting", "CastToCanvasPanel"), "Cast To CanvasPanel", exact="Utilities|Casting|CastToCanvasPanel"); connect(out(gp, "ReturnValue"), pin(cast_c, "Object"), "-> cast"); connect(tail, exec_in(cast_c), "-> cast canvas"); tail = then_out(cast_c)
root, tail = construct("/Script/UMG.VerticalBox", "root vbox", tail)
ac = call(ed, "/Script/UMG.CanvasPanel:AddChildToCanvas", "canvas <- root"); connect(as_pin(cast_c), selfpin(ac), "canvas"); connect(root, pin(ac, "Content"), "root"); connect(tail, exec_in(ac), "-> add"); tail = then_out(ac)
an = call(ed, "/Script/UMG.CanvasPanelSlot:SetAnchors", "anchors fill"); connect(out(ac, "ReturnValue"), selfpin(an), "slot"); check(PL.set_pin_value(first_param(an), "(Minimum=(X=0.000000,Y=0.000000),Maximum=(X=1.000000,Y=1.000000))"), "anchors"); connect(tail, exec_in(an), "-> anchors"); tail = then_out(an)
of = call(ed, "/Script/UMG.CanvasPanelSlot:SetOffsets", "offsets"); connect(out(ac, "ReturnValue"), selfpin(of), "slot"); check(PL.set_pin_value(first_param(of), "(Left=20.000000,Top=0.000000,Right=20.000000,Bottom=0.000000)"), "offsets"); connect(tail, exec_in(of), "-> offsets"); tail = then_out(of)
# ---- Ranks table
rb, tail = construct("/Script/UMG.VerticalBox", "RanksBox", tail); srb = ed.add_set_member_variable_node("RanksBox"); connect(rb, pin(srb, "RanksBox"), "-> RanksBox"); connect(tail, exec_in(srb), "-> Set RanksBox"); tail = then_out(srb)
av = call(ed, "/Script/UMG.VerticalBox:AddChildToVerticalBox", "root <- RanksBox"); connect(root, selfpin(av), "root"); connect(rb, pin(av, "Content"), "RanksBox"); connect(tail, exec_in(av), "-> add"); tail = then_out(av)
hb, tail = row(rb, "ranks header", tail, highlight=False, header=True)
for txt, ratio, hal in (("Badge", 0.1, "Center"), ("Rank Name", 0.6, "Left"), ("Ranking", 0.3, "Center")):
    tp, tail = styled_text(ST_HEAD, TINT, f"ranks head {txt}", tail, literal=txt, justify="Center" if hal == "Center" else None)
    tail = hcell(hb, tp, ratio, hal, tail, pad="(Left=12.000000,Top=0.000000,Right=0.000000,Bottom=0.000000)" if txt == "Rank Name" else None)
nametexts = ed.add_get_member_variable_node("NameTexts"); cellbtns = ed.add_get_member_variable_node("CellButtons"); headtexts = ed.add_get_member_variable_node("HeadTexts")
cell_pins = {}; cell_widgets = {}
for r in range(4):   # created in rank order so CellButtons[rank] / NameTexts[rank] hold the cell
    ov, tail = construct("/Script/UMG.Overlay", f"name cell {r}", tail)
    hb_, tail = construct("/Script/UMG.HorizontalBox", f"name hbox {r}", tail)
    pen, tail = image(PENCIL, 16, 16, f"pencil {r}", tail); tail = hcell(hb_, pen, 0.0, "Left", tail)
    nt, tail = styled_text(ST_BODY, TINT, f"name text {r}", tail, text_pin=name_text(r)); tail = hcell(hb_, nt, 1.0, "Left", tail, pad="(Left=8.000000,Top=0.000000,Right=0.000000,Bottom=0.000000)")
    tail = array_add(out(nametexts), nt, tail)
    a_ = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", f"cell <- hbox {r}"); connect(ov, selfpin(a_), "overlay"); connect(hb_, pin(a_, "Content"), "hbox"); connect(tail, exec_in(a_), "-> add"); tail = then_out(a_)
    for f_, v_ in (("SetHorizontalAlignment", "HAlign_Left"), ("SetVerticalAlignment", "VAlign_Center")):
        s_ = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(a_, "ReturnValue"), selfpin(s_), "slot"); check(PL.set_pin_value(first_param(s_), v_), v_); connect(tail, exec_in(s_), f"-> {f_}"); tail = then_out(s_)
    bp_, tail = create_widget(CELL_C, f"cell {r}", tail)
    ud = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetUserDataAsInt", f"userdata {r}"); connect(bp_, selfpin(ud), "btn"); PL.set_pin_value(first_param(ud), str(r)); connect(tail, exec_in(ud), "-> userdata"); tail = then_out(ud)
    en = call(ed, "/Script/UMG.Widget:SetIsEnabled", f"enable cell {r}"); connect(bp_, selfpin(en), "btn"); connect(out(is_gm, "ReturnValue"), pin(en, "bInIsEnabled"), "GM?"); connect(tail, exec_in(en), "-> enable"); tail = then_out(en)
    a2_ = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", f"cell <- button {r}"); connect(ov, selfpin(a2_), "overlay"); connect(bp_, pin(a2_, "Content"), "btn"); connect(tail, exec_in(a2_), "-> add"); tail = then_out(a2_)
    for f_, v_ in (("SetHorizontalAlignment", "HAlign_Fill"), ("SetVerticalAlignment", "VAlign_Fill")):
        s_ = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(a2_, "ReturnValue"), selfpin(s_), "slot"); check(PL.set_pin_value(first_param(s_), v_), v_); connect(tail, exec_in(s_), f"-> {f_}"); tail = then_out(s_)
    tail = array_add(out(cellbtns), bp_, tail); cell_pins[r] = bp_; cell_widgets[r] = ov
for i, r in enumerate(COLS):
    hb, tail = row(rb, f"rank row {r}", tail, highlight=(i % 2 == 0))
    ip, tail = image(BADGES[r], 16, 23, f"badge {r}", tail); tail = hcell(hb, ip, 0.1, "Center", tail)
    tail = hcell(hb, cell_widgets[r], 0.6, "Fill", tail); tail = setup_child(cell_pins[r], tail, f"cell {r}")
    tp, tail = styled_text(ST_BODY, TINT, f"ranking {r}", tail, literal=str(r + 1), justify="Center"); tail = hcell(hb, tp, 0.3, "Center", tail)
# ---- Permissions table (ScrollBox > VerticalBox)
ps, tail = construct("/Script/UMG.ScrollBox", "PermsScroll", tail); sps = ed.add_set_member_variable_node("PermsScroll"); connect(ps, pin(sps, "PermsScroll"), "-> PermsScroll"); connect(tail, exec_in(sps), "-> Set PermsScroll"); tail = then_out(sps)
av = call(ed, "/Script/UMG.VerticalBox:AddChildToVerticalBox", "root <- PermsScroll"); connect(root, selfpin(av), "root"); connect(ps, pin(av, "Content"), "scroll"); connect(tail, exec_in(av), "-> add"); tail = then_out(av)
ss = call(ed, "/Script/UMG.VerticalBoxSlot:SetSize", "scroll fill"); connect(out(av, "ReturnValue"), selfpin(ss), "slot"); PL.set_pin_value(first_param(ss), "(Value=1.000000,SizeRule=Fill)"); connect(tail, exec_in(ss), "-> fill"); tail = then_out(ss)
pb, tail = construct("/Script/UMG.VerticalBox", "perms vbox", tail)
ac2 = call(ed, "/Script/UMG.PanelWidget:AddChild", "scroll <- vbox"); connect(ps, selfpin(ac2), "scroll"); connect(pb, pin(ac2, "Content"), "vbox"); connect(tail, exec_in(ac2), "-> add"); tail = then_out(ac2)
hb, tail = row(pb, "perms header", tail, highlight=False, header=True)
tp, tail = styled_text(ST_HEAD, TINT, "perms head Ability", tail, literal="Ability"); tail = hcell(hb, tp, 0.34, "Left", tail)
head_cells = {}
for r in range(4):
    cellbox, tail = construct("/Script/UMG.HorizontalBox", f"perm head {r}", tail)
    ip, tail = image(BADGES[r], 16, 23, f"head badge {r}", tail); tail = hcell(cellbox, ip, 1.0, "Center", tail)
    tp, tail = styled_text(ST_HEAD, TINT, f"perm head name {r}", tail, text_pin=name_text(r)); tail = hcell(cellbox, tp, 0.0, "Left", tail); tail = set_vis(tp, "Collapsed", tail, f"perm head name {r}")
    tail = array_add(out(headtexts), tp, tail); head_cells[r] = cellbox
for r in COLS: tail = hcell(hb, head_cells[r], 0.165, "Center", tail)
for i, (ability, flags) in enumerate(PERMS):
    hb, tail = row(pb, f"perm row {i}", tail, highlight=(i % 2 == 0))
    tp, tail = styled_text(ST_BODY, TINT, f"perm {ability}", tail, literal=ability); tail = hcell(hb, tp, 0.34, "Left", tail)
    for ci, r in enumerate(COLS):
        if flags[ci]:
            ip, tail = image(CHECK, 16, 16, f"check {i}/{r}", tail, tint=LIN); tail = hcell(hb, ip, 0.165, "Center", tail)
        else:
            dp, tail = styled_text(ST_BODY, TINT, f"dash {i}/{r}", tail, literal="-", justify="Center"); tail = hcell(hb, dp, 0.165, "Center", tail)
tail = set_vis(ps, "Collapsed", tail, "PermsScroll (start on Ranks)")
# ---- rename modal (built once, collapsed) in the clan window's root overlay (ButtonBar's parent)
host = ed.add_get_member_variable_node("Host"); bar = ed.add_get_member_variable_node("ButtonBar", "/Script/ConanSandbox.GuildViewBase"); connect(out(host), selfpin(bar), "host")
bgp = call(ed, "/Script/UMG.Widget:GetParent", "GetParent(ButtonBar)"); connect(out(bar), selfpin(bgp), "bar")
cast_o = create_by_search(ed, [out(bgp, "ReturnValue")], ("Casting", "CastToOverlay"), "Cast To Overlay (root)", exact="Utilities|Casting|CastToOverlay"); connect(out(bgp, "ReturnValue"), pin(cast_o, "Object"), "-> cast"); connect(tail, exec_in(cast_o), "-> cast root overlay"); tail = then_out(cast_o)
mo, tail = construct("/Script/UMG.Overlay", "modal root", tail); smr = ed.add_set_member_variable_node("ModalRoot"); connect(mo, pin(smr, "ModalRoot"), "-> ModalRoot"); connect(tail, exec_in(smr), "-> Set ModalRoot"); tail = then_out(smr)
ao = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", "root overlay <- modal"); connect(as_pin(cast_o), selfpin(ao), "overlay"); connect(mo, pin(ao, "Content"), "modal"); connect(tail, exec_in(ao), "-> add"); tail = then_out(ao)
for f_, v_ in (("SetHorizontalAlignment", "Fill"), ("SetVerticalAlignment", "Fill")):
    s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); PL.set_pin_value(first_param(s), v_); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
dim, tail = construct("/Script/UMG.Image", "dim", tail)
co = call(ed, "/Script/UMG.Image:SetColorAndOpacity", "dim colour"); connect(dim, selfpin(co), "img"); PL.set_pin_value(first_param(co), "(R=0.000000,G=0.000000,B=0.000000,A=0.700000)"); connect(tail, exec_in(co), "-> dim"); tail = then_out(co)
ao = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", "modal <- dim"); connect(mo, selfpin(ao), "modal"); connect(dim, pin(ao, "Content"), "dim"); connect(tail, exec_in(ao), "-> add"); tail = then_out(ao)
for f_, v_ in (("SetHorizontalAlignment", "Fill"), ("SetVerticalAlignment", "Fill")):
    s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); PL.set_pin_value(first_param(s), v_); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
box, tail = construct("/Script/UMG.SizeBox", "modal box", tail)
wo = call(ed, "/Script/UMG.SizeBox:SetWidthOverride", "modal width"); connect(box, selfpin(wo), "box"); PL.set_pin_value(first_param(wo), "760.0"); connect(tail, exec_in(wo), "-> width"); tail = then_out(wo)
ao = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", "modal <- box"); connect(mo, selfpin(ao), "modal"); connect(box, pin(ao, "Content"), "box"); connect(tail, exec_in(ao), "-> add"); tail = then_out(ao)
for f_, v_ in (("SetHorizontalAlignment", "HAlign_Center"), ("SetVerticalAlignment", "VAlign_Center")):
    s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); check(PL.set_pin_value(first_param(s), v_), v_); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
inner, tail = construct("/Script/UMG.Overlay", "modal inner", tail)
sc2 = call(ed, "/Script/UMG.PanelWidget:AddChild", "box <- inner"); connect(box, selfpin(sc2), "box"); connect(inner, pin(sc2, "Content"), "inner"); connect(tail, exec_in(sc2), "-> add"); tail = then_out(sc2)
def layer(kind, brush, label, tail, pad, valign="VAlign_Fill", halign="HAlign_Fill"):
    """a Border or Image layer of the popup chrome, brush from the vanilla popup, added to the inner overlay"""
    wp, tail = construct(f"/Script/UMG.{kind}", label, tail)
    mk = create_by_search(ed, [], ("Struct", "MakeSlateBrush"), f"MakeSlateBrush({label})", exact="Utilities|Struct|MakeSlateBrush")
    if label == "window background": print("   MakeSlateBrush pins:", pins(mk))
    for k, v in brush.items():
        pk = next((q for q in lib.list_input_pins(mk) if str(PL.get_pin_name(q)) == k), None); check(pk is not None and PL.set_pin_value(pk, v), f"{label}: brush {k}")
    sb = call(ed, f"/Script/UMG.{kind}:SetBrush", f"brush({label})"); connect(wp, selfpin(sb), label); connect(out(mk), first_param(sb), "brush"); connect(tail, exec_in(sb), "-> brush"); tail = then_out(sb)
    if kind == "Image":
        hv = call(ed, "/Script/UMG.Widget:SetVisibility", f"{label} hit-test"); connect(wp, selfpin(hv), label); setval(hv, "InVisibility", "SelfHitTestInvisible"); connect(tail, exec_in(hv), "-> vis"); tail = then_out(hv)
    a = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", f"inner <- {label}"); connect(inner, selfpin(a), "inner"); connect(wp, pin(a, "Content"), label); connect(tail, exec_in(a), "-> add"); tail = then_out(a)
    for f_, v_ in (("SetHorizontalAlignment", halign), ("SetVerticalAlignment", valign)):
        s_ = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(a, "ReturnValue"), selfpin(s_), "slot"); check(PL.set_pin_value(first_param(s_), v_), v_); connect(tail, exec_in(s_), f"-> {f_}"); tail = then_out(s_)
    pd = call(ed, "/Script/UMG.OverlaySlot:SetPadding", f"{label} pad"); connect(out(a, "ReturnValue"), selfpin(pd), "slot"); check(PL.set_pin_value(first_param(pd), pad), f"{label}: pad"); connect(tail, exec_in(pd), "-> pad"); tail = then_out(pd)
    return wp, tail
_, tail = layer("Border", WIN_BG, "window background", tail, "(Left=10.000000,Top=2.000000,Right=10.000000,Bottom=2.000000)")
_, tail = layer("Border", FRAME_H, "frame top/bottom", tail, "(Left=8.000000,Top=1.000000,Right=8.000000,Bottom=1.000000)")
_, tail = layer("Border", FRAME_V, "frame left/right", tail, "(Left=10.000000,Top=0.000000,Right=10.000000,Bottom=0.000000)")
_, tail = layer("Image", BLOSSOM, "blossom", tail, "(Left=10.000000,Top=2.000000,Right=10.000000,Bottom=2.000000)")
_, tail = layer("Image", FLOURISH, "flourishes", tail, "(Left=0.000000,Top=0.000000,Right=0.000000,Bottom=0.000000)", valign="VAlign_Center")
mv, tail = construct("/Script/UMG.VerticalBox", "modal vbox", tail)
ao = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", "inner <- vbox"); connect(inner, selfpin(ao), "inner"); connect(mv, pin(ao, "Content"), "vbox"); connect(tail, exec_in(ao), "-> add"); tail = then_out(ao)
for f_, v_ in (("SetHorizontalAlignment", "HAlign_Fill"), ("SetVerticalAlignment", "VAlign_Center")):
    s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); check(PL.set_pin_value(first_param(s), v_), v_); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
p = call(ed, "/Script/UMG.OverlaySlot:SetPadding", "modal pad"); connect(out(ao, "ReturnValue"), selfpin(p), "slot"); PL.set_pin_value(first_param(p), "(Left=36.000000,Top=32.000000,Right=36.000000,Bottom=32.000000)"); connect(tail, exec_in(p), "-> pad"); tail = then_out(p)
def vadd(vb, wp, tail, pad=None, halign=None):
    a = call(ed, "/Script/UMG.VerticalBox:AddChildToVerticalBox", "vbox add"); connect(vb, selfpin(a), "vbox"); connect(wp, pin(a, "Content"), "child"); connect(tail, exec_in(a), "-> add"); tail = then_out(a)
    if pad:
        p_ = call(ed, "/Script/UMG.VerticalBoxSlot:SetPadding", "pad"); connect(out(a, "ReturnValue"), selfpin(p_), "slot"); PL.set_pin_value(first_param(p_), pad); connect(tail, exec_in(p_), "-> pad"); tail = then_out(p_)
    if halign:
        h_ = call(ed, "/Script/UMG.VerticalBoxSlot:SetHorizontalAlignment", "halign"); connect(out(a, "ReturnValue"), selfpin(h_), "slot"); check(PL.set_pin_value(first_param(h_), "HAlign_" + halign), halign); connect(tail, exec_in(h_), "-> halign"); tail = then_out(h_)
    return tail
tp, tail = styled_text(ST_TITLE, TINT1, "Rename Rank", tail, literal="Rename Rank", justify="Center"); tail = vadd(mv, tp, tail, pad="(Left=0.000000,Top=0.000000,Right=0.000000,Bottom=32.000000)", halign="Fill")
me, tail = create_widget(EDIT_C, "modal edit", tail); sme = ed.add_set_member_variable_node("ModalEdit"); connect(me, pin(sme, "ModalEdit"), "-> ModalEdit"); connect(tail, exec_in(sme), "-> Set ModalEdit"); tail = then_out(sme)
tail = vadd(mv, me, tail, pad="(Left=0.000000,Top=0.000000,Right=0.000000,Bottom=32.000000)", halign="Fill"); tail = setup_child(me, tail, "modal edit")
btns = {}
for lbl in ("Confirm", "Cancel"):
    bp_, tail = create_widget(BTN_C, f"modal {lbl}", tail)
    sl = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetLabel", f"SetLabel({lbl})"); connect(bp_, selfpin(sl), "btn"); lt = call(ed, T + "Conv_StringToText", f"{lbl} text"); setval(lt, "InString", lbl); connect(out(lt, "ReturnValue"), pin(sl, "NewLabel"), "text"); connect(tail, exec_in(sl), "-> label"); tail = then_out(sl)
    tail = vadd(mv, bp_, tail, pad="(Left=0.000000,Top=4.000000,Right=0.000000,Bottom=4.000000)", halign="Fill"); tail = setup_child(bp_, tail, f"modal {lbl}"); btns[lbl] = bp_
tail = set_vis(mo, "Collapsed", tail, "modal (start hidden)")
# ---- bindings: cell clicks (one handler, the button's user data = rank), Confirm, Cancel
asg, h_cell = assign(cell_pins[3], "Events|AssignSignalClicked", "Assign cell 3"); connect(tail, exec_in(asg), "-> Assign cell 3"); tail = then_out(asg)
lib.compile_blueprint(w)
for r in (2, 1, 0):
    a2 = call(ed, "/Script/ConanSandbox.FLXButtonBase:SignalClicked", f"bind cell {r}") if False else None
    asg2, h2 = assign(cell_pins[r], "Events|AssignSignalClicked", f"Assign cell {r}"); connect(tail, exec_in(asg2), f"-> Assign cell {r}"); tail = then_out(asg2)
    # share the first handler: point this Assign's delegate at handler 3 and drop the generated one
    dp = pin(asg2, "Delegate"); PL.break_pin_links(dp)
    if connect(out(h_cell, "OutputDelegate"), dp, f"cell {r} -> shared handler"): ed.remove_nodes([h2])
    else: print(f"   (cell {r} keeps its own handler)"); h_cell_extra = h2
    lib.compile_blueprint(w)
asg_ok, h_ok = assign(btns["Confirm"], "Events|AssignSignalClicked", "Assign Confirm"); connect(tail, exec_in(asg_ok), "-> Assign Confirm"); tail = then_out(asg_ok)
lib.compile_blueprint(w)
asg_no, h_no = assign(btns["Cancel"], "Events|AssignSignalClicked", "Assign Cancel"); connect(tail, exec_in(asg_no), "-> Assign Cancel"); tail = then_out(asg_no)
# cell handler: EditRank = Button.UserData; ModalEdit.SetText(CachedNames[EditRank]); modal visible
t = then_out(h_cell); bpin = out(h_cell, "Button")
gud = call(ed, "/Script/ConanSandbox.FLXButtonBase:GetUserDataAsInt", "GetUserDataAsInt"); connect(bpin, selfpin(gud), "button")
ser = ed.add_set_member_variable_node("EditRank"); connect(out(gud, "ReturnValue"), pin(ser, "EditRank"), "-> EditRank"); connect(t, exec_in(ser), "-> Set EditRank"); t = then_out(ser)
comp3 = ed.add_get_member_variable_node("Comp"); names3 = ed.add_get_member_variable_node("CachedNames", PL_C); connect(out(comp3), selfpin(names3), "comp"); er = ed.add_get_member_variable_node("EditRank")
s2t = call(ed, T + "Conv_StringToText", "current name"); connect(array_get(out(names3), out(er)), pin(s2t, "InString"), "CachedNames[EditRank]")
medit = ed.add_get_member_variable_node("ModalEdit"); st = call(ed, "/Script/ConanSandbox.FCEditableTextBase:SetText", "modal SetText"); connect(out(medit), selfpin(st), "edit"); connect(out(s2t, "ReturnValue"), first_param(st), "text"); connect(t, exec_in(st), "-> SetText"); t = then_out(st)
mroot = ed.add_get_member_variable_node("ModalRoot"); t = set_vis(out(mroot), "Visible", t, "modal")
# Confirm: name = ModalEdit.GetText; RPC; CachedNames[EditRank] = name; labels + head texts refreshed; modal hidden
t = then_out(h_ok); medit2 = ed.add_get_member_variable_node("ModalEdit"); gt = call(ed, "/Script/ConanSandbox.FCEditableTextBase:GetText", "modal GetText"); connect(out(medit2), selfpin(gt), "edit")
t2s = call(ed, T + "Conv_TextToString", "TextToString"); connect(out(gt, "ReturnValue"), pin(t2s, "InText"), "text"); nm = out(t2s, "ReturnValue")
comp4 = ed.add_get_member_variable_node("Comp"); er2 = ed.add_get_member_variable_node("EditRank")
i2b = call(ed, M + "Conv_IntToByte", "rank byte"); connect(out(er2), pin(i2b, "InInt"), "EditRank")
rpc = call(ed, f"{PL_C}:Server_ServerSetRankName_0", "ServerSetRankName"); connect(out(comp4), selfpin(rpc), "comp"); connect(out(i2b, "ReturnValue"), pin(rpc, "Rank"), "rank"); connect(nm, pin(rpc, "Name"), "name"); connect(t, exec_in(rpc), "-> RPC"); t = then_out(rpc)
names4 = ed.add_get_member_variable_node("CachedNames", PL_C); connect(out(comp4), selfpin(names4), "comp")
setel = create_by_search(ed, [out(names4)], ("Array", "SetArrayElem"), "Array Set", exact="Utilities|Array|SetArrayElem"); connect(out(names4), pin_exact_in(setel, "TargetArray"), "CachedNames"); connect(out(er2), pin_exact_in(setel, "Index"), "idx"); connect(nm, pin_exact_in(setel, "Item"), "name"); connect(t, exec_in(setel), "-> CachedNames[EditRank]"); t = then_out(setel)
s2t2 = call(ed, T + "Conv_StringToText", "new name text"); connect(nm, pin(s2t2, "InString"), "name")
cb2 = ed.add_get_member_variable_node("CellButtons"); ht2 = ed.add_get_member_variable_node("HeadTexts")
nt2 = ed.add_get_member_variable_node("NameTexts")
sl = call(ed, "/Script/UMG.TextBlock:SetText", "rename cell text"); connect(array_get(out(nt2), out(er2)), selfpin(sl), "text"); connect(out(s2t2, "ReturnValue"), pin(sl, "InText"), "text"); connect(t, exec_in(sl), "-> rename"); t = then_out(sl)
sh = call(ed, "/Script/UMG.TextBlock:SetText", "retitle head"); connect(array_get(out(ht2), out(er2)), selfpin(sh), "head"); connect(out(s2t2, "ReturnValue"), pin(sh, "InText"), "text"); connect(t, exec_in(sh), "-> retitle"); t = then_out(sh)
mroot2 = ed.add_get_member_variable_node("ModalRoot"); set_vis(out(mroot2), "Collapsed", t, "modal")
mroot3 = ed.add_get_member_variable_node("ModalRoot"); set_vis(out(mroot3), "Collapsed", then_out(h_no), "modal (cancel)")
# ---- ShowRanks / ShowPerms
for name, show_ranks in (("ShowRanks", True), ("ShowPerms", False)):
    evn = ed.add_custom_event_node(name); check(evn is not None, f"custom event {name}"); t = then_out(evn)
    rb_ = ed.add_get_member_variable_node("RanksBox"); ps_ = ed.add_get_member_variable_node("PermsScroll")
    t = set_vis(out(rb_), "Visible" if show_ranks else "Collapsed", t, "RanksBox"); set_vis(out(ps_), "Collapsed" if show_ranks else "Visible", t, "PermsScroll")
sec("compile")
compile_ok(w, [(ed, "EventGraph")], "W_GA_ClanRanks")
if MODE == "real" and not failures: save(w, os.path.join(DISK_LOCAL, "W_GA_ClanRanks.uasset"), "W_GA_ClanRanks")
elif MODE == "real": print("   NOT SAVING: failures above")
result()
