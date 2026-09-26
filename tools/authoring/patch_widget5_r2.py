"""One-off: round-2 fixes to author_v2_widget5.py (kept for review).
- slot alignment literals use the enum's real names (HAlign_*/VAlign_*): the short forms were silently ignored, so every
  cell fell back to Fill and stretched the badges / checkmarks / buttons
- alternate rows: a plain tinted image (the highlight material rendered nothing)
- Ranks header: 'Rank Name' left-aligned with a 12 px inset, matching the name buttons
- rename modal: the game's popup chrome (window background, top/bottom + left/right frames, blossom, flourishes),
  full-width text box, Confirm / Cancel stacked full width
- AddSubItem labels are handled in author_v2_ranknames.py
"""
import os, ast
here = os.path.dirname(os.path.abspath(__file__)); p = os.path.join(here, "author_v2_widget5.py"); s = open(p).read()
def rep(a, b, count=1):
    global s
    assert s.count(a) >= 1, a[:80]
    s = s.replace(a, b) if count == 0 else s.replace(a, b, count)
# --- enum literals everywhere
for short, full in (('"Fill"', '"HAlign_Fill"'), ('"Center"', '"HAlign_Center"'), ('"Left"', '"HAlign_Left"'), ('"Right"', '"HAlign_Right"')):
    pass
rep('''    h = call(ed, "/Script/UMG.HorizontalBoxSlot:SetHorizontalAlignment", "cell halign"); connect(sl, selfpin(h), "slot"); setval(h, "InHorizontalAlignment", halign); connect(tail, exec_in(h), "-> halign"); tail = then_out(h)
    v = call(ed, "/Script/UMG.HorizontalBoxSlot:SetVerticalAlignment", "cell valign"); connect(sl, selfpin(v), "slot"); setval(v, "InVerticalAlignment", "Center"); connect(tail, exec_in(v), "-> valign"); tail = then_out(v)''',
    '''    h = call(ed, "/Script/UMG.HorizontalBoxSlot:SetHorizontalAlignment", "cell halign"); connect(sl, selfpin(h), "slot"); setval(h, "InHorizontalAlignment", "HAlign_" + halign); connect(tail, exec_in(h), "-> halign"); tail = then_out(h)
    v = call(ed, "/Script/UMG.HorizontalBoxSlot:SetVerticalAlignment", "cell valign"); connect(sl, selfpin(v), "slot"); setval(v, "InVerticalAlignment", "VAlign_Center"); connect(tail, exec_in(v), "-> valign"); tail = then_out(v)''')
rep('''        for f_, v_ in (("SetHorizontalAlignment", "Fill"), ("SetVerticalAlignment", "Fill")):
            s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); PL.set_pin_value(first_param(s), v_); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
        p = call(ed, "/Script/UMG.OverlaySlot:SetPadding", "highlight pad")''',
    '''        for f_, v_ in (("SetHorizontalAlignment", "HAlign_Fill"), ("SetVerticalAlignment", "VAlign_Fill")):
            s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); check(PL.set_pin_value(first_param(s), v_), f"{f_} {v_}"); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
        p = call(ed, "/Script/UMG.OverlaySlot:SetPadding", "highlight pad")''')
rep('''    for f_, v_ in (("SetHorizontalAlignment", "Fill"), ("SetVerticalAlignment", "Fill")):
        s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); PL.set_pin_value(first_param(s), v_); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
    av = call(ed, "/Script/UMG.VerticalBox:AddChildToVerticalBox", "vbox <- row")''',
    '''    for f_, v_ in (("SetHorizontalAlignment", "HAlign_Fill"), ("SetVerticalAlignment", "VAlign_Fill")):
        s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); check(PL.set_pin_value(first_param(s), v_), f"{f_} {v_}"); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
    av = call(ed, "/Script/UMG.VerticalBox:AddChildToVerticalBox", "vbox <- row")''')
# --- alternate-row fill: plain tinted image
rep('''        hi, tail = construct("/Script/UMG.Image", f"highlight {label}", tail)
        bm = call(ed, "/Script/UMG.Image:SetBrushFromMaterial", "highlight material"); connect(hi, selfpin(bm), "img"); check(PL.set_pin_value(first_param(bm), HILITE), "highlight material literal"); connect(tail, exec_in(bm), "-> material"); tail = then_out(bm)''',
    '''        hi, tail = construct("/Script/UMG.Image", f"highlight {label}", tail)
        bm = call(ed, "/Script/UMG.Image:SetColorAndOpacity", "row fill"); connect(hi, selfpin(bm), "img"); check(PL.set_pin_value(first_param(bm), ROWFILL), "row fill literal"); connect(tail, exec_in(bm), "-> fill"); tail = then_out(bm)''')
rep('''HILITE = "/Game/UI/Materials/General/M_UI_FLX_InputHighlight.M_UI_FLX_InputHighlight"''',
    '''ROWFILL = "(R=0.000000,G=0.000000,B=0.000000,A=0.450000)"   # the roster's row bar, as a flat tint
WIN_BG = "(ImageSize=(X=512.000000,Y=512.000000),Margin=(Left=0.050000,Top=0.050000,Right=0.050000,Bottom=0.050000),ResourceObject=/Script/Engine.Texture2D'/Game/UI/Textures/Backgrounds/T_UI_GeneralWindow_Background.T_UI_GeneralWindow_Background',Tiling=Both,ImageType=FullColor)"
FRAME_H = "(ImageSize=(X=512.000000,Y=32.000000),Margin=(Top=0.250000,Bottom=0.250000),ResourceObject=/Script/Engine.Texture2D'/Game/UI/Textures/Backgrounds/T_UI_Panel_Frame_TopBottom.T_UI_Panel_Frame_TopBottom',DrawAs=Box,ImageType=FullColor)"
FRAME_V = "(ImageSize=(X=32.000000,Y=512.000000),Margin=(Left=0.250000,Right=0.250000),ResourceObject=/Script/Engine.Texture2D'/Game/UI/Textures/Backgrounds/T_UI_Panel_Frame_LeftRight.T_UI_Panel_Frame_LeftRight',DrawAs=Box,ImageType=FullColor)"
BLOSSOM = "(ResourceObject=/Script/Engine.Material'/Game/UI/Materials/General/M_UI_Blossom_Blank.M_UI_Blossom_Blank',ImageType=FullColor)"
FLOURISH = "(ImageSize=(X=64.000000,Y=128.000000),Margin=(Left=0.250000,Top=0.250000,Right=0.250000,Bottom=0.250000),ResourceObject=/Script/Engine.Texture2D'/Game/UI/Textures/Backgrounds/T_UI_Panel_Frame_Flourishes.T_UI_Panel_Frame_Flourishes',DrawAs=Box,ImageType=FullColor)"''')
# --- Ranks header inset + name column alignment
rep('''for txt, ratio, hal in (("Badge", 0.1, "Center"), ("Rank Name", 0.6, "Left"), ("Ranking", 0.3, "Center")):
    tp, tail = styled_text(ST_HEAD, TINT, f"ranks head {txt}", tail, literal=txt, justify="Center" if hal == "Center" else None); tail = hcell(hb, tp, ratio, hal, tail)''',
    '''for txt, ratio, hal in (("Badge", 0.1, "Center"), ("Rank Name", 0.6, "Left"), ("Ranking", 0.3, "Center")):
    tp, tail = styled_text(ST_HEAD, TINT, f"ranks head {txt}", tail, literal=txt, justify="Center" if hal == "Center" else None)
    tail = hcell(hb, tp, ratio, hal, tail, pad="(Left=12.000000,Top=0.000000,Right=0.000000,Bottom=0.000000)" if txt == "Rank Name" else None)''')
# --- modal chrome
rep('''box, tail = construct("/Script/UMG.SizeBox", "modal box", tail)
wo = call(ed, "/Script/UMG.SizeBox:SetWidthOverride", "modal width"); connect(box, selfpin(wo), "box"); PL.set_pin_value(first_param(wo), "560.0"); connect(tail, exec_in(wo), "-> width"); tail = then_out(wo)''',
    '''box, tail = construct("/Script/UMG.SizeBox", "modal box", tail)
wo = call(ed, "/Script/UMG.SizeBox:SetWidthOverride", "modal width"); connect(box, selfpin(wo), "box"); PL.set_pin_value(first_param(wo), "760.0"); connect(tail, exec_in(wo), "-> width"); tail = then_out(wo)''')
rep('''for f_, v_ in (("SetHorizontalAlignment", "Center"), ("SetVerticalAlignment", "Center")):
    s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); PL.set_pin_value(first_param(s), v_); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
inner, tail = construct("/Script/UMG.Overlay", "modal inner", tail)
sc2 = call(ed, "/Script/UMG.PanelWidget:AddChild", "box <- inner"); connect(box, selfpin(sc2), "box"); connect(inner, pin(sc2, "Content"), "inner"); connect(tail, exec_in(sc2), "-> add"); tail = then_out(sc2)
bgi, tail = image(BG, 560, 320, "modal background", tail)
ao = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", "inner <- bg"); connect(inner, selfpin(ao), "inner"); connect(bgi, pin(ao, "Content"), "bg"); connect(tail, exec_in(ao), "-> add"); tail = then_out(ao)
for f_, v_ in (("SetHorizontalAlignment", "Fill"), ("SetVerticalAlignment", "Fill")):
    s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); PL.set_pin_value(first_param(s), v_); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
mv, tail = construct("/Script/UMG.VerticalBox", "modal vbox", tail)
ao = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", "inner <- vbox"); connect(inner, selfpin(ao), "inner"); connect(mv, pin(ao, "Content"), "vbox"); connect(tail, exec_in(ao), "-> add"); tail = then_out(ao)
for f_, v_ in (("SetHorizontalAlignment", "Fill"), ("SetVerticalAlignment", "Center")):
    s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); PL.set_pin_value(first_param(s), v_); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
p = call(ed, "/Script/UMG.OverlaySlot:SetPadding", "modal pad"); connect(out(ao, "ReturnValue"), selfpin(p), "slot"); PL.set_pin_value(first_param(p), "(Left=36.000000,Top=32.000000,Right=36.000000,Bottom=32.000000)"); connect(tail, exec_in(p), "-> pad"); tail = then_out(p)''',
    '''for f_, v_ in (("SetHorizontalAlignment", "HAlign_Center"), ("SetVerticalAlignment", "VAlign_Center")):
    s = call(ed, f"/Script/UMG.OverlaySlot:{f_}", f_); connect(out(ao, "ReturnValue"), selfpin(s), "slot"); check(PL.set_pin_value(first_param(s), v_), v_); connect(tail, exec_in(s), f"-> {f_}"); tail = then_out(s)
inner, tail = construct("/Script/UMG.Overlay", "modal inner", tail)
sc2 = call(ed, "/Script/UMG.PanelWidget:AddChild", "box <- inner"); connect(box, selfpin(sc2), "box"); connect(inner, pin(sc2, "Content"), "inner"); connect(tail, exec_in(sc2), "-> add"); tail = then_out(sc2)
def layer(kind, brush, label, tail, pad, valign="VAlign_Fill", halign="HAlign_Fill"):
    """a Border or Image layer of the popup chrome, brush from the vanilla popup, added to the inner overlay"""
    wp, tail = construct(f"/Script/UMG.{kind}", label, tail)
    sb = call(ed, f"/Script/UMG.{kind}:SetBrush", f"brush({label})"); connect(wp, selfpin(sb), label); check(PL.set_pin_value(first_param(sb), brush), f"{label}: brush literal"); connect(tail, exec_in(sb), "-> brush"); tail = then_out(sb)
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
p = call(ed, "/Script/UMG.OverlaySlot:SetPadding", "modal pad"); connect(out(ao, "ReturnValue"), selfpin(p), "slot"); PL.set_pin_value(first_param(p), "(Left=36.000000,Top=32.000000,Right=36.000000,Bottom=32.000000)"); connect(tail, exec_in(p), "-> pad"); tail = then_out(p)''')
rep('''        h_ = call(ed, "/Script/UMG.VerticalBoxSlot:SetHorizontalAlignment", "halign"); connect(out(a, "ReturnValue"), selfpin(h_), "slot"); PL.set_pin_value(first_param(h_), halign); connect(tail, exec_in(h_), "-> halign"); tail = then_out(h_)''',
    '''        h_ = call(ed, "/Script/UMG.VerticalBoxSlot:SetHorizontalAlignment", "halign"); connect(out(a, "ReturnValue"), selfpin(h_), "slot"); check(PL.set_pin_value(first_param(h_), "HAlign_" + halign), halign); connect(tail, exec_in(h_), "-> halign"); tail = then_out(h_)''')
# --- Confirm / Cancel stacked full width (like Yes / No on the leave popup)
rep('''bh, tail = construct("/Script/UMG.HorizontalBox", "modal buttons", tail); tail = vadd(mv, bh, tail, halign="Center")
btns = {}
for lbl in ("Confirm", "Cancel"):
    bp_, tail = create_widget(BTN_C, f"modal {lbl}", tail)
    sl = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetLabel", f"SetLabel({lbl})"); connect(bp_, selfpin(sl), "btn"); lt = call(ed, T + "Conv_StringToText", f"{lbl} text"); setval(lt, "InString", lbl); connect(out(lt, "ReturnValue"), pin(sl, "NewLabel"), "text"); connect(tail, exec_in(sl), "-> label"); tail = then_out(sl)
    tail = hcell(bh, bp_, 1.0, "Center", tail, pad="(Left=8.000000,Top=4.000000,Right=8.000000,Bottom=4.000000)"); tail = setup_child(bp_, tail, f"modal {lbl}"); btns[lbl] = bp_''',
    '''btns = {}
for lbl in ("Confirm", "Cancel"):
    bp_, tail = create_widget(BTN_C, f"modal {lbl}", tail)
    sl = call(ed, "/Script/ConanSandbox.FLXButtonBase:SetLabel", f"SetLabel({lbl})"); connect(bp_, selfpin(sl), "btn"); lt = call(ed, T + "Conv_StringToText", f"{lbl} text"); setval(lt, "InString", lbl); connect(out(lt, "ReturnValue"), pin(sl, "NewLabel"), "text"); connect(tail, exec_in(sl), "-> label"); tail = then_out(sl)
    tail = vadd(mv, bp_, tail, pad="(Left=0.000000,Top=4.000000,Right=0.000000,Bottom=4.000000)", halign="Fill"); tail = setup_child(bp_, tail, f"modal {lbl}"); btns[lbl] = bp_''')
ast.parse(s); open(p, "w").write(s); print("author_v2_widget5.py patched (round 2)")
