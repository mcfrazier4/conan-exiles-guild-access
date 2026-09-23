# Editing Blueprints headlessly with the dev kit's Python

Discovered 2026-09-23. This replaces click-by-click Blueprint wiring for most
tasks, and it replaces screenshots for verification entirely.

## Why not the marketplace Unreal MCP plugin

Epic's `ModelContextProtocol` and `Toolsets/*` plugins exist in this dev kit as
**descriptors only** - no compiled binaries anywhere in the 169 GB install.
They cannot be enabled in a prebuilt, no-code editor. The Claude marketplace
"Unreal Engine skills" plugin depends on them, so it does not work here.

## What does work

- `PythonScriptPlugin` ships with binaries and is **already enabled**
  (`LogPython: Using Python 3.11.8` in every editor log).
- The headless editor runs a script in ~30 s, versus ~3 min to open the GUI:

      & "<DevKit>\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" ^
          "<DevKit>\UE4\ConanSandbox.uproject" ^
          -run=pythonscript -script="<file>.py" -ModDevKit ^
          -stdout -FullStdOutLogOutput -unattended -nopause -nosplash

  `-ModDevKit` is required so the mod overlay is mounted. Exit code 3 on
  teardown is normal; check for "Python script executed successfully".
- `EditorScriptingUtilities` (`unreal.EditorAssetLibrary`) is **not** enabled.
  Use `unreal.load_asset(path)` and `unreal.EditorLoadingAndSavingUtils`.

## Asset paths

- New mod assets: `/Game/Mods/GuildAccess/Local/<Name>`
- **Overrides load at their vanilla path**, e.g.
  `/Game/Systems/Building/Placeables/BP_PlaceableItemContainer`. The
  `/Game/Mods/GuildAccess/Content/...` path does not resolve.

## The API (UE 5.8 shape)

Three classes. The first two are new in 5.8 and are where the authoring lives.

    unreal.BlueprintGraphEditor        - per-graph editing handle
        get_graph_editor_by_name(blueprint, graph_name) -> editor   (static)
        get_graph_editor(graph) -> editor                          (static, 1 arg)
        ed.list_all_nodes() -> [K2Node]
        ed.list_nodes_of_class(cls)
        ed.add_call_function_node(function_path) -> K2Node_CallFunction
        ed.create_node_from_name('Utilities|FlowControl|Branch', location, context_pins)
        ed.add_return_node(), ed.add_branch_node(), ed.add_macro_node(), ...
        ed.remove_nodes([nodes])
        ed.find_graph_entry_pin(), ed.find_event_node(...)

    unreal.BlueprintGraphPinLibrary    - static pin functions (pins are proxies)
        get_pin_name(pin) / get_pin_direction(pin) / get_pin_type(pin)
        get_pin_value(pin) -> str          ('' when connected or unset)
        set_pin_value(pin, str) -> bool    literal on an input pin
        list_connected_pins(pin)           compare with is_same_native_pin, not ==
        try_create_connection(pin, other) -> bool
        break_pin_links(pin) / break_single_pin_link(pin, other)
        get_owning_node(pin) -> K2Node

    unreal.BlueprintEditorLibrary      - blueprint-level helpers
        find_graph(bp, name), list_graph_names(bp), list_functions(bp)
        list_all_pins(node), list_input_pins(node), list_output_pins(node)
        find_input_pin(node, name), find_output_pin(node, name)
        find_condition_pin(node)           K2Node_IfThenElse only
        get_node_title(node), compile_blueprint(bp)
        add_function_graph / add_function_override / add_member_variable ...

`EdGraph.Nodes` is a protected property; always go through
`BlueprintGraphEditor.list_all_nodes()`.

## Read-only dump recipe

    lib, GE, PL = unreal.BlueprintEditorLibrary, unreal.BlueprintGraphEditor, unreal.BlueprintGraphPinLibrary
    bp = unreal.load_asset('/Game/Mods/GuildAccess/Local/BPL_GuildAccess')
    ed = GE.get_graph_editor_by_name(bp, 'GetPawnRank')
    for n in ed.list_all_nodes():
        print(n.get_class().get_name(), lib.get_node_title(n))
        for p in lib.list_all_pins(n):
            print('  ', PL.get_pin_name(p), PL.get_pin_direction(p), repr(PL.get_pin_value(p)),
                  [PL.get_pin_name(c) for c in PL.list_connected_pins(p)])

Run it before and after any edit. It is the source of truth for what is in a
graph; a screenshot is not.

## Gotchas found the hard way

- **`-ModDevKit` breaks saving mod-owned assets.** With the mod platform layer
  installed, saving `/Game/Mods/GuildAccess/Local/*` fails at the
  delete-and-replace step ("DeleteFile was unable to delete ... Error saving").
  Overrides are unaffected because they go through its remap path. So:
  - editing an **override** (`/Game/Systems/...`): run **with** `-ModDevKit`
  - editing a **new mod asset** (`/Game/Mods/GuildAccess/Local/...`): run
    **without** it
  - a script that touches both needs two runs.
- **The save API lies.** `save_dirty_packages` returned `True` ("All files are
  already saved") right after a save had failed. `save_packages` returned
  `False` correctly. Never trust either: record the file's mtime and size
  before, and assert they changed after.
- The vanilla asset is never written even when the log prints
  `FILE="../../../UE4/Content/Systems/..."`: that is the logical path, and the
  platform layer redirects the physical write into
  `GuildAccess/Content/...`. Verified by byte-comparing the vanilla file
  against a backup taken before the write. Keep taking that backup anyway.
- **Python strips the `Kismet` prefix.** `KismetMathLibrary` is
  `unreal.MathLibrary`, `KismetSystemLibrary` is `unreal.SystemLibrary`.
  `unreal.KismetMathLibrary` is an AttributeError that aborts the whole script.
- Exit code 3 from `UnrealEditor-Cmd.exe` on teardown is normal. The success
  signal is `Python script executed successfully` plus your own on-disk checks.

## Vanilla patterns to copy (from headless dumps, 2026-09-23)

**Interface functions with exec pins are events in the EventGraph**, not
function graphs: `Event InteractableActivate`, `Event InteractableMenu`,
`Event SetShareAccess`. Use `add_event_override`, not `add_function_override`.

**Radial menu entries** (`BP_PL_Door :: Event InteractableMenu`):

    Event InteractableMenu(RadialMenu, HitIndex)
      -> Parent: InteractableMenu
      -> RadialMenu.AddItem(label: Text, subtitle: Text, icon, keyShortcutName='None', index=0) -> RadialMenuEntry
      -> Bind Event to Signal Clicked(entry, <custom event delegate>)

`RadialMenuEntry` (Python `unreal.RadialMenuEntry`) has `add_sub_item`,
`get_sub_item`, `goto_parent`, `set_label`, `set_icon_from_texture`,
`set_is_enabled`, `signal_clicked`, `user_tag/user_value/user_object`.
Submenus are native.

**Click-to-server**: click handlers run on the client and call an interface
message on the player controller (`Controller_SetDoorAutoCloseEnabled(Door,
Enabled)`, `K2Node_Message`), which owns the server RPC. UE only delivers
Run-on-Server RPCs from actors the client owns, and a placeable is not owned by
the player - so a mod cannot put a server RPC on the chest without first
making the player its net owner (`PlaceableBase.set_owner` is exposed) or
overriding the player controller.

**Server to client feedback**: `ConanPlayerController.client_hud_show_notification`,
`client_show_message_box`, `client_show_rich_message_box`.

**Persistence**: `game_0.db` table `properties(object_id, name, value BLOB)`
stores per-object variables keyed `<ConcreteClass_C>.<VarName>`
(`BP_PL_Chest_Medium_C.DecayDisabled`), only for `SaveGame`-flagged properties
with non-default values. `ConanBuildingPersistenceComponent.set_dirty` is
callable from Blueprint. The `SaveGame` flag on a Blueprint variable cannot be
set through this Python API - it is a GUI checkbox.

**Placeable door open logic** lives in `BP_PL_Door :: Event Custom
Interaction(Instigator, HitIndex, IsOwner)`, raised natively after the
ownership check; `Instigator` is a controller (`Get Controlled Pawn` follows).

## Rules

- Probe scripts are read-only unless the file name says otherwise.
- After a write script: `compile_blueprint`, then save through
  `unreal.EditorLoadingAndSavingUtils`, then re-run the dump to verify.
- The GUI editor must be closed while a write script runs.
- Never `git add -A` after a script has written assets; stage deliberately
  (see the `.uasset` house rule in CLAUDE.md).
