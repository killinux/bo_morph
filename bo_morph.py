bl_info = {
    "name": "PMX Bone Morph Generator",
    "author": "bo_morph",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > MMD Morph",
    "description": "Generate bone morphs for PMX models with auto-calibrated presets",
    "category": "Animation",
}

import bpy
import math
from bpy.types import Operator, Panel
from mathutils import Vector, Quaternion

# ================================================================
# Bone Name Mapping: canonical_key -> list of possible names
# Tried in order: XPS English, Japanese MMD, Blender .L/.R convention
# ================================================================
BONE_NAME_MAP = {
    "eyelid_upper_L": ["head eyelid upper left", "左目上", "目上.L"],
    "eyelid_upper_R": ["head eyelid upper right", "右目上", "目上.R"],
    "eyelid_lower_L": ["head eyelid lower left", "左目下", "目下.L"],
    "eyelid_lower_R": ["head eyelid lower right", "右目下", "目下.R"],
    "eyeball_L": ["head eyeball left", "左目", "目.L"],
    "eyeball_R": ["head eyeball right", "右目", "目.R"],
    "eyebrow_root_L": ["head eyebrow left root", "左眉根", "眉根.L"],
    "eyebrow_1_L": ["head eyebrow left 1", "左眉1", "眉1.L"],
    "eyebrow_2_L": ["head eyebrow left 2", "左眉2", "眉2.L"],
    "eyebrow_3_L": ["head eyebrow left 3", "左眉3", "眉3.L"],
    "eyebrow_root_R": ["head eyebrow right root", "右眉根", "眉根.R"],
    "eyebrow_1_R": ["head eyebrow right 1", "右眉1", "眉1.R"],
    "eyebrow_2_R": ["head eyebrow right 2", "右眉2", "眉2.R"],
    "eyebrow_3_R": ["head eyebrow right 3", "右眉3", "眉3.R"],
    "cheek_L": ["head cheek left 1", "head cheek left", "左ほほ", "ほほ.L"],
    "cheek_R": ["head cheek right 1", "head cheek right", "右ほほ", "ほほ.R"],
    "lip_upper_L": ["head lip upper left", "上唇左", "上唇.L"],
    "lip_upper_R": ["head lip upper right", "上唇右", "上唇.R"],
    "lip_upper_mid": ["head lip upper middle", "上唇中", "上唇"],
    "lip_lower_L": ["head lip lower left", "下唇左", "下唇.L"],
    "lip_lower_R": ["head lip lower right", "下唇右", "下唇.R"],
    "lip_lower_mid": ["head lip lower middle", "下唇中", "下唇"],
    "mouth_corner_L": ["head mouth corner left", "左口角", "口角.L"],
    "mouth_corner_R": ["head mouth corner right", "右口角", "口角.R"],
    "jaw": ["head jaw", "あご", "顎", "下あご"],
    "tongue_1": ["head tongue 1", "舌1", "舌"],
    "tongue_2": ["head tongue 2", "舌2"],
    "tongue_3": ["head tongue 3", "舌3"],
    "nose_L": ["head nose nostril left", "左鼻", "鼻.L"],
    "nose_R": ["head nose nostril right", "右鼻", "鼻.R"],
}

# Reference bone lengths from Inase54 model (for calibration)
REF_BONE_LENGTHS = {
    "eyelid_upper_L": 0.477, "eyelid_upper_R": 0.454,
    "eyelid_lower_L": 0.477, "eyelid_lower_R": 0.454,
    "eyeball_L": 0.484, "eyeball_R": 0.460,
    "jaw": 0.633,
    "mouth_corner_L": 0.546, "mouth_corner_R": 0.533,
    "cheek_L": 0.500, "cheek_R": 0.471,
    "eyebrow_root_L": 0.063, "eyebrow_root_R": 0.063,
    "eyebrow_1_L": 0.231, "eyebrow_1_R": 0.231,
    "eyebrow_2_L": 0.063, "eyebrow_2_R": 0.063,
    "eyebrow_3_L": 0.244, "eyebrow_3_R": 0.244,
    "lip_upper_L": 0.485, "lip_upper_R": 0.477,
    "lip_upper_mid": 0.475,
    "lip_lower_L": 0.224, "lip_lower_R": 0.224,
    "lip_lower_mid": 0.218,
    "tongue_1": 0.242, "tongue_2": 0.230, "tongue_3": 0.230,
    "nose_L": 0.330, "nose_R": 0.315,
}
REF_INTER_EYE = 0.726

# ================================================================
# Expression Presets
# Each bone entry: (semantic_axis, angle_degrees, (loc_x, loc_y, loc_z))
# semantic_axis: "close" = around world X, "lateral" = around world Z
# Positive close angle = downward for bones facing forward
# ================================================================
EXPRESSION_PRESETS = {
    "まばたき": {
        "name_e": "Blink", "category": "EYE",
        "bones": {
            "eyelid_upper_L": ("close", 7.0, 0.11),
            "eyelid_upper_R": ("close", 7.0, 0.11),
            "eyelid_lower_L": ("close", 2.0, -0.04),
            "eyelid_lower_R": ("close", 2.0, -0.04),
            "eyeball_L": ("close", 0.0, (-0.039, 0.003, -0.031)),
            "eyeball_R": ("close", 0.0, (0.038, 0.003, -0.033)),
        },
    },
    "笑い": {
        "name_e": "Smile", "category": "EYE",
        "bones": {
            "eyelid_upper_L": ("close", 5.0, 0.06),
            "eyelid_upper_R": ("close", 5.0, 0.06),
            "eyelid_lower_L": ("close", -5.0, -0.14),
            "eyelid_lower_R": ("close", -5.0, -0.14),
            "eyeball_L": ("close", 0.0, (-0.039, 0.003, -0.031)),
            "eyeball_R": ("close", 0.0, (0.038, 0.003, -0.033)),
            "cheek_L": ("close", -5.0, -0.05),
            "cheek_R": ("close", -5.0, -0.05),
            "mouth_corner_L": ("close", -5.0, (0, 0, 0)),
            "mouth_corner_R": ("close", -5.0, (0, 0, 0)),
        },
    },
    "ウィンク": {
        "name_e": "Wink", "category": "EYE",
        "bones": {
            "eyelid_upper_L": ("close", 8.0, 0.13),
            "eyelid_lower_L": ("close", -4.0, -0.04),
        },
    },
    "ウィンク右": {
        "name_e": "Wink_R", "category": "EYE",
        "bones": {
            "eyelid_upper_R": ("close", 8.0, 0.13),
            "eyelid_lower_R": ("close", -4.0, -0.04),
        },
    },
    "ウィンク２": {
        "name_e": "Wink2", "category": "EYE",
        "bones": {
            "eyelid_upper_L": ("close", 5.0, 0.07),
            "eyelid_lower_L": ("close", -8.0, -0.12),
        },
    },
    "ウィンク２右": {
        "name_e": "Wink2_R", "category": "EYE",
        "bones": {
            "eyelid_upper_R": ("close", 5.0, 0.07),
            "eyelid_lower_R": ("close", -8.0, -0.12),
        },
    },
    "あ": {
        "name_e": "A", "category": "MOUTH",
        "bones": {
            "jaw": ("close", 15.0, (0, 0, 0)),
            "lip_upper_mid": ("close", -3.0, (0, 0, 0)),
            "lip_upper_L": ("close", -2.0, (0, 0, 0)),
            "lip_upper_R": ("close", -2.0, (0, 0, 0)),
            "lip_lower_mid": ("close", 2.0, (0, 0, 0)),
            "lip_lower_L": ("close", 1.5, (0, 0, 0)),
            "lip_lower_R": ("close", 1.5, (0, 0, 0)),
            "mouth_corner_L": ("close", -2.0, (0, 0, 0)),
            "mouth_corner_R": ("close", -2.0, (0, 0, 0)),
        },
    },
    "い": {
        "name_e": "I", "category": "MOUTH",
        "bones": {
            "jaw": ("close", 4.0, (0, 0, 0)),
            "mouth_corner_L": ("lateral", 8.0, (0, 0, 0)),
            "mouth_corner_R": ("lateral", -8.0, (0, 0, 0)),
            "lip_upper_L": ("lateral", 3.0, (0, 0, 0)),
            "lip_upper_R": ("lateral", -3.0, (0, 0, 0)),
            "lip_lower_L": ("lateral", 3.0, (0, 0, 0)),
            "lip_lower_R": ("lateral", -3.0, (0, 0, 0)),
        },
    },
    "う": {
        "name_e": "U", "category": "MOUTH",
        "bones": {
            "jaw": ("close", 5.0, (0, 0, 0)),
            "mouth_corner_L": ("lateral", -6.0, (0, 0, 0)),
            "mouth_corner_R": ("lateral", 6.0, (0, 0, 0)),
            "lip_upper_mid": ("close", -2.0, (0, -0.015, 0)),
            "lip_lower_mid": ("close", 2.0, (0, -0.01, 0)),
            "lip_upper_L": ("lateral", -2.0, (0, -0.01, 0)),
            "lip_upper_R": ("lateral", 2.0, (0, -0.01, 0)),
            "lip_lower_L": ("lateral", -2.0, (0, -0.008, 0)),
            "lip_lower_R": ("lateral", 2.0, (0, -0.008, 0)),
        },
    },
    "え": {
        "name_e": "E", "category": "MOUTH",
        "bones": {
            "jaw": ("close", 7.0, (0, 0, 0)),
            "lip_upper_mid": ("close", -2.5, (0, 0, 0)),
            "lip_lower_mid": ("close", 1.5, (0, 0, 0)),
            "mouth_corner_L": ("lateral", 4.0, (0, 0, 0)),
            "mouth_corner_R": ("lateral", -4.0, (0, 0, 0)),
        },
    },
    "お": {
        "name_e": "O", "category": "MOUTH",
        "bones": {
            "jaw": ("close", 10.0, (0, 0, 0)),
            "lip_upper_mid": ("close", -4.0, (0, -0.008, 0)),
            "lip_lower_mid": ("close", 2.5, (0, 0, 0)),
            "mouth_corner_L": ("lateral", -4.0, (0, 0, 0)),
            "mouth_corner_R": ("lateral", 4.0, (0, 0, 0)),
            "lip_upper_L": ("lateral", -2.0, (0, -0.005, 0)),
            "lip_upper_R": ("lateral", 2.0, (0, -0.005, 0)),
            "lip_lower_L": ("lateral", -2.0, (0, 0, 0)),
            "lip_lower_R": ("lateral", 2.0, (0, 0, 0)),
        },
    },
    "上": {
        "name_e": "Brows_Up", "category": "EYEBROW",
        "bones": {
            "eyebrow_root_L": ("close", -10.0, (0, 0, 0.01)),
            "eyebrow_root_R": ("close", -10.0, (0, 0, 0.01)),
            "eyebrow_1_L": ("close", -6.0, (0, 0, 0.008)),
            "eyebrow_1_R": ("close", -6.0, (0, 0, 0.008)),
            "eyebrow_2_L": ("close", -5.0, (0, 0, 0.006)),
            "eyebrow_2_R": ("close", -5.0, (0, 0, 0.006)),
            "eyebrow_3_L": ("close", -4.0, (0, 0, 0.004)),
            "eyebrow_3_R": ("close", -4.0, (0, 0, 0.004)),
        },
    },
    "下": {
        "name_e": "Brows_Down", "category": "EYEBROW",
        "bones": {
            "eyebrow_root_L": ("close", 8.0, (0, 0, -0.008)),
            "eyebrow_root_R": ("close", 8.0, (0, 0, -0.008)),
            "eyebrow_1_L": ("close", 5.0, (0, 0, -0.006)),
            "eyebrow_1_R": ("close", 5.0, (0, 0, -0.006)),
            "eyebrow_2_L": ("close", 4.0, (0, 0, -0.004)),
            "eyebrow_2_R": ("close", 4.0, (0, 0, -0.004)),
            "eyebrow_3_L": ("close", 3.0, (0, 0, -0.003)),
            "eyebrow_3_R": ("close", 3.0, (0, 0, -0.003)),
        },
    },
    "怒り": {
        "name_e": "Brows_Angry", "category": "EYEBROW",
        "bones": {
            "eyebrow_root_L": ("close", 12.0, (0, 0, -0.01)),
            "eyebrow_root_R": ("close", 12.0, (0, 0, -0.01)),
            "eyebrow_1_L": ("close", 6.0, (0, 0, -0.005)),
            "eyebrow_1_R": ("close", 6.0, (0, 0, -0.005)),
            "eyebrow_2_L": ("close", -2.0, (0, 0, 0.002)),
            "eyebrow_2_R": ("close", -2.0, (0, 0, 0.002)),
            "eyebrow_3_L": ("close", -7.0, (0, 0, 0.006)),
            "eyebrow_3_R": ("close", -7.0, (0, 0, 0.006)),
        },
    },
    "困る": {
        "name_e": "Brows_Sad", "category": "EYEBROW",
        "bones": {
            "eyebrow_root_L": ("close", -12.0, (0, 0, 0.012)),
            "eyebrow_root_R": ("close", -12.0, (0, 0, 0.012)),
            "eyebrow_1_L": ("close", -6.0, (0, 0, 0.006)),
            "eyebrow_1_R": ("close", -6.0, (0, 0, 0.006)),
            "eyebrow_2_L": ("close", 3.0, (0, 0, -0.003)),
            "eyebrow_2_R": ("close", 3.0, (0, 0, -0.003)),
            "eyebrow_3_L": ("close", 8.0, (0, 0, -0.007)),
            "eyebrow_3_R": ("close", 8.0, (0, 0, -0.007)),
        },
    },
    "にやり": {
        "name_e": "Grin", "category": "MOUTH",
        "bones": {
            "mouth_corner_L": ("close", -10.0, (0, 0, 0)),
            "mouth_corner_R": ("close", -10.0, (0, 0, 0)),
            "lip_upper_L": ("lateral", -2.0, (0, 0, 0)),
            "lip_upper_R": ("lateral", 2.0, (0, 0, 0)),
        },
    },
    "∧": {
        "name_e": "Mouth_Cat", "category": "MOUTH",
        "bones": {
            "mouth_corner_L": ("close", -12.0, (0, 0, 0)),
            "mouth_corner_R": ("close", -12.0, (0, 0, 0)),
            "lip_upper_mid": ("close", 5.0, (0, 0.01, 0)),
            "lip_lower_mid": ("close", -3.0, (0, 0, 0)),
        },
    },
    "べー": {
        "name_e": "Tongue_Out", "category": "MOUTH",
        "bones": {
            "jaw": ("close", 5.0, (0, 0, 0)),
            "tongue_1": ("close", -15.0, (0, 0, 0)),
            "tongue_2": ("close", -10.0, (0, 0, 0)),
            "tongue_3": ("close", -5.0, (0, -0.015, 0)),
        },
    },
}


# ================================================================
# Utility Functions
# ================================================================

def resolve_bone_name(armature, canonical_key):
    names = BONE_NAME_MAP.get(canonical_key)
    if not names:
        return None
    bones = armature.data.bones
    for name in names:
        if name in bones:
            return name
    for name in names:
        name_clean = name.lower().replace(" ", "").replace("_", "")
        for b in bones:
            if b.name.lower().replace(" ", "").replace("_", "") == name_clean:
                return b.name
    return None


def find_mmd_root(obj):
    current = obj
    while current:
        if current.type == 'EMPTY' and hasattr(current, 'mmd_root'):
            try:
                _ = current.mmd_root.name
                return current
            except:
                pass
        current = current.parent
    if obj and obj.type == 'ARMATURE' and obj.parent:
        return find_mmd_root(obj.parent)
    return None


# ================================================================
# Auto-Calibrate Blink: curve fitting upper eyelid to lower eyelid
# ================================================================

def _get_eyelid_boundary(mesh, eval_mesh, vg_name, mode="upper"):
    """Extract the edge of an eyelid (the row of vertices closest to the eye opening)."""
    vg = mesh.vertex_groups.get(vg_name)
    if not vg:
        return []
    bins = {}
    for v in mesh.data.vertices:
        for g in v.groups:
            if g.group == vg.index and g.weight > 0.05:
                pos = eval_mesh.matrix_world @ eval_mesh.data.vertices[v.index].co
                x_bin = round(pos.x * 50) / 50
                if x_bin not in bins:
                    bins[x_bin] = []
                bins[x_bin].append((v.index, g.weight, pos.x, pos.y, pos.z))
    boundary = []
    for x_bin in sorted(bins.keys()):
        group = bins[x_bin]
        if mode == "upper":
            best = min(group, key=lambda v: v[4])
        else:
            best = max(group, key=lambda v: v[4])
        boundary.append(best)
    return boundary


def auto_calibrate_blink(armature, upper_bone_name, lower_bone_name):
    """Find optimal (rotation, translation) for upper eyelid to align with lower eyelid.

    Returns (rot_degrees, trans_units) or None if bones/mesh not found.
    Works on any model with eyelid bones and weighted mesh.
    """
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == armature]
    if not meshes:
        return None

    bone = armature.data.bones.get(upper_bone_name)
    if not bone:
        return None

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    for pb in armature.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()

    upper_edge = []
    lower_edge = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for mesh_obj in meshes:
        eval_m = mesh_obj.evaluated_get(depsgraph)
        upper_edge += _get_eyelid_boundary(mesh_obj, eval_m, upper_bone_name, "upper")
        lower_edge += _get_eyelid_boundary(mesh_obj, eval_m, lower_bone_name, "lower")

    if len(upper_edge) < 3 or len(lower_edge) < 3:
        return None

    bone_head = Vector(bone.head_local)
    mat = bone.matrix_local.to_3x3()
    bone_dir = (mat @ Vector((0, 1, 0))).normalized()
    close_world = Vector((0, 0, -1))
    rot_axis_world = bone_dir.cross(close_world)
    if rot_axis_world.length < 0.001:
        return None
    rot_axis_world.normalize()

    best_cost = 999
    best_params = (0, 0)
    for rot_deg in range(-15, 20):
        for trans_100 in range(0, 30):
            trans = trans_100 / 100.0
            total_dist = 0
            for _, w, vx, vy, vz in upper_edge:
                dz_t = close_world.z * trans * w
                dy_t = close_world.y * trans * w
                dx_t = close_world.x * trans * w
                rel = Vector((vx, vy, vz)) - bone_head
                q = Quaternion(rot_axis_world, math.radians(rot_deg * w))
                rotated = q @ rel
                nx = vx + dx_t + rotated.x - rel.x
                ny = vy + dy_t + rotated.y - rel.y
                nz = vz + dz_t + rotated.z - rel.z
                min_d = min(math.sqrt((nx-lx)**2 + (ny-ly)**2 + (nz-lz)**2)
                           for _, _, lx, ly, lz in lower_edge)
                total_dist += min_d
            avg = total_dist / len(upper_edge)
            if avg < best_cost:
                best_cost = avg
                best_params = (rot_deg, trans)

    return best_params[0], best_params[1], best_cost


def auto_calibrate_all_blinks(armature):
    """Auto-calibrate blink parameters for all eyelid bone pairs found on the model.

    Returns dict: {
        "eyelid_upper_L": (rot, trans, cost),
        "eyelid_upper_R": (rot, trans, cost),
    }
    """
    results = {}
    pairs = [
        ("eyelid_upper_L", "eyelid_lower_L"),
        ("eyelid_upper_R", "eyelid_lower_R"),
    ]
    for upper_key, lower_key in pairs:
        upper_name = resolve_bone_name(armature, upper_key)
        lower_name = resolve_bone_name(armature, lower_key)
        if upper_name and lower_name:
            result = auto_calibrate_blink(armature, upper_name, lower_name)
            if result:
                results[upper_key] = result
    return results


def compute_rotation(armature, bone_name, semantic_axis, angle_degrees):
    bone = armature.data.bones.get(bone_name)
    if not bone:
        return Quaternion((1, 0, 0, 0))

    mat = bone.matrix_local.to_3x3()
    bone_dir = (mat @ Vector((0, 1, 0))).normalized()

    if semantic_axis == "close":
        desired_motion = Vector((0, 0, -1))
    elif semantic_axis == "lateral":
        desired_motion = Vector((1, 0, 0))
    else:
        desired_motion = Vector((0, 0, -1))

    rot_axis_world = bone_dir.cross(desired_motion)
    if rot_axis_world.length < 0.001:
        rot_axis_world = Vector((1, 0, 0))
    rot_axis_world.normalize()

    rot_axis_local = (mat.inverted() @ rot_axis_world).normalized()
    angle_rad = math.radians(angle_degrees)

    return Quaternion(rot_axis_local, angle_rad)


# ================================================================
# Calibrator
# ================================================================

class BoneMorphCalibrator:
    def __init__(self, armature):
        self.armature = armature
        self._scale = None

    def _get_inter_eye_dist(self):
        bones = self.armature.data.bones
        for names_l, names_r in [
            (BONE_NAME_MAP.get("eyeball_L", []), BONE_NAME_MAP.get("eyeball_R", [])),
            (BONE_NAME_MAP.get("eyelid_upper_L", []), BONE_NAME_MAP.get("eyelid_upper_R", [])),
        ]:
            bl = br = None
            for n in names_l:
                if n in bones:
                    bl = bones[n]; break
            for n in names_r:
                if n in bones:
                    br = bones[n]; break
            if bl and br:
                return (bl.head_local - br.head_local).length
        return None

    def scale_factor(self):
        if self._scale is None:
            dist = self._get_inter_eye_dist()
            self._scale = REF_INTER_EYE / dist if dist and dist > 0.001 else 1.0
        return self._scale

    def calibrated_angle(self, base_angle, bone_key):
        bone_name = resolve_bone_name(self.armature, bone_key)
        if not bone_name:
            return base_angle * self.scale_factor()
        bone = self.armature.data.bones.get(bone_name)
        if not bone:
            return base_angle * self.scale_factor()
        ref_len = REF_BONE_LENGTHS.get(bone_key)
        if ref_len and bone.length > 0.001:
            return base_angle * (ref_len / bone.length)
        return base_angle * self.scale_factor()

    def calibrated_location(self, loc):
        s = self.scale_factor()
        return (loc[0] * s, loc[1] * s, loc[2] * s)


# ================================================================
# Generator
# ================================================================

class BoneMorphGenerator:
    def __init__(self, mmd_root_obj, armature):
        self.root_obj = mmd_root_obj
        self.mmd_root = mmd_root_obj.mmd_root
        self.armature = armature
        self.calibrator = BoneMorphCalibrator(armature)

    def _set_category(self, morph, cat_str):
        cat_map = {"LIP": "MOUTH", "MOUTH": "MOUTH"}
        cat = cat_map.get(cat_str, cat_str)
        try:
            morph.category = cat
        except TypeError:
            for alt in [cat_str, "OTHER"]:
                try:
                    morph.category = alt
                    return
                except TypeError:
                    continue

    def _compute_semantic_location(self, bone_name, sem_axis, magnitude):
        bone = self.armature.data.bones.get(bone_name)
        if not bone or abs(magnitude) < 1e-6:
            return (0, 0, 0)
        mat_inv = bone.matrix_local.to_3x3().inverted()
        if sem_axis == "close":
            world_dir = Vector((0, 0, -1))
        elif sem_axis == "lateral":
            world_dir = Vector((1, 0, 0))
        else:
            world_dir = Vector((0, 0, -1))
        local_offset = mat_inv @ (world_dir * magnitude)
        return tuple(local_offset)

    def create_morph(self, jp_name, en_name, category, bone_transforms):
        existing = None
        for m in self.mmd_root.bone_morphs:
            if m.name == jp_name:
                existing = m
                break

        if existing:
            existing.data.clear()
            morph = existing
        else:
            morph = self.mmd_root.bone_morphs.add()
            morph.name = jp_name

        morph.name_e = en_name
        self._set_category(morph, category)

        count = 0
        for bone_key, (sem_axis, base_angle, loc) in bone_transforms.items():
            actual_name = resolve_bone_name(self.armature, bone_key)
            if not actual_name:
                continue

            cal_angle = self.calibrator.calibrated_angle(base_angle, bone_key)
            quat = compute_rotation(self.armature, actual_name, sem_axis, cal_angle)

            if quat.w < 0:
                quat = Quaternion((-quat.w, -quat.x, -quat.y, -quat.z))

            if isinstance(loc, (int, float)):
                cal_loc = self._compute_semantic_location(
                    actual_name, sem_axis, loc * self.calibrator.scale_factor())
            else:
                cal_loc = self.calibrator.calibrated_location(loc)

            item = morph.data.add()
            item.bone = actual_name
            item.location = cal_loc
            item.rotation = (quat.w, quat.x, quat.y, quat.z)
            count += 1

        return count

    def generate_presets(self, category_filter=None, auto_blink=True):
        if auto_blink:
            self._apply_auto_blink()

        created = []
        skipped = []
        for jp_name, preset in EXPRESSION_PRESETS.items():
            if category_filter and preset["category"] != category_filter:
                continue
            n = self.create_morph(jp_name, preset["name_e"], preset["category"], preset["bones"])
            if n > 0:
                created.append(jp_name)
            else:
                skipped.append(jp_name)
        return created, skipped

    def _apply_auto_blink(self):
        """Override blink preset values with auto-calibrated optimal parameters."""
        cal = auto_calibrate_all_blinks(self.armature)
        if not cal:
            return

        eyeball_loc_L = (-0.039, 0.003, -0.031)
        eyeball_loc_R = (0.038, 0.003, -0.033)

        blink_morphs = ["まばたき", "ウィンク", "ウィンク右"]
        for morph_name in blink_morphs:
            preset = EXPRESSION_PRESETS.get(morph_name)
            if not preset:
                continue
            bones = dict(preset["bones"])
            for key in ["eyelid_upper_L", "eyelid_upper_R"]:
                if key in bones and key in cal:
                    rot, trans, cost = cal[key]
                    bones[key] = ("close", rot, trans)
            preset["bones"] = bones

    def register_in_display(self):
        frames = self.mmd_root.display_item_frames
        expr_frame = None
        for f in frames:
            if f.name == "表情":
                expr_frame = f
                break
        if not expr_frame:
            expr_frame = frames.add()
            expr_frame.name = "表情"

        existing = set()
        for item in expr_frame.data:
            existing.add(getattr(item, 'name', ''))

        added = 0
        for morph in self.mmd_root.bone_morphs:
            if morph.name not in existing:
                item = expr_frame.data.add()
                item.type = 'MORPH'
                item.name = morph.name
                try:
                    item.morph_type = 'bone_morphs'
                except:
                    pass
                added += 1
        return added


# ================================================================
# Operators
# ================================================================

class BOMP_OT_auto_calibrate_blink(Operator):
    bl_idname = "bomp.auto_calibrate_blink"
    bl_label = "Auto-Calibrate Blink"
    bl_description = "Find optimal blink parameters by fitting upper eyelid curve to lower eyelid"
    bl_options = {'REGISTER'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an armature")
            return {'CANCELLED'}

        results = auto_calibrate_all_blinks(obj)
        if not results:
            self.report({'WARNING'}, "No eyelid bones found")
            return {'CANCELLED'}

        for key, (rot, trans, cost) in results.items():
            self.report({'INFO'}, "%s: rot=%.1f, trans=%.3f, dist=%.4f" % (key, rot, trans, cost))
        return {'FINISHED'}


class BOMP_OT_generate_presets(Operator):
    bl_idname = "bomp.generate_presets"
    bl_label = "Generate Bone Morph Presets"
    bl_options = {'REGISTER', 'UNDO'}

    category_filter: bpy.props.StringProperty(default="")

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an armature")
            return {'CANCELLED'}

        root = find_mmd_root(obj)
        if not root:
            self.report({'ERROR'}, "No MMD model root found")
            return {'CANCELLED'}

        gen = BoneMorphGenerator(root, obj)
        cat = self.category_filter if self.category_filter else None
        created, skipped = gen.generate_presets(cat)
        gen.register_in_display()

        self.report({'INFO'}, f"Created {len(created)} morphs, skipped {len(skipped)}")
        return {'FINISHED'}


class BOMP_OT_capture_pose(Operator):
    bl_idname = "bomp.capture_pose"
    bl_label = "Capture Pose as Bone Morph"
    bl_options = {'REGISTER', 'UNDO'}

    morph_name: bpy.props.StringProperty(name="Name (JP)", default="新規モーフ")
    morph_name_e: bpy.props.StringProperty(name="Name (EN)", default="NewMorph")
    morph_category: bpy.props.EnumProperty(
        name="Category",
        items=[
            ('EYE', "目 (Eye)", ""),
            ('EYEBROW', "眉 (Eyebrow)", ""),
            ('MOUTH', "口 (Mouth)", ""),
            ('OTHER', "その他 (Other)", ""),
        ],
        default='OTHER',
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an armature")
            return {'CANCELLED'}

        root = find_mmd_root(obj)
        if not root:
            self.report({'ERROR'}, "No MMD model root found")
            return {'CANCELLED'}

        mmd_root = root.mmd_root
        morph = mmd_root.bone_morphs.add()
        morph.name = self.morph_name
        morph.name_e = self.morph_name_e
        try:
            morph.category = self.morph_category
        except TypeError:
            morph.category = 'OTHER'

        captured = 0
        for pb in obj.pose.bones:
            loc = pb.location.copy()
            if pb.rotation_mode == 'QUATERNION':
                rot = pb.rotation_quaternion.copy()
            else:
                rot = pb.matrix_basis.to_quaternion()

            has_loc = loc.length > 1e-5
            has_rot = abs(rot.w - 1.0) > 1e-5 or Vector((rot.x, rot.y, rot.z)).length > 1e-5

            if has_loc or has_rot:
                item = morph.data.add()
                item.bone = pb.name
                item.location = tuple(loc)
                item.rotation = (rot.w, rot.x, rot.y, rot.z)
                captured += 1

        gen = BoneMorphGenerator(root, obj)
        gen.register_in_display()

        self.report({'INFO'}, f"Captured {captured} bones into '{self.morph_name}'")
        return {'FINISHED'}


class BOMP_OT_preview_morph(Operator):
    bl_idname = "bomp.preview_morph"
    bl_label = "Preview Bone Morph"
    bl_options = {'REGISTER', 'UNDO'}

    morph_index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            return {'CANCELLED'}

        root = find_mmd_root(obj)
        if not root:
            return {'CANCELLED'}

        mmd_root = root.mmd_root
        if self.morph_index < 0 or self.morph_index >= len(mmd_root.bone_morphs):
            return {'CANCELLED'}

        for pb in obj.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = (1, 0, 0, 0)

        morph = mmd_root.bone_morphs[self.morph_index]
        for item in morph.data:
            pb = obj.pose.bones.get(item.bone)
            if not pb:
                continue
            pb.rotation_mode = 'QUATERNION'
            pb.rotation_quaternion = Quaternion(item.rotation)
            pb.location = Vector(item.location)

        context.view_layer.update()
        self.report({'INFO'}, f"Preview: {morph.name}")
        return {'FINISHED'}


class BOMP_OT_clear_pose(Operator):
    bl_idname = "bomp.clear_pose"
    bl_label = "Clear Pose"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'ARMATURE':
            for pb in obj.pose.bones:
                pb.location = (0, 0, 0)
                pb.rotation_quaternion = (1, 0, 0, 0)
                pb.rotation_euler = (0, 0, 0)
                pb.scale = (1, 1, 1)
            context.view_layer.update()
        return {'FINISHED'}


class BOMP_OT_delete_morph(Operator):
    bl_idname = "bomp.delete_morph"
    bl_label = "Delete Bone Morph"
    bl_options = {'REGISTER', 'UNDO'}

    morph_index: bpy.props.IntProperty(default=-1)

    def execute(self, context):
        obj = context.active_object
        root = find_mmd_root(obj) if obj else None
        if not root:
            return {'CANCELLED'}
        mmd_root = root.mmd_root
        if 0 <= self.morph_index < len(mmd_root.bone_morphs):
            name = mmd_root.bone_morphs[self.morph_index].name
            mmd_root.bone_morphs.remove(self.morph_index)
            self.report({'INFO'}, f"Deleted: {name}")
        return {'FINISHED'}


# ================================================================
# UI Panels
# ================================================================

class BOMP_PT_main_panel(Panel):
    bl_label = "Bone Morph Generator"
    bl_idname = "BOMP_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MMD Morph"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        if not obj or obj.type != 'ARMATURE':
            layout.label(text="Select an armature", icon='ERROR')
            return

        box = layout.box()
        box.label(text=f"Armature: {obj.name}", icon='ARMATURE_DATA')
        box.label(text=f"Bones: {len(obj.data.bones)}")

        root = find_mmd_root(obj)
        if root:
            mmd_root = root.mmd_root
            box.label(text=f"MMD Root: {root.name}")
            box.label(text=f"Bone Morphs: {len(mmd_root.bone_morphs)}")

            detected = sum(1 for k in BONE_NAME_MAP if resolve_bone_name(obj, k))
            box.label(text=f"Facial Bones: {detected}/{len(BONE_NAME_MAP)}")
        else:
            box.label(text="No MMD Root found", icon='ERROR')


class BOMP_PT_presets_panel(Panel):
    bl_label = "Expression Presets"
    bl_idname = "BOMP_PT_presets"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MMD Morph"
    bl_parent_id = "BOMP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE' or not find_mmd_root(obj):
            layout.label(text="Select MMD armature")
            return

        col = layout.column(align=True)
        op = col.operator("bomp.generate_presets", text="Generate All", icon='ADD')
        op.category_filter = ""

        col.operator("bomp.auto_calibrate_blink", text="Auto-Calibrate Blink", icon='VIEWZOOM')

        row = col.row(align=True)
        op = row.operator("bomp.generate_presets", text="Eye")
        op.category_filter = "EYE"
        op = row.operator("bomp.generate_presets", text="Mouth")
        op.category_filter = "MOUTH"
        op = row.operator("bomp.generate_presets", text="Brow")
        op.category_filter = "EYEBROW"


class BOMP_PT_morphs_panel(Panel):
    bl_label = "Bone Morphs"
    bl_idname = "BOMP_PT_morphs"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MMD Morph"
    bl_parent_id = "BOMP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        root = find_mmd_root(obj) if obj and obj.type == 'ARMATURE' else None
        if not root:
            return

        mmd_root = root.mmd_root
        if not mmd_root.bone_morphs:
            layout.label(text="No bone morphs yet")
            return

        for i, m in enumerate(mmd_root.bone_morphs):
            row = layout.row(align=True)
            row.label(text=f"{m.name} ({len(m.data)})")
            op = row.operator("bomp.preview_morph", text="", icon='PLAY')
            op.morph_index = i
            op = row.operator("bomp.delete_morph", text="", icon='X')
            op.morph_index = i

        layout.separator()
        layout.operator("bomp.clear_pose", text="Reset Pose", icon='LOOP_BACK')


class BOMP_PT_capture_panel(Panel):
    bl_label = "Manual Capture"
    bl_idname = "BOMP_PT_capture"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MMD Morph"
    bl_parent_id = "BOMP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator("bomp.capture_pose", icon='REC')
        col.operator("bomp.clear_pose", icon='LOOP_BACK')


# ================================================================
# Registration
# ================================================================

classes = (
    BOMP_OT_auto_calibrate_blink,
    BOMP_OT_generate_presets,
    BOMP_OT_capture_pose,
    BOMP_OT_preview_morph,
    BOMP_OT_clear_pose,
    BOMP_OT_delete_morph,
    BOMP_PT_main_panel,
    BOMP_PT_presets_panel,
    BOMP_PT_morphs_panel,
    BOMP_PT_capture_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass


if __name__ == "__main__":
    register()
