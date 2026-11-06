"""소품 41종 → web/models/props/<Name>.glb (미터, Y-up, 원점=FBX 와 같은 피벗).  python3 export_glb_props.py"""
import json
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glbkit as G  # noqa: E402

BL = G.WEB + "/blend/"
OUT = G.WEB + "/models/props"
os.makedirs(OUT, exist_ok=True)
SRC = {
    "Printer.blend": ["SM_Printer", "REF_PrintKey", "REF_PrintKey_Half"],
    "Tools.blend": ["SM_Tool_Cryo", "SM_Tool_Taser", "SM_Tool_VentLock", "REF_VentHatch"],
    "Barrier.blend": ["SM_Barrier_3m", "SM_BarrierLow_3m", "SM_BarrierLowCab"],
    "Shelf.blend": ["SM_Shelf", "SM_BarrierLocker"],
    "Structures.blend": ["SM_Catwalk", "SM_Console", "SM_Container", "SM_Desk", "SM_LabTable", "SM_LabTank",
                         "SM_LowBox", "SM_StairStep_1", "SM_StairStep_2", "SM_StairStep_3", "SM_StairStep_4", "SM_Tank"],
    "Env.blend": ["SM_CeilingLamp", "SM_CeilingTruss", "SM_Pillar", "SM_WallPost"],
    "Gameplay2.blend": ["SM_Collar", "SM_Collar_Open", "SM_ExitDoor", "SM_Key_Collar", "SM_Key_Collar_Half",
                        "SM_Key_Exit", "SM_Key_Exit_Half", "SM_Vent"],
    "Crate.blend": ["SM_Crate"],
    "Materials.blend": ["SM_Mat_Battery", "SM_Mat_Coil", "SM_Mat_LN2"],
    "Arrow.blend": ["SM_DirArrow"],
}

G.make_emissive_tex()
report = {}
for blend, names in SRC.items():
    bpy.ops.wm.open_mainfile(filepath=BL + blend)
    G._CACHE.clear()
    sc = bpy.context.scene
    for name in names:
        root = bpy.data.objects[name]
        tree = [root] + [c for c in root.children_recursive if c.type == "MESH"]
        dg = bpy.context.evaluated_depsgraph_get()
        inv = root.matrix_world.inverted()
        S = G.scale_matrix()
        for o in tree:
            o.name = o.name + "__o"
        copies, cmap = [], {}
        for o in tree:
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
            me.transform(S @ inv @ o.matrix_world)
            nm = o.name[:-3]
            me.name = nm
            c = bpy.data.objects.new(nm, me)
            sc.collection.objects.link(c)
            c.visible_shadow = o.visible_shadow
            cmap[o] = c
            copies.append(c)
        for o in tree[1:]:
            par = o.parent if o.parent in cmap else root
            cmap[o].parent = cmap[par]
        G.swap_materials(copies)
        G.select(copies, copies[0])
        path = os.path.join(OUT, name + ".glb")
        G.gltf_export(path, export_extras=False, export_animations=False, export_skins=False)
        lo = [min(v.co[i] for c in copies for v in c.data.vertices) for i in range(3)]
        hi = [max(v.co[i] for c in copies for v in c.data.vertices) for i in range(3)]
        tris = sum(len(p.vertices) - 2 for c in copies for p in c.data.polygons)
        # Blender Z-up → glTF Y-up:  (x, y, z) → (x, z, -y)
        size = [hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1]]
        info = {"source": blend, "units": "m", "sizeXYZ_m": [round(v, 4) for v in size],
                "minY_m": round(lo[2], 4), "tris": tris, "parts": [c.name for c in copies]}
        G.patch_glb(path, extras={"escapelab": {"asset": name, "stud_m": G.STUD_M, **info}})
        report[name] = info
        for c in copies:
            me = c.data
            bpy.data.objects.remove(c, do_unlink=True)
            bpy.data.meshes.remove(me)
        for o in tree:
            o.name = o.name[:-3]
        print("OK", name, info["sizeXYZ_m"], tris)

with open(os.path.join(OUT, "index.json"), "w") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)
print("DONE", len(report))
