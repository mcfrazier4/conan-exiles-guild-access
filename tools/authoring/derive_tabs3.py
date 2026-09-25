"""One-off: derive author_v2_tabs3.py (three tabs, panel v5) from author_v2_tabs.py."""
import os, ast
here = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(here, "author_v2_tabs.py")).read()
def rep(a, b):
    global s
    assert a in s, a[:70]
    s = s.replace(a, b)
rep('"""v2 - Roster / Ranks tabs on the clan window.', '"""v2 - Roster / Ranks / Permissions tabs on the clan window (third version: panel v5, no Save on close).')
# ---- player: PendingMode var, ShowRanks/ShowPerms after adding, drop the viewport fallback, BeginPlay request on clients
rep('''    for nm, t in (("RanksHost", lib.get_object_reference_type(unreal.GuildViewBase)), ("RanksPanel", lib.get_object_reference_type(unreal.load_class(None, W_C)))):''',
    '''    for nm, t in (("RanksHost", lib.get_object_reference_type(unreal.GuildViewBase)), ("RanksPanel", lib.get_object_reference_type(unreal.load_class(None, W_C))), ("PendingMode", lib.get_basic_type_by_name("int"))):''')
rep('''    victims = walk_exec(then_out(cw), stop_titles=("AddToViewport",)); atv = [n for n in ed.list_all_nodes() if title(n).replace(" ", "") == "AddToViewport"]; check(len(atv) == 1, "AddToViewport node"); atv = atv[0]
    print("   stripping:", sorted(set(title(n) for n in victims)))
    ed.remove_nodes(victims); PL.break_pin_links(then_out(cw))''',
    '''    victims = walk_exec(then_out(cw)); print("   stripping (incl. the viewport fallback):", sorted(set(title(n) for n in victims)))
    ed.remove_nodes(victims); PL.break_pin_links(then_out(cw))''')
rep('''    br = ed.add_branch_node(); connect(out(iv, "ReturnValue"), lib.find_condition_pin(br), "valid?"); connect(then_out(sh), exec_in(br), "-> Branch"); connect(lib.find_else_pin(br), exec_in(atv), "no host -> AddToViewport (fallback)")''',
    '''    br = ed.add_branch_node(); connect(out(iv, "ReturnValue"), lib.find_condition_pin(br), "valid?"); connect(then_out(sh), exec_in(br), "-> Branch")''')
rep('''    sp_ = ed.add_set_member_variable_node("RanksPanel"); connect(panel, pin_exact_in(sp_, "RanksPanel"), "panel -> RanksPanel"); connect(t, exec_in(sp_), "-> RanksPanel"); t = then_out(sp_)
    clr = ed.add_set_member_variable_node("RanksHost"); connect(t, exec_in(clr), "-> RanksHost = null")''',
    '''    sp_ = ed.add_set_member_variable_node("RanksPanel"); connect(panel, pin_exact_in(sp_, "RanksPanel"), "panel -> RanksPanel"); connect(t, exec_in(sp_), "-> RanksPanel"); t = then_out(sp_)
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
    else: print("   BeginPlay already wired")''')
# ---- guildview: third tab, PendingMode, ShowRanks/ShowPerms, closing just removes the panel and its modal
rep('''    for nm, t in (("TabsBuilt", lib.get_basic_type_by_name("bool")), ("TabRoster", lib.get_object_reference_type(unreal.FLXButtonBase)), ("TabRanks", lib.get_object_reference_type(unreal.FLXButtonBase)), ("Comp", lib.get_object_reference_type(unreal.load_class(None, PL_C)))):''',
    '''    for nm, t in (("TabsBuilt", lib.get_basic_type_by_name("bool")), ("TabRoster", lib.get_object_reference_type(unreal.FLXButtonBase)), ("TabRanks", lib.get_object_reference_type(unreal.FLXButtonBase)), ("TabPerms", lib.get_object_reference_type(unreal.FLXButtonBase)), ("Comp", lib.get_object_reference_type(unreal.load_class(None, PL_C)))):''')
rep('''    for key, label in (("TabRoster", "Roster"), ("TabRanks", "Ranks")):''', '''    for key, label in (("TabRoster", "Roster"), ("TabRanks", "Ranks"), ("TabPerms", "Permissions")):''')
rep('''    asg_k, h_ranks = assign(ed, tabs["TabRanks"], "Events|AssignSignalToggled", "Assign Ranks toggled"); connect(tail, exec_in(asg_k), "-> Assign Ranks"); tail = then_out(asg_k)''',
    '''    asg_k, h_ranks = assign(ed, tabs["TabRanks"], "Events|AssignSignalToggled", "Assign Ranks toggled"); connect(tail, exec_in(asg_k), "-> Assign Ranks"); tail = then_out(asg_k)
    lib.compile_blueprint(gv)
    asg_p, h_perms = assign(ed, tabs["TabPerms"], "Events|AssignSignalToggled", "Assign Perms toggled"); connect(tail, exec_in(asg_p), "-> Assign Perms"); tail = then_out(asg_p)''')
rep('''    def toggle(tail, roster_on):
        for key, on in (("TabRoster", roster_on), ("TabRanks", not roster_on)):''',
    '''    def toggle(tail, active):
        for key in ("TabRoster", "TabRanks", "TabPerms"):
            on = (key == active)''')
rep('''    t2 = set_vis(ed, p, "Collapsed", then_out(b), "panel"); toggle(t2, True)''', '''    t2 = set_vis(ed, p, "Collapsed", then_out(b), "panel"); toggle(t2, "TabRoster")''')
rep('''    # Ranks click
    t = only_on(h_ranks); sbx, swp = roster_bits(); t = set_vis(ed, sbx, "Collapsed", t, "roster"); t = set_vis(ed, swp, "Collapsed", t, "show offline"); t = toggle(t, False)
    c, p, valid = panel_bits(); b = ed.add_branch_node(); connect(valid, lib.find_condition_pin(b), "panel?"); connect(t, exec_in(b), "-> panel?")
    set_vis(ed, p, "Visible", then_out(b), "panel")
    sh = ed.add_set_member_variable_node("RanksHost", PL_C); connect(c, selfpin(sh), "comp"); connect(out(me), pin_exact_in(sh, "RanksHost"), "self"); connect(lib.find_else_pin(b), exec_in(sh), "no panel -> RanksHost = self")
    rpc = call(ed, f"{PL_C}:Server_ServerRequestClanTable", "ServerRequestClanTable"); connect(c, selfpin(rpc), "comp"); connect(then_out(sh), exec_in(rpc), "-> request table")''',
    '''    # Ranks / Permissions click: hide the roster, light the tab; show the panel in the right mode or request it
    for h_, key, mode, show_fn in ((h_ranks, "TabRanks", "0", "ShowRanks"), (h_perms, "TabPerms", "1", "ShowPerms")):
        t = only_on(h_); sbx, swp = roster_bits(); t = set_vis(ed, sbx, "Collapsed", t, "roster"); t = set_vis(ed, swp, "Collapsed", t, "show offline"); t = toggle(t, key)
        c, p, valid = panel_bits(); b = ed.add_branch_node(); connect(valid, lib.find_condition_pin(b), "panel?"); connect(t, exec_in(b), "-> panel?")
        t2 = set_vis(ed, p, "Visible", then_out(b), "panel"); sf = call(ed, f"{W_C}:{show_fn}", f"panel.{show_fn}"); connect(p, selfpin(sf), "panel"); connect(t2, exec_in(sf), f"-> {show_fn}")
        sm = ed.add_set_member_variable_node("PendingMode", PL_C); connect(c, selfpin(sm), "comp"); PL.set_pin_value(pin_exact_in(sm, "PendingMode"), mode); connect(lib.find_else_pin(b), exec_in(sm), "no panel -> PendingMode")
        sh = ed.add_set_member_variable_node("RanksHost", PL_C); connect(c, selfpin(sh), "comp"); connect(out(me), pin_exact_in(sh, "RanksHost"), "self"); connect(then_out(sm), exec_in(sh), "-> RanksHost = self")
        rpc = call(ed, f"{PL_C}:Server_ServerRequestClanTable", "ServerRequestClanTable"); connect(c, selfpin(rpc), "comp"); connect(then_out(sh), exec_in(rpc), "-> request table")''')
rep('''    sv = call(ed, f"{W_C}:SaveNow", "panel.SaveNow"); connect(p, selfpin(sv), "panel"); connect(then_out(b), exec_in(sv), "-> SaveNow"); t = then_out(sv)
    rf = call(ed, "/Script/UMG.Widget:RemoveFromParent", "RemoveFromParent(panel)"); connect(p, selfpin(rf), "panel"); connect(t, exec_in(rf), "-> remove"); t = then_out(rf)''',
    '''    mr = ed.add_get_member_variable_node("ModalRoot", W_C); connect(p, selfpin(mr), "panel"); rfm = call(ed, "/Script/UMG.Widget:RemoveFromParent", "RemoveFromParent(modal)"); connect(out(mr), selfpin(rfm), "modal"); connect(then_out(b), exec_in(rfm), "-> remove modal"); t = then_out(rfm)
    rf = call(ed, "/Script/UMG.Widget:RemoveFromParent", "RemoveFromParent(panel)"); connect(p, selfpin(rf), "panel"); connect(t, exec_in(rf), "-> remove"); t = then_out(rf)''')
rep('''    sbx, swp = roster_bits(); t = set_vis(ed, sbx, "Visible", t, "roster"); t = set_vis(ed, swp, "Visible", t, "show offline"); toggle(t, True)''',
    '''    sbx, swp = roster_bits(); t = set_vis(ed, sbx, "Visible", t, "roster"); t = set_vis(ed, swp, "Visible", t, "show offline"); toggle(t, "TabRoster")''')
ast.parse(s)
open(os.path.join(here, "author_v2_tabs3.py"), "w").write(s); print("author_v2_tabs3.py written")
