"""Export the final character as an open-format GLB and time one full 1080p render (master is not saved).

  blender -b character_hunyuan3d_studio.blend --python export_glb_and_time_render.py -- <out.glb> <render.png>
"""
import bpy, json, os, sys, time

glb_out, png_out = sys.argv[sys.argv.index("--") + 1:][:2]
scene = bpy.context.scene

# --- open-format copy of the final model (Character only, modifiers applied, custom properties as glTF extras)
for o in bpy.context.view_layer.objects:
    o.select_set(o.name == "Character")
bpy.context.view_layer.objects.active = bpy.data.objects["Character"]
t0 = time.time()
bpy.ops.export_scene.gltf(filepath=glb_out, export_format='GLB', use_selection=True, export_apply=True,
                          export_extras=True, export_yup=True)
export_s = time.time() - t0

# --- time a full render with the file's own settings
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.get_devices()
devices = [d.name for d in prefs.devices if d.use]
scene.render.filepath = png_out
t0 = time.time()
bpy.ops.render.render(write_still=True)
render_s = time.time() - t0

print("TIMING " + json.dumps({
    "export_s": round(export_s, 1), "glb_bytes": os.path.getsize(glb_out),
    "render_s": round(render_s, 1), "device_type": prefs.compute_device_type, "scene_device": scene.cycles.device,
    "devices": devices, "samples": scene.cycles.samples,
    "res": [scene.render.resolution_x, scene.render.resolution_y],
}))
