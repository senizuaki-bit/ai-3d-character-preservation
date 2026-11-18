"""Read-only examination of the open .blend (run with blender -b <file> --python this)."""
import bpy, os, json, sys

p = bpy.data.filepath
s = bpy.context.scene
out = {"file": os.path.basename(p), "bytes": os.path.getsize(p),
       "saved_by_version": list(bpy.data.version), "reader": bpy.app.version_string}

with open(p, "rb") as fh:
    raw = fh.read(64)
out["magic_hex"] = raw[:4].hex(" ")
if raw[:4] == b"\x28\xb5\x2f\xfd":
    out["compression"] = "zstd"
    try:
        import zstandard
        with open(p, "rb") as fh:
            r = zstandard.ZstdDecompressor().stream_reader(fh)
            out["decompressed_header"] = r.read(24).decode("latin-1")
    except Exception as e:
        out["decompressed_header"] = f"(could not decompress: {e!r})"
else:
    out["compression"] = "none"
    out["decompressed_header"] = raw[:24].decode("latin-1")

kinds = ["scenes", "collections", "objects", "meshes", "materials", "node_groups", "images", "lights",
         "cameras", "worlds", "actions", "texts", "libraries"]
out["datablocks"] = {k: len(getattr(bpy.data, k)) for k in kinds}
out["collections"] = {c.name: [o.name for o in c.objects] for c in bpy.data.collections}
out["images"] = [{"name": i.name, "size": list(i.size), "packed_bytes": i.packed_file.size if i.packed_file else None,
                  "filepath": i.filepath, "colorspace": i.colorspace_settings.name} for i in bpy.data.images]
out["external_paths"] = bpy.utils.blend_paths(absolute=False)
out["libraries"] = [l.filepath for l in bpy.data.libraries]

c = bpy.data.objects.get("Character")
if c:
    me = c.data
    mat = me.materials[0] if me.materials else None
    out["character"] = {
        "verts": len(me.vertices), "faces": len(me.polygons),
        "tris": sum(len(f.vertices) - 2 for f in me.polygons),
        "uv_layers": [u.name for u in me.uv_layers], "dims_m": [round(d, 4) for d in c.dimensions],
        "modifiers": [(m.name, m.type) for m in c.modifiers],
        "material": mat.name if mat else None,
        "material_nodes": len(mat.node_tree.nodes) if mat and mat.use_nodes else 0,
        "node_types": sorted({n.bl_idname for n in mat.node_tree.nodes}) if mat and mat.use_nodes else [],
        "custom_props": {k: c[k] for k in c.keys() if isinstance(c[k], (str, int, float))},
    }
out["scene_custom_props"] = {k: s[k] for k in s.keys() if isinstance(s[k], (str, int, float))}
r = s.render
out["render"] = {"engine": r.engine, "res": [r.resolution_x, r.resolution_y, r.resolution_percentage],
                 "samples": getattr(s.cycles, "samples", None), "device": getattr(s.cycles, "device", None),
                 "view_transform": s.view_settings.view_transform, "film_transparent": r.film_transparent,
                 "note": r.stamp_note_text if r.use_stamp_note else None}
out["units"] = {"system": s.unit_settings.system, "scale_length": s.unit_settings.scale_length}
out["lights"] = [(l.name, l.data.type, round(l.data.energy, 1)) for l in bpy.data.objects if l.type == "LIGHT"]
out["cameras"] = [o.name for o in bpy.data.objects if o.type == "CAMERA"]
out["world"] = s.world.name if s.world else None
out["use_autopack"] = bpy.data.use_autopack
print("EXAMINE " + json.dumps(out, ensure_ascii=False))
