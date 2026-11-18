"""Add author / rights metadata to the final .blend (scene and Character object custom properties).

  blender -b character_hunyuan3d_studio.blend --python add_blend_metadata.py

Also turns on the render "Note" metadata field, so renders saved as PNG carry the author in their
file metadata (not burned into the pixels). Nothing in the scene geometry, materials or lights changes.
"""
import bpy

META = {
    "author": "SUN HAOSONG",
    "copyright": "© 2026 SUN HAOSONG. All rights reserved.",
    "title": "Stylised cartoon boy - 3D character model",
    "description": "Tencent Hunyuan 3D (hy-3d-3.0) mesh, normalised to 1.4 m, with an enhanced "
                   "Principled BSDF and a #ECEFF4 studio light rig.",
    "source_model": "generated/hunyuan3d_v3_multiview_textured.glb",
    "source_model_sha256": "db572d97c9fcfeb240c00ef7409cf28f601dc5d2ebb98df440fb8c4b3af3b1ec",
    "source_model_created": "2026-11-18T19:38:23+08:00",
    "metadata_record": "generated/hunyuan3d_v3_multiview_textured.metadata.json",
}

scene = bpy.context.scene
targets = [scene] + [o for o in (bpy.data.objects.get("Character"),) if o]
for idb in targets:
    for k, v in META.items():
        idb[k] = v

r = scene.render
r.use_stamp_note = True
r.stamp_note_text = f"Author: {META['author']} | {META['copyright']}"
r.use_stamp = False  # metadata only, never drawn onto the image

try:
    bpy.ops.wm.save_mainfile(compress=True)
except TypeError:
    bpy.ops.wm.save_mainfile()
print("BLEND_META_OK", [t.name for t in targets], bpy.data.filepath, bpy.data.use_autopack)
