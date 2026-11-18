"""Tencent TokenHub 3D client (stdlib only). The API key is read from the TENCENT_3D_KEY env var, never from disk.

  python t3d.py post <submit|query|...> <payload.json>   # "@b64:<view>" / "@uri:<view>" strings become the image
  python t3d.py poll <model> <job_id> <out_dir> [interval_s] [timeout_s]
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "https://tokenhub.tencentmaas.com/v1/api/3d"
REFS = r"C:\Users\HP\Desktop\2005\Lab Assessment 1\character_model\rodin_refs"


def headers():
    key = os.environ.get("TENCENT_3D_KEY", "").strip()
    if not key:
        sys.exit("TENCENT_3D_KEY is not set")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "python-urllib"}


def expand(obj):
    if isinstance(obj, dict):
        return {k: expand(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand(v) for v in obj]
    if isinstance(obj, str):
        m = re.fullmatch(r"@(b64|uri):(\w+)", obj)
        if m:
            with open(os.path.join(REFS, m.group(2) + ".jpg"), "rb") as fh:
                raw = base64.b64encode(fh.read()).decode()
            return raw if m.group(1) == "b64" else "data:image/jpeg;base64," + raw
    return obj


def redact(obj):
    if isinstance(obj, dict):
        return {k: redact(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    if isinstance(obj, str) and len(obj) > 300:
        return obj[:60] + f"...<{len(obj)} chars>"
    return obj


def post(path, payload, timeout=120):
    req = urllib.request.Request(f"{BASE}/{path}", data=json.dumps(payload).encode(), headers=headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, body = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read().decode("utf-8", "replace")
    try:
        return status, json.loads(body)
    except Exception:
        return status, body


def find_urls(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            find_urls(v, out)
    elif isinstance(obj, list):
        for v in obj:
            find_urls(v, out)
    elif isinstance(obj, str) and obj.startswith("http"):
        out.append(obj)
    return out


def find_status(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in ("status", "state", "task_status", "job_status") and isinstance(v, (str, int)):
                return str(v)
        for v in obj.values():
            s = find_status(v)
            if s:
                return s
    if isinstance(obj, list):
        for v in obj:
            s = find_status(v)
            if s:
                return s
    return None


def download(url, out_dir):
    name = os.path.basename(url.split("?")[0]) or "download.bin"
    dest = os.path.join(out_dir, "tencent_" + name)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "python-urllib"}), timeout=600) as r, \
            open(dest, "wb") as fh:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)
    return dest


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cmd = sys.argv[1]
    if cmd == "post":
        with open(sys.argv[3], encoding="utf-8") as fh:
            payload = json.load(fh)
        status, body = post(sys.argv[2], expand(payload))
        print("HTTP", status)
        print(json.dumps(redact(body), indent=1, ensure_ascii=False) if not isinstance(body, str) else body[:3000])
    elif cmd == "poll":
        model, job_id, out_dir = sys.argv[2], sys.argv[3], sys.argv[4]
        interval = float(sys.argv[5]) if len(sys.argv) > 5 else 5
        timeout = float(sys.argv[6]) if len(sys.argv) > 6 else 1200
        os.makedirs(out_dir, exist_ok=True)
        t0, last, body = time.time(), None, None
        while time.time() - t0 < timeout:
            status, body = post("query", {"model": model, "id": job_id})
            st = find_status(body) if not isinstance(body, str) else None
            if st != last:
                print(f"[{time.time() - t0:5.0f}s] HTTP {status} status={st}", flush=True)
                last = st
            if status != 200 or (st and st.lower() in ("done", "success", "succeeded", "completed", "finished",
                                                       "fail", "failed", "error", "canceled", "cancelled")):
                break
            time.sleep(interval)
        with open(os.path.join(out_dir, "tencent_query_result.json"), "w", encoding="utf-8") as fh:
            json.dump(body, fh, indent=1, ensure_ascii=False)
        print(json.dumps(redact(body), indent=1, ensure_ascii=False)[:4000] if not isinstance(body, str) else body[:3000])
        for url in find_urls(body, []):
            if re.search(r"\.(glb|gltf|obj|fbx|zip|png|jpg|jpeg|webp|mtl|usdz|stl)(\?|$)", url, re.I):
                try:
                    dest = download(url, out_dir)
                    print("saved", os.path.basename(dest), os.path.getsize(dest), "bytes", flush=True)
                except Exception as e:
                    print("download failed:", url[:120], repr(e), flush=True)


if __name__ == "__main__":
    main()
