"""
Deploy bo_morph.py to remote Windows Blender via client.py tunnel.
Usage: python3 deploy.py [--generate] [--preview INDEX]
  --generate  After deploying, auto-generate all presets on the active armature
  --preview N Preview morph at index N
"""
import sys
import os
import json
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'win_b'))
from client import SERVER


def send_code(code):
    data = {"type": "execute_code", "params": {"code": code}}
    body = json.dumps(data).encode()
    req = urllib.request.Request(SERVER, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def deploy():
    addon_path = os.path.join(os.path.dirname(__file__), 'bo_morph.py')
    with open(addon_path, 'r', encoding='utf-8') as f:
        addon_code = f.read()

    deploy_code = (
        "import bpy, sys\n"
        "mod_name = 'bo_morph_addon'\n"
        "if mod_name in sys.modules:\n"
        "    mod = sys.modules[mod_name]\n"
        "    if hasattr(mod, 'unregister'):\n"
        "        try: mod.unregister()\n"
        "        except: pass\n"
        "    del sys.modules[mod_name]\n"
        "import types\n"
        "mod = types.ModuleType(mod_name)\n"
        "sys.modules[mod_name] = mod\n"
        "exec(compile(SOURCE_CODE, 'bo_morph.py', 'exec'), mod.__dict__)\n"
        "if hasattr(mod, 'register'):\n"
        "    mod.register()\n"
        "print('bo_morph addon deployed and registered')\n"
    )

    full_code = f"SOURCE_CODE = {repr(addon_code)}\n{deploy_code}"
    result = send_code(full_code)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def generate_all():
    code = """
import bpy
arm = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE' and obj.parent and obj.parent.type == 'EMPTY':
        try:
            _ = obj.parent.mmd_root.name
            arm = obj
            break
        except:
            pass

if not arm:
    print("ERROR: No MMD armature found")
else:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    result = bpy.ops.bomp.generate_presets(category_filter="")
    mmd_root = arm.parent.mmd_root
    morphs = [(m.name, m.name_e, len(m.data)) for m in mmd_root.bone_morphs]
    print("Generated morphs:")
    for name, name_e, count in morphs:
        print(f"  {name} ({name_e}): {count} bones")
    print(f"Total: {len(morphs)} morphs")
"""
    result = send_code(code)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def preview_morph(index):
    code = f"""
import bpy
arm = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE' and obj.parent and obj.parent.type == 'EMPTY':
        try:
            _ = obj.parent.mmd_root.name
            arm = obj
            break
        except:
            pass

if arm:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.bomp.preview_morph(morph_index={index})
    morph = arm.parent.mmd_root.bone_morphs[{index}]
    print(f"Previewing: {{morph.name}}")
    for d in morph.data:
        print(f"  {{d.bone}}: loc={{list(d.location)}}, rot={{list(d.rotation)}}")
"""
    result = send_code(code)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


def clear_pose():
    code = """
import bpy
arm = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE' and obj.parent and obj.parent.type == 'EMPTY':
        try:
            _ = obj.parent.mmd_root.name
            arm = obj
            break
        except:
            pass
if arm:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.bomp.clear_pose()
    print("Pose cleared")
"""
    result = send_code(code)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    args = sys.argv[1:]

    print("=== Deploying bo_morph addon ===")
    deploy()

    if "--generate" in args:
        print("\n=== Generating all presets ===")
        generate_all()

    if "--preview" in args:
        idx = int(args[args.index("--preview") + 1])
        print(f"\n=== Previewing morph {idx} ===")
        preview_morph(idx)

    if "--clear" in args:
        print("\n=== Clearing pose ===")
        clear_pose()
