"""Read-only inspection of a GLB (glTF 2.0 binary) file: header, JSON chunk, meshes, materials, embedded images."""
import json
import struct
import sys
import zipfile
import hashlib
import os


def png_size(b):
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", b[16:24])
        bit_depth, color_type = b[24], b[25]
        return f"PNG {w}x{h}, bit depth {bit_depth}, colour type {color_type}"
    if b[:2] == b"\xff\xd8":
        i = 2
        while i < len(b):
            if b[i] != 0xFF:
                i += 1
                continue
            marker = b[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", b[i + 5:i + 9])
                return f"JPEG {w}x{h}"
            seg = struct.unpack(">H", b[i + 2:i + 4])[0]
            i += 2 + seg
        return "JPEG (size not found)"
    return f"unknown magic {b[:8]!r}"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    path = sys.argv[1]
    with open(path, "rb") as fh:
        data = fh.read()
    magic, version, length = struct.unpack("<4sII", data[:12])
    print(f"file: {os.path.basename(path)}  bytes: {len(data)}  sha256: {hashlib.sha256(data).hexdigest()}")
    print(f"header: magic={magic!r} glTF container version={version} declared length={length} (matches file: {length == len(data)})")
    off = 12
    chunks = []
    while off < len(data):
        clen, ctype = struct.unpack("<I4s", data[off:off + 8])
        chunks.append((ctype, clen, off + 8))
        off += 8 + clen
    for ctype, clen, start in chunks:
        print(f"chunk {ctype!r}: {clen} bytes")
    jtype, jlen, jstart = chunks[0]
    gl = json.loads(data[jstart:jstart + jlen])
    bin_start = chunks[1][2] if len(chunks) > 1 else None
    print("top-level keys:", sorted(gl.keys()))
    print("asset:", json.dumps(gl.get("asset")))
    print("extensionsUsed:", gl.get("extensionsUsed"), " extensionsRequired:", gl.get("extensionsRequired"))
    print("scenes:", len(gl.get("scenes", [])), " nodes:", len(gl.get("nodes", [])), " meshes:", len(gl.get("meshes", [])))
    for n in gl.get("nodes", []):
        print("  node:", {k: v for k, v in n.items() if k in ("name", "mesh", "children", "matrix", "rotation", "scale", "translation")})
    acc = gl.get("accessors", [])
    for mi, m in enumerate(gl.get("meshes", [])):
        for pi, p in enumerate(m["primitives"]):
            attrs = {k: (acc[v]["count"], acc[v]["type"], acc[v].get("componentType")) for k, v in p["attributes"].items()}
            idx = acc[p["indices"]] if "indices" in p else None
            print(f"  mesh {mi} '{m.get('name')}' prim {pi}: mode={p.get('mode', 4)} attributes={attrs}")
            if idx:
                print(f"    indices: {idx['count']} ({idx['count'] // 3} triangles), componentType={idx['componentType']}")
            pos = acc[p["attributes"]["POSITION"]]
            print(f"    POSITION min={pos.get('min')} max={pos.get('max')}")
            print(f"    material: {p.get('material')}  extensions: {list(p.get('extensions', {}).keys())}")
    for i, mat in enumerate(gl.get("materials", [])):
        print(f"  material {i}: {json.dumps(mat)[:600]}")
    for i, img in enumerate(gl.get("images", [])):
        bv = gl["bufferViews"][img["bufferView"]] if "bufferView" in img else None
        info = ""
        if bv is not None and bin_start is not None:
            s = bin_start + bv.get("byteOffset", 0)
            info = png_size(data[s:s + 4096]) + f", {bv['byteLength']} bytes"
        print(f"  image {i}: name={img.get('name')} mimeType={img.get('mimeType')} uri={img.get('uri')} -> {info}")
    print("textures:", gl.get("textures"))
    print("samplers:", gl.get("samplers"))
    print("buffers:", [{k: v for k, v in b.items() if k != 'uri'} for b in gl.get("buffers", [])])
    print("extras / copyright fields:", gl.get("extras"), gl.get("asset", {}).get("copyright"))
    if len(sys.argv) > 2:
        z = sys.argv[2]
        print(f"\nzip: {os.path.basename(z)}")
        with zipfile.ZipFile(z) as zf:
            for info in zf.infolist():
                print(f"  {info.filename}  {info.file_size} bytes  (stored {info.compress_size}, method {info.compress_type}, date {info.date_time})")
            for info in zf.infolist():
                if info.filename.lower().endswith(".mtl"):
                    print("  --- mtl ---")
                    print("  " + zf.read(info).decode("utf-8", "replace").replace("\n", "\n  ")[:800])
                if info.filename.lower().endswith(".obj"):
                    head = zf.open(info).read(600).decode("utf-8", "replace")
                    print("  --- obj head ---\n  " + head.replace("\n", "\n  "))


if __name__ == "__main__":
    main()
