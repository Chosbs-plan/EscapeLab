"""캐릭터 5종 → web/models/characters/CH_<ClassId>.glb (메시 + 뼈 + 애니메이션 전부, 미터).

스터드 → 미터 베이크: 메시 정점 · 바인드 뼈 위치 ×0.28, 뼈 위치 키 ×0.28 (회전 키는 그대로).
베이크 전후로 모든 애니메이션의 시작 · 중간 · 끝 프레임에서 변형된 본체 정점을 비교해
(후 = 전 × 0.28) 오차를 리포트한다.   python3 export_glb_chars.py
"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glbkit as G  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = G.WEB + "/models/characters"
os.makedirs(OUT, exist_ok=True)

SURV_ANIMS = [("Idle", 60, True, "Movement"), ("Walk", 32, True, "Movement"), ("Run", 20, True, "Movement"),
              ("JumpStart", 9, False, "Movement"), ("JumpAir", 20, True, "Movement"), ("JumpLand", 10, False, "Movement"),
              ("Fall", 16, True, "Movement"), ("SlideEnter", 9, False, "Action"), ("SlideLoop", 16, True, "Movement"),
              ("SlideExit", 11, False, "Action"), ("CrawlLoop", 24, True, "Movement"), ("StandUp", 15, False, "Action")]
TAG_ANIMS = [("Idle", 60, True, "Movement"), ("Walk", 36, True, "Movement"), ("Run", 20, True, "Movement"),
             ("HighJumpPrep", 11, False, "Movement"), ("HighJumpAir", 20, True, "Movement"),
             ("HighJumpLand", 13, False, "Movement"), ("Fall", 16, True, "Movement"), ("ChargeLoop", 16, True, "Action"),
             ("Dash", 12, True, "Action"), ("DashMissRecover", 25, False, "Action"),
             ("DashHitPin", 17, False, "Action", "마지막 자세 유지")]
SETS = [
    (HERE + "/out_surv/Survivors_Rig_anims.blend", "A_Survivor_", SURV_ANIMS, 1.15, "survivor",
     ["Raccoon", "LabRat", "Crow"], ["", "_Outline"]),
    (HERE + "/out_tag/Taggers_Rig.blend", "A_Tagger_", TAG_ANIMS, 1.95, "tagger",
     ["Hound", "Root"], ["", "_Outline", "_Status"]),
]
ATTACH = {"RightGrip": "열쇠 · 도구", "LeftGrip": "보조 (루트 태블릿)", "NeckAttach": "목줄 · LED",
          "BackAttach": "등 도구 표시", "BeltEquip": "하운드 허리 장비"}


def assign(r, act):
    r.animation_data_create()
    r.animation_data.action = act
    if act is not None and len(act.slots):
        r.animation_data.action_slot = act.slots[0]


def fcurves(act):
    for L in act.layers:
        for s in L.strips:
            for cb in s.channelbags:
                yield from cb.fcurves


def sample(r, body, act, frames):
    assign(r, act)
    out = []
    sc = bpy.context.scene
    for f in frames:
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = body.evaluated_get(dg)
        me = ev.to_mesh()
        a = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", a)
        a = a.reshape(-1, 3) @ np.array(ev.matrix_world.to_3x3()).T + np.array(ev.matrix_world.translation)
        ev.to_mesh_clear()
        out.append(a)
    assign(r, None)
    return out


report = {}
for blend, prefix, anims, judge, side, ids, suffixes in SETS:
    bpy.ops.wm.open_mainfile(filepath=blend)
    G._CACHE.clear()
    sc = bpy.context.scene
    sc.render.fps = 30
    acts = {a[0]: bpy.data.actions[prefix + a[0]] for a in anims}
    chars = []
    for cid in ids:
        r = bpy.data.objects[f"CH_{cid}_Rig"]
        r.location, r.rotation_euler, r.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
        parts = [bpy.data.objects[f"CH_{cid}{s}"] for s in suffixes]
        chars.append((cid, r, parts))
    bpy.context.view_layer.update()

    # --- 베이크 전 샘플 ---
    before = {}
    for cid, r, parts in chars:
        for a in anims:
            n = a[1]
            before[(cid, a[0])] = sample(r, parts[0], acts[a[0]], [1, (n + 1) // 2, n])

    # --- 베이크 ---
    S = G.scale_matrix()
    for cid, r, parts in chars:
        assign(r, None)
        for pb in r.pose.bones:
            pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
        inv = r.matrix_world.inverted()
        for o in parts:
            M = inv @ o.matrix_world
            o.data.transform(S @ M)
            o.matrix_parent_inverse.identity()
            o.matrix_basis.identity()
        G.select([r], r)
        bpy.ops.object.mode_set(mode="EDIT")
        for eb in r.data.edit_bones:
            eb.head *= G.STUD_M
            eb.tail *= G.STUD_M
        bpy.ops.object.mode_set(mode="OBJECT")
    for act in acts.values():
        for fc in fcurves(act):
            if fc.data_path.endswith(".location"):
                for kp in fc.keyframe_points:
                    kp.co[1] *= G.STUD_M
                    kp.handle_left[1] *= G.STUD_M
                    kp.handle_right[1] *= G.STUD_M
                fc.update()
    bpy.context.view_layer.update()

    # --- 베이크 후 비교 ---
    for cid, r, parts in chars:
        err = 0.0
        for a in anims:
            n = a[1]
            aft = sample(r, parts[0], acts[a[0]], [1, (n + 1) // 2, n])
            for b_, a_ in zip(before[(cid, a[0])], aft):
                err = max(err, float(np.abs(b_ * G.STUD_M - a_).max()))
        report.setdefault(cid, {})["bake_max_err_m"] = err
        print("BAKE", cid, f"{err:.2e}")

    # --- 내보내기: NLA 트랙 1개 = glTF 애니메이션 1개 ---
    G.swap_materials([p for c in chars for p in c[2]])
    for cid, r, parts in chars:
        r.animation_data_create()
        for tr in list(r.animation_data.nla_tracks):
            r.animation_data.nla_tracks.remove(tr)
        for a in anims:
            tr = r.animation_data.nla_tracks.new()
            tr.name = a[0]
            st = tr.strips.new(a[0], 1, acts[a[0]])
            if hasattr(st, "action_slot") and len(acts[a[0]].slots):
                st.action_slot = acts[a[0]].slots[0]
            tr.mute = False
        assign(r, None)
        G.select([r] + parts, r)
        path = os.path.join(OUT, f"CH_{cid}.glb")
        G.gltf_export(path, export_extras=False, export_skins=True, export_animations=True,
                      export_animation_mode="NLA_TRACKS", export_force_sampling=True, export_frame_step=1,
                      export_anim_slide_to_zero=True, export_def_bones=False, export_rest_position_armature=True,
                      export_reset_pose_bones=True, export_influence_nb=4, export_optimize_animation_size=False,
                      export_anim_single_armature=True, export_bake_animation=False)
        bones = [b.name for b in r.data.bones]
        meta = {"classId": cid, "side": side, "units": "m", "judgeHeight_m": judge, "fps": 30,
                "parts": [p.name for p in parts],
                "attachBones": {k: v for k, v in ATTACH.items() if k in bones},
                "anims": {a[0]: {"frames": a[1], "loop": a[2], "priority": a[3],
                                 **({"note": a[4]} if len(a) > 4 else {})} for a in anims}}
        js = G.patch_glb(path, extras={"escapelab": meta})
        report[cid].update({"bones": len(bones), "anims": [x["name"] for x in js.get("animations", [])],
                            "tris": sum(len(p.vertices) - 2 for o in parts for p in o.data.polygons)})
        for tr in list(r.animation_data.nla_tracks):
            r.animation_data.nla_tracks.remove(tr)
        print("OK", cid, report[cid])

with open(os.path.join(OUT, "export_report.json"), "w") as fh:
    json.dump(report, fh, ensure_ascii=False, indent=1)
print("DONE")
