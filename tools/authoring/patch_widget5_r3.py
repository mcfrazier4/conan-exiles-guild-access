"""One-off: round-3 refinements to author_v2_widget5.py.
- icons live in a fixed SizeBox (badge 16x23, checkmark 16x16, pencil 16x16): exact roster size, never stretched
- uniform 40 px rows; the alternate-row tint at roughly half strength
- name cell = pencil image + Body_4 text (mixed case) with a transparent clear-styled button laid over it for the click
- Permissions header: badge only, centred (name texts kept but collapsed so renames still refresh them)
"""
import os, ast
here = os.path.dirname(os.path.abspath(__file__)); p = os.path.join(here, "author_v2_widget5.py"); s = open(p).read()
def rep(a, b):
    global s
    assert a in s, a[:80]
    s = s.replace(a, b)
rep('''ROWFILL = "(R=0.000000,G=0.000000,B=0.000000,A=0.450000)"''', '''ROWFILL = "(R=0.000000,G=0.000000,B=0.000000,A=0.220000)"''')
# --- fixed-size icon box
rep('''def image(texture, w_, h_, label, tail, tint=None):
    ip, tail = construct("/Script/UMG.Image", label, tail)
    sb = call(ed, "/Script/UMG.Image:SetBrushFromTexture", f"SetBrush({label})"); connect(ip, selfpin(sb), "img"); check(PL.set_pin_value(pin(sb, "Texture"), texture), f"{label}: texture"); PL.set_pin_value(next((q for q in lib.list_input_pins(sb) if "Match" in str(PL.get_pin_name(q))), None), "false"); connect(tail, exec_in(sb), "-> brush"); tail = then_out(sb)
    ds = call(ed, "/Script/UMG.Image:SetDesiredSizeOverride", f"size({label})"); connect(ip, selfpin(ds), "img"); check(PL.set_pin_value(first_param(ds), f"(X={w_:.6f},Y={h_:.6f})"), f"{label}: size"); connect(tail, exec_in(ds), "-> size"); tail = then_out(ds)
    if tint:
        co = call(ed, "/Script/UMG.Image:SetColorAndOpacity", f"tint({label})"); connect(ip, selfpin(co), "img"); check(PL.set_pin_value(first_param(co), tint), f"{label}: tint"); connect(tail, exec_in(co), "-> tint"); tail = then_out(co)
    return ip, tail''',
'''def image(texture, w_, h_, label, tail, tint=None):
    """SizeBox(w x h)[Image(texture)] - the box pins the size, the image fills it. Returns (box pin, tail)."""
    ip, tail = construct("/Script/UMG.Image", label, tail)
    sb = call(ed, "/Script/UMG.Image:SetBrushFromTexture", f"SetBrush({label})"); connect(ip, selfpin(sb), "img"); check(PL.set_pin_value(pin(sb, "Texture"), texture), f"{label}: texture"); PL.set_pin_value(next((q for q in lib.list_input_pins(sb) if "Match" in str(PL.get_pin_name(q))), None), "false"); connect(tail, exec_in(sb), "-> brush"); tail = then_out(sb)
    if tint:
        co = call(ed, "/Script/UMG.Image:SetColorAndOpacity", f"tint({label})"); connect(ip, selfpin(co), "img"); check(PL.set_pin_value(first_param(co), tint), f"{label}: tint"); connect(tail, exec_in(co), "-> tint"); tail = then_out(co)
    bx, tail = construct("/Script/UMG.SizeBox", f"{label} box", tail)
    for f_, v_ in (("SetWidthOverride", w_), ("SetHeightOverride", h_)):
        n_ = call(ed, f"/Script/UMG.SizeBox:{f_}", f"{label} {f_}"); connect(bx, selfpin(n_), "box"); PL.set_pin_value(first_param(n_), f"{v_:.1f}"); connect(tail, exec_in(n_), f"-> {f_}"); tail = then_out(n_)
    a = call(ed, "/Script/UMG.PanelWidget:AddChild", f"{label} box <- image"); connect(bx, selfpin(a), "box"); connect(ip, pin(a, "Content"), "img"); connect(tail, exec_in(a), "-> add"); tail = then_out(a)
    return bx, tail''')
# --- uniform rows
rep('''        ho = call(ed, "/Script/UMG.SizeBox:SetHeightOverride", "row height"); connect(sz, selfpin(ho), "sizebox"); PL.set_pin_value(first_param(ho), "44.0"); connect(tail, exec_in(ho), "-> height"); tail = then_out(ho)''',
    '''        ho = call(ed, "/Script/UMG.SizeBox:SetHeightOverride", "row height"); connect(sz, selfpin(ho), "sizebox"); PL.set_pin_value(first_param(ho), "40.0"); connect(tail, exec_in(ho), "-> height"); tail = then_out(ho)''')
rep('''        p = call(ed, "/Script/UMG.OverlaySlot:SetPadding", "highlight pad"); connect(out(ao, "ReturnValue"), selfpin(p), "slot"); PL.set_pin_value(first_param(p), "(Left=0.000000,Top=5.000000,Right=0.000000,Bottom=5.000000)"); connect(tail, exec_in(p), "-> pad"); tail = then_out(p)''',
    '''        p = call(ed, "/Script/UMG.OverlaySlot:SetPadding", "highlight pad"); connect(out(ao, "ReturnValue"), selfpin(p), "slot"); PL.set_pin_value(first_param(p), "(Left=0.000000,Top=3.000000,Right=0.000000,Bottom=3.000000)"); connect(tail, exec_in(p), "-> pad"); tail = then_out(p)''')
# --- name cell: pencil + mixed-case text + transparent click button
rep('''cell_pins = {}
for r in range(4):   # created in rank order so CellButtons[rank] holds the cell
    bp_, tail = create_widget(CELL_C, f"cell {r}", tail)
    si = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetIcon", f"pencil {r}"); connect(bp_, selfpin(si), "btn"); check(PL.set_pin_value(first_param(si), PENCIL), "pencil literal"); connect(tail, exec_in(si), "-> icon"); tail = then_out(si)
    siv = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetIconVisibility", f"pencil vis {r}"); connect(bp_, selfpin(siv), "btn"); PL.set_pin_value(first_param(siv), "Visible"); connect(tail, exec_in(siv), "-> icon vis"); tail = then_out(siv)
    sl = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetLabel", f"label {r}"); connect(bp_, selfpin(sl), "btn"); connect(name_text(r), pin(sl, "NewLabel"), "name"); connect(tail, exec_in(sl), "-> label"); tail = then_out(sl)
    ud = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetUserDataAsInt", f"userdata {r}"); connect(bp_, selfpin(ud), "btn"); PL.set_pin_value(first_param(ud), str(r)); connect(tail, exec_in(ud), "-> userdata"); tail = then_out(ud)
    en = call(ed, "/Script/UMG.Widget:SetIsEnabled", f"enable cell {r}"); connect(bp_, selfpin(en), "btn"); connect(out(is_gm, "ReturnValue"), pin(en, "bInIsEnabled"), "GM?"); connect(tail, exec_in(en), "-> enable"); tail = then_out(en)
    tail = array_add(out(cellbtns), bp_, tail); cell_pins[r] = bp_''',
'''cell_pins = {}; cell_widgets = {}
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
    tail = array_add(out(cellbtns), bp_, tail); cell_pins[r] = bp_; cell_widgets[r] = ov''')
rep('''    tail = hcell(hb, cell_pins[r], 0.6, "Left", tail); tail = setup_child(cell_pins[r], tail, f"cell {r}")''',
    '''    tail = hcell(hb, cell_widgets[r], 0.6, "Fill", tail); tail = setup_child(cell_pins[r], tail, f"cell {r}")''')
# Confirm: refresh the text instead of a button label
rep('''sl = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetLabel", "relabel cell"); connect(array_get(out(cb2), out(er2)), selfpin(sl), "cell"); connect(out(s2t2, "ReturnValue"), pin(sl, "NewLabel"), "text"); connect(t, exec_in(sl), "-> relabel"); t = then_out(sl)''',
    '''nt2 = ed.add_get_member_variable_node("NameTexts")
sl = call(ed, "/Script/UMG.TextBlock:SetText", "rename cell text"); connect(array_get(out(nt2), out(er2)), selfpin(sl), "text"); connect(out(s2t2, "ReturnValue"), pin(sl, "InText"), "text"); connect(t, exec_in(sl), "-> rename"); t = then_out(sl)''')
# --- Permissions header: badge only, centred
rep('''    ip, tail = image(BADGES[r], 16, 23, f"head badge {r}", tail); tail = hcell(cellbox, ip, 0.2, "Right", tail)
    tp, tail = styled_text(ST_HEAD, TINT, f"perm head name {r}", tail, text_pin=name_text(r)); tail = hcell(cellbox, tp, 0.8, "Left", tail, pad="(Left=6.000000,Top=0.000000,Right=0.000000,Bottom=0.000000)")
    tail = array_add(out(headtexts), tp, tail); head_cells[r] = cellbox''',
    '''    ip, tail = image(BADGES[r], 16, 23, f"head badge {r}", tail); tail = hcell(cellbox, ip, 1.0, "Center", tail)
    tp, tail = styled_text(ST_HEAD, TINT, f"perm head name {r}", tail, text_pin=name_text(r)); tail = hcell(cellbox, tp, 0.0, "Left", tail); tail = set_vis(tp, "Collapsed", tail, f"perm head name {r}")
    tail = array_add(out(headtexts), tp, tail); head_cells[r] = cellbox''')
rep('''for r in COLS: tail = hcell(hb, head_cells[r], 0.165, "Fill", tail)''', '''for r in COLS: tail = hcell(hb, head_cells[r], 0.165, "Center", tail)''')
# checkmarks 16 px
rep('''ip, tail = image(CHECK, 23, 23, f"check {i}/{r}", tail, tint=LIN)''', '''ip, tail = image(CHECK, 16, 16, f"check {i}/{r}", tail, tint=LIN)''')
ast.parse(s); open(p, "w").write(s); print("author_v2_widget5.py patched (round 3)")
