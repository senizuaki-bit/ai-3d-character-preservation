"""Write descriptive and rights metadata into a copy of a GLB without touching the geometry or textures.

  python add_glb_metadata.py <original.glb> <output.glb> <sidecar.json> <tencent_query_result.json>

Only the GLB's JSON chunk changes. The BIN chunk (meshes, UVs, the three embedded PNG textures)
is copied byte for byte, and the script checks that before finishing. The original file is
opened read-only and never written. Metadata uses glTF's own `asset.copyright` field and the
Khronos KHR_xmp_json_ld extension (XMP / Dublin Core as JSON-LD).
"""
import datetime as dt
import hashlib
import json
import os
import struct
import sys

AUTHOR = "SUN HAOSONG"
TITLE = "Stylised cartoon boy - 3D character model"
DESCRIPTION = (
    "Stylised 3D character with layered black hair, black fleece zip-up jacket with a small white "
    "chest logo, black sweatpants and chunky black sneakers, in a double thumbs-up pose. Generated "
    "by Tencent Hunyuan 3D (model hy-3d-3.0) from front, back, left and right reference views. "
    "One mesh, 250,000 triangles, PBR textures (base colour, metallic-roughness, normal) at 4096 x 4096."
)


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def read_glb(path):
    with open(path, "rb") as fh:
        data = fh.read()
    magic, version, length = struct.unpack("<4sII", data[:12])
    if magic != b"glTF" or version != 2 or length != len(data):
        sys.exit(f"{path}: not a valid GLB 2.0 container")
    chunks, off = [], 12
    while off < len(data):
        clen, ctype = struct.unpack("<I4s", data[off:off + 8])
        chunks.append((ctype, data[off + 8:off + 8 + clen]))
        off += 8 + clen
    if chunks[0][0] != b"JSON":
        sys.exit("first chunk is not JSON")
    return data, json.loads(chunks[0][1]), chunks[1:]


def write_glb(path, gltf, other_chunks):
    js = json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    js += b" " * (-len(js) % 4)  # glTF pads the JSON chunk with spaces
    body = struct.pack("<I4s", len(js), b"JSON") + js
    for ctype, payload in other_chunks:
        body += struct.pack("<I4s", len(payload), ctype) + payload
    out = struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body
    with open(path, "xb") as fh:  # "x": refuse to overwrite an existing file
        fh.write(out)
    return out


def alt(text):
    return {"@type": "rdf:Alt", "rdf:_1": {"@language": "en", "@value": text}}


def main():
    src, dst, sidecar, query_json = sys.argv[1:5]
    original, gltf, other_chunks = read_glb(src)

    with open(query_json, encoding="utf-8") as fh:
        job = json.load(fh)
    local_tz = dt.datetime.now().astimezone().tzinfo
    created = dt.datetime.fromtimestamp(job["completed_at"], local_tz).isoformat(timespec="seconds")
    now = dt.datetime.now(local_tz).isoformat(timespec="seconds")
    year = created[:4]
    rights = f"© {year} {AUTHOR}. All rights reserved."

    packet = {
        "@context": {
            "dc": "http://purl.org/dc/elements/1.1/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "xmp": "http://ns.adobe.com/xap/1.0/",
            "xmpRights": "http://ns.adobe.com/xap/1.0/rights/",
        },
        "@id": "",
        "dc:title": alt(TITLE),
        "dc:creator": {"@list": [AUTHOR]},
        "dc:date": {"@list": [created]},
        "dc:description": alt(DESCRIPTION),
        "dc:format": "model/gltf-binary",
        "dc:rights": alt(rights),
        "dc:subject": {"@set": ["3D model", "character", "stylised", "AI-generated", "glTF"]},
        "xmp:CreateDate": created,
        "xmp:MetadataDate": now,
        "xmp:CreatorTool": "Tencent Hunyuan 3D hy-3d-3.0 (TokenHub API); GLB written by "
                           + gltf["asset"].get("generator", "unknown"),
        "xmpRights:Marked": True,
        "xmpRights:Owner": {"@set": [AUTHOR]},
    }
    provenance = {
        "generated_by": "Tencent Hunyuan 3D via TokenHub API",
        "model": "hy-3d-3.0",
        "generate_type": "Normal",
        "face_count": 250000,
        "enable_pbr": True,
        "input_views": ["front", "back", "left", "right"],
        "generated": created,
        "original_file": os.path.basename(src),
        "original_sha256": sha256(original),
        "original_download_name": "tencent_6ccc77d3-9a99-4ced-8d10-218389ea383a_0.glb",
        "metadata_added": now,
        "metadata_added_by": AUTHOR,
    }

    asset = gltf["asset"]
    asset["copyright"] = rights
    asset.setdefault("extensions", {})["KHR_xmp_json_ld"] = {"packet": 0}
    asset.setdefault("extras", {})["provenance"] = provenance
    gltf.setdefault("extensions", {})["KHR_xmp_json_ld"] = {"packets": [packet]}
    used = gltf.setdefault("extensionsUsed", [])
    if "KHR_xmp_json_ld" not in used:
        used.append("KHR_xmp_json_ld")

    out = write_glb(dst, gltf, other_chunks)

    # Check: the new file parses, and every non-JSON chunk is byte-identical to the original.
    _, check_gltf, check_chunks = read_glb(dst)
    for (t0, p0), (t1, p1) in zip(other_chunks, check_chunks):
        if t0 != t1 or p0 != p1:
            sys.exit("BIN chunk changed - aborting")
    assert check_gltf["asset"]["copyright"] == rights

    bin_hash = sha256(other_chunks[0][1])
    record = {
        "object": TITLE,
        "creator": AUTHOR,
        "rights": rights,
        "created": created,
        "recorded": now,
        "fixity_algorithm": "SHA-256",
        "files": [
            {"file": os.path.basename(src), "role": "original download from Tencent, unchanged",
             "bytes": len(original), "sha256": sha256(original), "bin_chunk_sha256": bin_hash},
            {"file": os.path.basename(dst),
             "role": "copy with embedded metadata (asset.copyright, KHR_xmp_json_ld); BIN chunk identical to original",
             "bytes": len(out), "sha256": sha256(out), "bin_chunk_sha256": bin_hash},
        ],
        "provenance": provenance,
        "xmp_packet": packet,
    }
    with open(sidecar, "x", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({k: record[k] for k in ("creator", "rights", "created", "files")}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
