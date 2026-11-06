"""웹(Three.js)용 glTF 내보내기 공용 — 재질 변환 · 미터 베이크 · GLB 후처리.

Roblox 미리보기 재질(Diffuse + Emission 노드)은 glTF 내보내기가 읽지 못하므로
내보내기 직전에 glTF 가 이해하는 Principled 재질로 바꿔 끼운다.
  M_LabRoblox  → 기본색 T_Lab_Palette, 발광 T_Lab_Palette_Emissive(×1.6), 거칠기 1 · 금속 0 (램버트 근사)
  M_CH_<Id>    → 기본색 T_CH_<Id>
  M_Glass      → #9FC3CC 알파 0.2, 블렌드, 양면
  M_Outline    → #1B1D20 unlit (KHR_materials_unlit), 단면 — 인버티드 헐이라 앞면 컬링으로 외곽선이 됨
  M_Status_*   → 해당 색 unlit (Roblox Neon 대응)
"""
import json
import os
import struct

import bpy
from mathutils import Matrix

STUD_M = 0.28
WEB = os.path.dirname(os.path.abspath(__file__)) + "/web"
TEX = WEB + "/tex"
UNLIT_PREFIX = ("M_Outline", "M_Status_")


def srgb(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def make_emissive_tex():
    from PIL import Image, ImageChops
    alb = Image.open(TEX + "/T_Lab_Palette.png").convert("RGB")
    m = Image.open(TEX + "/T_Lab_Palette_E.png").convert("L")
    ImageChops.multiply(alb, Image.merge("RGB", (m, m, m))).save(TEX + "/T_Lab_Palette_Emissive.png")


def _img(path, colorspace="sRGB"):
    name = os.path.basename(path)
    im = bpy.data.images.get("W_" + name)
    if im is None:
        im = bpy.data.images.load(path)
        im.name = "W_" + name
    im.colorspace_settings.name = colorspace
    return im


def _principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = True
    nt = m.node_tree
    nt.nodes.clear()
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(b.outputs[0], o.inputs["Surface"])
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Metallic"].default_value = 0.0
    return m, nt, b


def _tex(nt, b, path, sock, colorspace="sRGB"):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = _img(path, colorspace)
    nt.links.new(t.outputs["Color"], b.inputs[sock])
    return t


_CACHE = {}


def web_material(src):
    n = src.name
    if n in _CACHE:
        return _CACHE[n]
    if n == "M_LabRoblox":
        m, nt, b = _principled(n)
        _tex(nt, b, TEX + "/T_Lab_Palette.png", "Base Color")
        _tex(nt, b, TEX + "/T_Lab_Palette_Emissive.png", "Emission Color")
        b.inputs["Emission Strength"].default_value = 1.6
    elif n.startswith("M_CH_"):
        img = next(x.image for x in src.node_tree.nodes if x.type == "TEX_IMAGE")
        p = TEX + "/" + img.name
        img.save(filepath=p) if not os.path.exists(p) else None
        m, nt, b = _principled(n)
        _tex(nt, b, p, "Base Color")
    elif n == "M_Glass":
        m, nt, b = _principled(n)
        b.inputs["Base Color"].default_value = srgb("#9FC3CC") + (1,)
        b.inputs["Alpha"].default_value = 0.2
        m.use_backface_culling = False
        m.surface_render_method = "BLENDED"
    elif n == "M_Outline":
        m, nt, b = _principled(n)
        b.inputs["Base Color"].default_value = srgb("#1B1D20") + (1,)
    elif n.startswith("M_Status_"):
        m, nt, b = _principled(n)
        b.inputs["Base Color"].default_value = srgb(n[len("M_Status_"):]) + (1,)
    else:
        raise RuntimeError(f"모르는 재질: {n}")
    src_name = n
    src.name = n + "__src"
    m.name = src_name
    _CACHE[n] = m
    return m


def swap_materials(objs):
    web = set(id(m) for m in _CACHE.values())
    for o in objs:
        if o.type != "MESH":
            continue
        for sl in o.material_slots:
            m = sl.material
            if m is None or id(m) in web:
                continue
            key = m.name[:-5] if m.name.endswith("__src") else m.name
            sl.material = _CACHE[key] if key in _CACHE else web_material(m)
            web = set(id(x) for x in _CACHE.values())


# ---------------------------------------------------------------------------
# GLB 후처리: unlit 확장 + extras
# ---------------------------------------------------------------------------
def patch_glb(path, extras=None, scene_extras=None):
    with open(path, "rb") as fh:
        data = fh.read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67
    jl, jt = struct.unpack_from("<II", data, 12)
    js = json.loads(data[20:20 + jl].decode("utf-8"))
    rest = data[20 + jl:]
    used = set(js.get("extensionsUsed", []))
    for m in js.get("materials", []):
        if m["name"].startswith(UNLIT_PREFIX):
            m.setdefault("extensions", {})["KHR_materials_unlit"] = {}
            m.pop("emissiveFactor", None)
            pbr = m.setdefault("pbrMetallicRoughness", {})
            pbr["metallicFactor"], pbr["roughnessFactor"] = 0.0, 1.0
            used.add("KHR_materials_unlit")
    if used:
        js["extensionsUsed"] = sorted(used)
    if scene_extras:
        js["scenes"][js.get("scene", 0)].setdefault("extras", {}).update(scene_extras)
    if extras:
        js.setdefault("asset", {}).setdefault("extras", {}).update(extras)
    raw = json.dumps(js, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    raw += b" " * ((4 - len(raw) % 4) % 4)
    out = struct.pack("<III", magic, ver, 12 + 8 + len(raw) + len(rest)) + struct.pack("<II", len(raw), jt) + raw + rest
    with open(path, "wb") as fh:
        fh.write(out)
    return js


def gltf_export(path, **kw):
    opts = dict(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                export_apply=False, export_texcoords=True, export_normals=True, export_materials="EXPORT",
                export_image_format="AUTO", export_cameras=False, export_lights=False, export_extras=True)
    opts.update(kw)
    bpy.ops.export_scene.gltf(**opts)


def select(objs, active):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


def scale_matrix():
    return Matrix.Scale(STUD_M, 4)
