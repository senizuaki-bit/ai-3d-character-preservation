"""Re-save the master .blend without compression and make its metadata location-independent.

  blender -b character_hunyuan3d_studio.blend --python save_master_uncompressed.py

Uncompressed: the "BLENDER..." header is readable without decompression and damage to a few
bytes stays local. Paths in the metadata become file names, so they stay true wherever the
file is copied (laptop, GitHub, backups).
"""
import bpy

UPDATE = {
    "source_model": "hunyuan3d_v3_multiview_textured.glb",
    "metadata_record": "hunyuan3d_v3_multiview_textured.metadata.json",
    "workflow": "Photo of the author -> GPT Image 2.6 cartoon six-view sheet -> Tencent Hunyuan 3D 3.0 "
                "(front/back/left/right views) -> refined in Blender 5.3 with Claude (AI assistant)",
    "repository": "https://github.com/senizuaki-bit/ai-3d-character-preservation",
}
targets = [bpy.context.scene, bpy.data.objects["Character"]]
for idb in targets:
    for k, v in UPDATE.items():
        idb[k] = v
bpy.ops.wm.save_mainfile(compress=False)
with open(bpy.data.filepath, "rb") as fh:
    print("MASTER_SAVED", fh.read(17))
