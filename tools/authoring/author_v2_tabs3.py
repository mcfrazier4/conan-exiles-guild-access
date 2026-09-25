"""v2 - Roster / Ranks / Permissions tabs on the clan window (third version: panel v5, no Save on close). Run WITH -ModDevKit. GA_MODE=dry|real. GA_TARGET=player|guildview.
Order: author_v2_tabbutton.py, author_v2_widget4.py, then player, then guildview.

player   : BPC_GA_Player: var RanksPanel (W_GA_ClanRanks_C). ClientClanTable handler, after CreateWidget:
           panel.Host = RanksHost; if RanksHost valid -> the roster's grandparent VerticalBox .AddChild(panel) (slot Fill),
           RanksHost.SetupNewChild(panel), RanksPanel = panel, RanksHost = null; else -> old AddToViewport path.
guildview: W_GuildView override: the 'Ranks' button wiring is stripped. Event Construct (once per instance) hides the
           'Clan Roster' heading, adds a HorizontalBox with two W_GA_TabButton tabs ('Roster' on) into the heading overlay,
           registers them, binds their clicks and the window's SignalClosing.
           Roster click : roster + Show Offline visible, panel collapsed, tabs toggled
           Ranks click  : roster + Show Offline collapsed, tabs toggled; panel visible if it exists, else request the table
           Closing      : if a panel exists -> panel.SaveNow, RemoveFromParent, RanksPanel = null; roster state restored
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ga_helpers import *
TARGET = os.environ.get("GA_TARGET", "player").lower()
PL_PATH = f"{LOCAL}/BPC_GA_Player"; PL_C = f"{PL_PATH}.BPC_GA_Player_C"; W_C = f"{LOCAL}/W_GA_ClanRanks.W_GA_ClanRanks_C"; TAB_C = f"{LOCAL}/W_GA_TabButton.W_GA_TabButton_C"
GV_PATH = "/Game/UI/Widgets/Guild/W_GuildView"; GV_DISK = os.path.join(DISK_CONTENT, r"UI\Widgets\Guild\W_GuildView.uasset")
GVB = "/Script/ConanSandbox.GuildViewBase"; FLX = "/Script/ConanSandbox.FLXButtonBase"
sec(f"mode = {MODE} target = {TARGET}")
wait_registry()
def out(n, name=None):
    if n is None: return None
    if name: return lib.find_output_pin(n, name)
    o = lib.list_output_pins(n); return o[0] if o else None
def selfpin(n): return lib.find_self_pin(n) or pin_exact_in(n, "self")
def first_param(n): return next((p for p in lib.list_input_pins(n) if str(PL.get_pin_name(p)) not in ("self", "execute")), None)
def is_pure(n): return exec_in(n) is None and n.get_class().get_name() not in ("K2Node_Event", "K2Node_CustomEvent", "K2Node_ComponentBoundEvent")
def walk_exec(start_pin, stop_titles=()):
    """nodes reachable by exec links from start_pin (not crossing nodes whose title is in stop_titles), plus pure feeders"""
    seen = {}; frontier = [PL.get_owning_node(c) for c in PL.list_connected_pins(start_pin)]
    while frontier:
        n = frontier.pop()
        if n.get_name() in seen or title(n).replace(" ", "") in stop_titles: continue
        seen[n.get_name()] = n
        for p in lib.list_output_pins(n):
            for c in PL.list_connected_pins(p):
                m = PL.get_owning_node(c)
                if exec_in(m) is not None and PL.get_pin_name(c) and str(PL.get_pin_name(c)) == "execute": frontier.append(m)
    # pure feeders of the collected nodes (only those that feed nothing outside the set)
    changed = True
    while changed:
        changed = False
        for n in list(seen.values()):
            for p in lib.list_input_pins(n):
                for c in PL.list_connected_pins(p):
                    m = PL.get_owning_node(c)
                    if m.get_name() in seen or not is_pure(m): continue
                    consumers = {PL.get_owning_node(cc).get_name() for q in lib.list_output_pins(m) for cc in PL.list_connected_pins(q)}
                    if consumers <= set(seen.keys()): seen[m.get_name()] = m; changed = True
    return list(seen.values())
def set_vis(ed, widget_pin, vis, tail, label):
    v = call(ed, "/Script/UMG.Widget:SetVisibility", f"SetVisibility({label})"); connect(widget_pin, selfpin(v), label); setval(v, "InVisibility", vis); connect(tail, exec_in(v), f"-> {label} {vis}"); return then_out(v)
def assign(ed, obj_pin, exact, label):
    before = snapshot(ed)
    asg = create_by_search(ed, [obj_pin] if obj_pin is not None else [], tuple(exact.split("|")[-1:]), label, exact=exact)
    h = [n for n in new_nodes(ed, before) if n.get_class().get_name() == "K2Node_CustomEvent"]; check(len(h) == 1, f"{label}: handler"); h = h[0] if h else None
    sp = selfpin(asg)
    if obj_pin is not None and sp is not None and not list(PL.list_connected_pins(sp)): connect(obj_pin, sp, f"{label}: self")
    return asg, h

if TARGET == "player":
    pl = unreal.load_asset(PL_PATH); ed = GE.get_graph_editor_by_name(pl, "EventGraph")
    for nm, t in (("RanksHost", lib.get_object_reference_type(unreal.GuildViewBase)), ("RanksPanel", lib.get_object_reference_type(unreal.load_class(None, W_C))), ("PendingMode", lib.get_basic_type_by_name("int"))):
        if nm not in [str(v) for v in lib.list_member_variable_names(pl)]: check(lib.add_member_variable(pl, nm, t), f"var {nm}")
    lib.compile_blueprint(pl)
    cw = [n for n in ed.list_all_nodes() if "CreateWidget" in n.get_class().get_name()]; check(len(cw) == 1, "the CreateWidget node"); cw = cw[0]
    panel = out(cw, "ReturnValue")
    # strip everything after CreateWidget except the AddToViewport fallback chain
    victims = walk_exec(then_out(cw)); print("   stripping (incl. the viewport fallback):", sorted(set(title(n) for n in victims)))
    ed.remove_nodes(victims); PL.break_pin_links(then_out(cw))
    host = ed.add_get_member_variable_node("RanksHost")
    sh = ed.add_set_member_variable_node("Host", W_C); check(sh is not None, "Set Host (panel)"); connect(panel, selfpin(sh), "panel"); connect(out(host), pin_exact_in(sh, "Host"), "RanksHost -> Host"); connect(then_out(cw), exec_in(sh), "CreateWidget -> Set Host")
    iv = call(ed, "/Script/Engine.KismetSystemLibrary:IsValid", "IsValid(RanksHost)"); connect(out(host), pin_exact_in(iv, "Object"), "host")
    br = ed.add_branch_node(); connect(out(iv, "ReturnValue"), lib.find_condition_pin(br), "valid?"); connect(then_out(sh), exec_in(br), "-> Branch")
    gl = ed.add_get_member_variable_node("GuildMembersList", GVB); connect(out(host), selfpin(gl), "host -> roster")
    gp1 = call(ed, "/Script/UMG.Widget:GetParent", "GetParent(roster)"); connect(out(gl), selfpin(gp1), "roster")
    gp2 = call(ed, "/Script/UMG.Widget:GetParent", "GetParent(SizeBox)"); connect(out(gp1, "ReturnValue"), selfpin(gp2), "size box")
    ac = call(ed, "/Script/UMG.PanelWidget:AddChild", "AddChild(panel)"); connect(out(gp2, "ReturnValue"), selfpin(ac), "VerticalBox"); connect(panel, pin_exact_in(ac, "Content"), "panel"); connect(then_out(br), exec_in(ac), "valid -> AddChild"); t = then_out(ac)
    cast = create_by_search(ed, [out(ac, "ReturnValue")], ("Casting", "CastToVerticalBoxSlot"), "Cast To VerticalBoxSlot", exact="Utilities|Casting|CastToVerticalBoxSlot"); connect(out(ac, "ReturnValue"), pin_exact_in(cast, "Object"), "slot -> cast"); connect(t, exec_in(cast), "-> cast"); t = then_out(cast)
    ss = call(ed, "/Script/UMG.VerticalBoxSlot:SetSize", "SetSize(Fill)"); connect(as_pin(cast), selfpin(ss), "slot"); check(PL.set_pin_value(first_param(ss), "(Value=1.000000,SizeRule=Fill)"), "slot size literal"); connect(t, exec_in(ss), "-> SetSize"); t = then_out(ss)
    sn = call(ed, "/Script/ConanSandbox.RootWidget:SetupNewChild", "SetupNewChild(panel)"); connect(out(host), selfpin(sn), "host"); connect(panel, pin_exact_in(sn, "child"), "panel"); connect(t, exec_in(sn), "-> SetupNewChild"); t = then_out(sn)
    sp_ = ed.add_set_member_variable_node("RanksPanel"); connect(panel, pin_exact_in(sp_, "RanksPanel"), "panel -> RanksPanel"); connect(t, exec_in(sp_), "-> RanksPanel"); t = then_out(sp_)
    clr = ed.add_set_member_variable_node("RanksHost"); connect(t, exec_in(clr), "-> RanksHost = null"); t = then_out(clr)
    pm = ed.add_get_member_variable_node("PendingMode"); eq = call(ed, "/Script/Engine.KismetMathLibrary:EqualEqual_IntInt", "PendingMode==1"); connect(out(pm), pin_exact_in(eq, "A"), "mode"); setval(eq, "B", "1")
    b2 = ed.add_branch_node(); connect(out(eq, "ReturnValue"), lib.find_condition_pin(b2), "perms?"); connect(t, exec_in(b2), "-> mode?")
    sr = call(ed, f"{W_C}:ShowRanks", "panel.ShowRanks"); connect(panel, selfpin(sr), "panel"); connect(lib.find_else_pin(b2), exec_in(sr), "ranks")
    sp2 = call(ed, f"{W_C}:ShowPerms", "panel.ShowPerms"); connect(panel, selfpin(sp2), "panel"); connect(then_out(b2), exec_in(sp2), "perms")
    # clients ask for the table shortly after BeginPlay so radial labels and the panel have the clan's names
    bpn = [n for n in ed.list_all_nodes() if title(n) == "Event Begin Play"]; check(len(bpn) == 1, "Event BeginPlay"); bpn = bpn[0]
    if not list(PL.list_connected_pins(then_out(bpn))):
        own = call(ed, "/Script/Engine.ActorComponent:GetOwner", "GetOwner (BeginPlay)"); ha = call(ed, "/Script/Engine.Actor:HasAuthority", "HasAuthority"); connect(out(own, "ReturnValue"), selfpin(ha), "owner")
        b3 = ed.add_branch_node(); connect(out(ha, "ReturnValue"), lib.find_condition_pin(b3), "authority?"); connect(then_out(bpn), exec_in(b3), "BeginPlay -> authority?")
        dl = create_by_search(ed, [], ("FlowControl", "Delay"), "Delay", exact="Utilities|FlowControl|Delay"); setval(dl, "Duration", "3.0"); connect(lib.find_else_pin(b3), exec_in(dl), "client -> Delay")
        rq = call(ed, f"{PL_C}:Server_ServerRequestClanTable", "request table (BeginPlay)"); connect(then_out(dl), exec_in(rq), "-> request")
    else: print("   BeginPlay already wired")
    compile_ok(pl, [(ed, "EventGraph")], "BPC_GA_Player")
    if MODE == "real" and not failures: save(pl, os.path.join(DISK_LOCAL, "BPC_GA_Player.uasset"), "BPC_GA_Player")
    elif MODE == "real": print("   NOT SAVING: failures above")
else:
    gv = unreal.load_asset(GV_PATH); check(gv is not None, "loaded W_GuildView"); ed = GE.get_graph_editor_by_name(gv, "EventGraph")
    # --- strip the 'Ranks' button wiring (switch pin 2 chain) and any earlier tab build
    sw = [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_SwitchInteger"]; check(len(sw) == 1, "Switch on Int"); sw = sw[0]
    p2 = pin_exact_out(sw, "2")
    if p2 is not None and list(PL.list_connected_pins(p2)):
        victims = walk_exec(p2); print("   stripping switch-2 chain:", sorted(set(title(n) for n in victims))); ed.remove_nodes(victims)
    # the vanilla Construct chain (Set KeyNavChildren ...) must survive: our build hangs off a Sequence's then_1
    old = [n for n in ed.list_all_nodes() if title(n) in ("Event Construct",)]
    seq = None
    if old:
        nxt = [PL.get_owning_node(c) for c in PL.list_connected_pins(then_out(old[0]))]
        if nxt and nxt[0].get_class().get_name() == "K2Node_ExecutionSequence" and "Set TabsBuilt" in [title(n) for n in walk_exec(pin_exact_out(nxt[0], "then_1"))]:
            seq = nxt[0]; victims = walk_exec(pin_exact_out(seq, "then_1")); print("   stripping our old tab build:", sorted(set(title(n) for n in victims))); ed.remove_nodes(victims)
    for n in [n for n in ed.list_all_nodes() if n.get_class().get_name() == "K2Node_CustomEvent" and title(n).replace(" ", "").startswith("Signal")]:
        victims = walk_exec(then_out(n)); ed.remove_nodes(victims + [n])
    lib.compile_blueprint(gv)
    for nm, t in (("TabsBuilt", lib.get_basic_type_by_name("bool")), ("TabRoster", lib.get_object_reference_type(unreal.FLXButtonBase)), ("TabRanks", lib.get_object_reference_type(unreal.FLXButtonBase)), ("TabPerms", lib.get_object_reference_type(unreal.FLXButtonBase)), ("Comp", lib.get_object_reference_type(unreal.load_class(None, PL_C)))):
        if nm not in [str(v) for v in lib.list_member_variable_names(gv)]: check(lib.add_member_variable(gv, nm, t), f"var {nm}")
    lib.compile_blueprint(gv)
    ev = old[0] if old else lib.add_event_override(gv, "Construct", unreal.IntPoint(0, 0)); check(ev is not None, "Event Construct")
    if seq is None:
        vanilla = list(PL.list_connected_pins(then_out(ev)))
        seq = create_by_search(ed, [], ("FlowControl", "Sequence"), "Sequence", exact="Utilities|FlowControl|Sequence")
        PL.break_pin_links(then_out(ev)); connect(then_out(ev), exec_in(seq), "Construct -> Sequence")
        if vanilla: connect(pin_exact_out(seq, "then_0"), vanilla[0], "then_0 -> vanilla Construct chain")
    built = ed.add_get_member_variable_node("TabsBuilt"); br = ed.add_branch_node(); connect(out(built), lib.find_condition_pin(br), "TabsBuilt"); connect(pin_exact_out(seq, "then_1"), exec_in(br), "then_1 -> built?"); tail = lib.find_else_pin(br)
    gop = create_by_search(ed, [], ("GetOwningPlayer",), "GetOwningPlayer", prefer=["|GetOwningPlayer"]); pc = out(gop, "ReturnValue")
    gcb = call(ed, "/Script/Engine.Actor:GetComponentByClass", "GetComponentByClass(Player)"); connect(pc, pin_exact_in(gcb, "self"), "PC -> gcb"); setval(gcb, "ComponentClass", PL_C)
    sc = ed.add_set_member_variable_node("Comp"); connect(out(gcb, "ReturnValue"), pin_exact_in(sc, "Comp"), "-> Comp"); connect(tail, exec_in(sc), "-> Set Comp"); tail = then_out(sc)
    me = create_by_search(ed, [], ("Getareferencetoself",), "self", exact="Variables|Getareferencetoself")
    # heading overlay = roster.GetParent().GetParent().GetChildAt(1); its child 0 is the 'Clan Roster' text
    gl = ed.add_get_member_variable_node("GuildMembersList"); gp1 = call(ed, "/Script/UMG.Widget:GetParent", "GetParent(roster)"); connect(out(gl), selfpin(gp1), "roster")
    gp2 = call(ed, "/Script/UMG.Widget:GetParent", "GetParent(SizeBox)"); connect(out(gp1, "ReturnValue"), selfpin(gp2), "size box")
    ca1 = call(ed, "/Script/UMG.PanelWidget:GetChildAt", "GetChildAt(1) heading overlay"); connect(out(gp2, "ReturnValue"), selfpin(ca1), "VerticalBox"); setval(ca1, "Index", "1")
    cast_o = create_by_search(ed, [out(ca1, "ReturnValue")], ("Casting", "CastToOverlay"), "Cast To Overlay", exact="Utilities|Casting|CastToOverlay"); connect(out(ca1, "ReturnValue"), pin_exact_in(cast_o, "Object"), "-> cast"); connect(tail, exec_in(cast_o), "-> cast overlay"); tail = then_out(cast_o)
    ca0 = call(ed, "/Script/UMG.PanelWidget:GetChildAt", "GetChildAt(0) 'Clan Roster' text"); connect(as_pin(cast_o), selfpin(ca0), "overlay"); setval(ca0, "Index", "0")
    tail = set_vis(ed, out(ca0, "ReturnValue"), "Collapsed", tail, "'Clan Roster' text")
    hb = create_by_search(ed, [], ("ConstructObjectfromClass",), "Construct HorizontalBox", exact="Game|ConstructObjectfromClass"); check(PL.set_pin_value(pin_exact_in(hb, "Class"), "/Script/UMG.HorizontalBox"), "HorizontalBox class"); connect(tail, exec_in(hb), "-> HorizontalBox"); tail = then_out(hb); hbp = out(hb, "ReturnValue")
    ao = call(ed, "/Script/UMG.Overlay:AddChildToOverlay", "AddChildToOverlay(tabs)"); connect(as_pin(cast_o), selfpin(ao), "overlay"); connect(hbp, pin_exact_in(ao, "Content"), "hbox"); connect(tail, exec_in(ao), "-> AddChildToOverlay"); tail = then_out(ao)
    sha = call(ed, "/Script/UMG.OverlaySlot:SetHorizontalAlignment", "tabs HAlign Left"); connect(out(ao, "ReturnValue"), selfpin(sha), "slot"); setval(sha, "InHorizontalAlignment", "Left"); connect(tail, exec_in(sha), "-> HAlign"); tail = then_out(sha)
    sva = call(ed, "/Script/UMG.OverlaySlot:SetVerticalAlignment", "tabs VAlign Bottom"); connect(out(ao, "ReturnValue"), selfpin(sva), "slot"); setval(sva, "InVerticalAlignment", "Bottom"); connect(tail, exec_in(sva), "-> VAlign"); tail = then_out(sva)
    tabs = {}
    for key, label in (("TabRoster", "Roster"), ("TabRanks", "Ranks"), ("TabPerms", "Permissions")):
        cw = create_by_search(ed, [], ("CreateWidget",), f"CreateWidget {label}", exact="UserInterface|CreateWidget"); check(PL.set_pin_value(pin_exact_in(cw, "Class"), TAB_C), f"{label}: class"); connect(pc, pin_exact_in(cw, "OwningPlayer"), "owner")
        connect(tail, exec_in(cw), f"-> CreateWidget {label}"); tail = then_out(cw); bp_ = out(cw, "ReturnValue")
        sl = call(ed, f"{FLX}:SetLabel", f"SetLabel({label})"); connect(bp_, selfpin(sl), "tab"); lt = call(ed, "/Script/Engine.KismetTextLibrary:Conv_StringToText", f"{label} text"); setval(lt, "InString", label); connect(out(lt, "ReturnValue"), pin_exact_in(sl, "NewLabel"), "text"); connect(tail, exec_in(sl), "-> label"); tail = then_out(sl)
        ah = call(ed, "/Script/UMG.HorizontalBox:AddChildToHorizontalBox", f"AddChildToHorizontalBox({label})"); connect(hbp, selfpin(ah), "hbox"); connect(bp_, pin_exact_in(ah, "Content"), "tab"); connect(tail, exec_in(ah), "-> add"); tail = then_out(ah)
        snc = call(ed, "/Script/ConanSandbox.RootWidget:SetupNewChild", f"SetupNewChild({label})"); connect(bp_, pin_exact_in(snc, "child"), "tab"); connect(tail, exec_in(snc), "-> SetupNewChild"); tail = then_out(snc)
        st = ed.add_set_member_variable_node(key); connect(bp_, pin_exact_in(st, key), f"-> {key}"); connect(tail, exec_in(st), f"-> Set {key}"); tail = then_out(st)
        tabs[key] = bp_
    ion = call(ed, f"{FLX}:SetIsToggledOn", "Roster tab on"); connect(tabs["TabRoster"], selfpin(ion), "tab"); setval(ion, "NewIsToggledOn", "true"); setval(ion, "ShouldSendEvent", "false"); setval(ion, "IsInstantTransition", "false"); connect(tail, exec_in(ion), "-> Roster on"); tail = then_out(ion)
    sb = ed.add_set_member_variable_node("TabsBuilt"); PL.set_pin_value(pin_exact_in(sb, "TabsBuilt"), "true"); connect(tail, exec_in(sb), "-> TabsBuilt"); tail = then_out(sb)
    asg_r, h_roster = assign(ed, tabs["TabRoster"], "Events|AssignSignalToggled", "Assign Roster toggled"); connect(tail, exec_in(asg_r), "-> Assign Roster"); tail = then_out(asg_r)
    lib.compile_blueprint(gv)
    asg_k, h_ranks = assign(ed, tabs["TabRanks"], "Events|AssignSignalToggled", "Assign Ranks toggled"); connect(tail, exec_in(asg_k), "-> Assign Ranks"); tail = then_out(asg_k)
    lib.compile_blueprint(gv)
    asg_p, h_perms = assign(ed, tabs["TabPerms"], "Events|AssignSignalToggled", "Assign Perms toggled"); connect(tail, exec_in(asg_p), "-> Assign Perms"); tail = then_out(asg_p)
    print("   toggled handler pins:", pins(h_roster))
    def only_on(h):
        """a toggled handler fires for on and off; only 'on' switches tabs"""
        bp_ = next((p for p in lib.list_output_pins(h) if str(PL.get_pin_name(p)) not in ("then", "OutputDelegate", "Button")), None); check(bp_ is not None, "toggled handler bool pin")
        b = ed.add_branch_node(); connect(bp_, lib.find_condition_pin(b), "toggled on?"); connect(then_out(h), exec_in(b), "handler -> on?"); return then_out(b)
    lib.compile_blueprint(gv)
    asg_c, h_close = assign(ed, None, "Signals|AssignSignalClosing", "Assign SignalClosing"); connect(tail, exec_in(asg_c), "-> Assign Closing")
    # --- shared pieces for the handlers
    def roster_bits():
        gl_ = ed.add_get_member_variable_node("GuildMembersList"); sbx = call(ed, "/Script/UMG.Widget:GetParent", "GetParent(roster)"); connect(out(gl_), selfpin(sbx), "roster")
        so = ed.add_get_member_variable_node("ButtonShowOfflineMembers"); swp = call(ed, "/Script/UMG.Widget:GetParent", "GetParent(show offline)"); connect(out(so), selfpin(swp), "checkbox")
        return out(sbx, "ReturnValue"), out(swp, "ReturnValue")
    def panel_bits():
        c = ed.add_get_member_variable_node("Comp"); p = ed.add_get_member_variable_node("RanksPanel", PL_C); connect(out(c), selfpin(p), "comp")
        iv = call(ed, "/Script/Engine.KismetSystemLibrary:IsValid", "IsValid(panel)"); connect(out(p), pin_exact_in(iv, "Object"), "panel")
        return out(c), out(p), out(iv, "ReturnValue")
    def toggle(tail, active):
        for key in ("TabRoster", "TabRanks", "TabPerms"):
            on = (key == active)
            g = ed.add_get_member_variable_node(key); s = call(ed, f"{FLX}:SetIsToggledOn", f"{key} -> {on}"); connect(out(g), selfpin(s), key)
            setval(s, "NewIsToggledOn", "true" if on else "false"); setval(s, "ShouldSendEvent", "false"); setval(s, "IsInstantTransition", "false"); connect(tail, exec_in(s), f"-> {key}"); tail = then_out(s)
        return tail
    # Roster click
    t = only_on(h_roster); sbx, swp = roster_bits(); t = set_vis(ed, sbx, "Visible", t, "roster"); t = set_vis(ed, swp, "Visible", t, "show offline")
    c, p, valid = panel_bits(); b = ed.add_branch_node(); connect(valid, lib.find_condition_pin(b), "panel?"); connect(t, exec_in(b), "-> panel?")
    t2 = set_vis(ed, p, "Collapsed", then_out(b), "panel"); toggle(t2, "TabRoster")
    # the toggle chain starts at the SetIsToggledOn node fed by t2; the no-panel branch joins it there
    first_toggle = PL.get_owning_node(list(PL.list_connected_pins(t2))[0]); connect(lib.find_else_pin(b), exec_in(first_toggle), "no panel -> toggles")
    # Ranks / Permissions click: hide the roster, light the tab; show the panel in the right mode or request it
    for h_, key, mode, show_fn in ((h_ranks, "TabRanks", "0", "ShowRanks"), (h_perms, "TabPerms", "1", "ShowPerms")):
        t = only_on(h_); sbx, swp = roster_bits(); t = set_vis(ed, sbx, "Collapsed", t, "roster"); t = set_vis(ed, swp, "Collapsed", t, "show offline"); t = toggle(t, key)
        c, p, valid = panel_bits(); b = ed.add_branch_node(); connect(valid, lib.find_condition_pin(b), "panel?"); connect(t, exec_in(b), "-> panel?")
        t2 = set_vis(ed, p, "Visible", then_out(b), "panel"); sf = call(ed, f"{W_C}:{show_fn}", f"panel.{show_fn}"); connect(p, selfpin(sf), "panel"); connect(t2, exec_in(sf), f"-> {show_fn}")
        sm = ed.add_set_member_variable_node("PendingMode", PL_C); connect(c, selfpin(sm), "comp"); PL.set_pin_value(pin_exact_in(sm, "PendingMode"), mode); connect(lib.find_else_pin(b), exec_in(sm), "no panel -> PendingMode")
        sh = ed.add_set_member_variable_node("RanksHost", PL_C); connect(c, selfpin(sh), "comp"); connect(out(me), pin_exact_in(sh, "RanksHost"), "self"); connect(then_out(sm), exec_in(sh), "-> RanksHost = self")
        rpc = call(ed, f"{PL_C}:Server_ServerRequestClanTable", "ServerRequestClanTable"); connect(c, selfpin(rpc), "comp"); connect(then_out(sh), exec_in(rpc), "-> request table")
    # Closing: save + tear down the panel, restore the roster state
    t = then_out(h_close); c, p, valid = panel_bits(); b = ed.add_branch_node(); connect(valid, lib.find_condition_pin(b), "panel?"); connect(t, exec_in(b), "closing -> panel?")
    mr = ed.add_get_member_variable_node("ModalRoot", W_C); connect(p, selfpin(mr), "panel"); rfm = call(ed, "/Script/UMG.Widget:RemoveFromParent", "RemoveFromParent(modal)"); connect(out(mr), selfpin(rfm), "modal"); connect(then_out(b), exec_in(rfm), "-> remove modal"); t = then_out(rfm)
    rf = call(ed, "/Script/UMG.Widget:RemoveFromParent", "RemoveFromParent(panel)"); connect(p, selfpin(rf), "panel"); connect(t, exec_in(rf), "-> remove"); t = then_out(rf)
    cl = ed.add_set_member_variable_node("RanksPanel", PL_C); connect(c, selfpin(cl), "comp"); connect(t, exec_in(cl), "-> RanksPanel = null"); t = then_out(cl)
    sbx, swp = roster_bits(); t = set_vis(ed, sbx, "Visible", t, "roster"); t = set_vis(ed, swp, "Visible", t, "show offline"); toggle(t, "TabRoster")
    compile_ok(gv, [(ed, "EventGraph")], "W_GuildView")
    if MODE == "real" and not failures: save(gv, GV_DISK, "W_GuildView override")
    elif MODE == "real": print("   NOT SAVING: failures above")
result()
