"""Deploy task/ to the JATOS study via the JATOS API (v1).

Usage:
  python scripts/deploy_jatos.py              # upload task files, ensure component exists
  python scripts/deploy_jatos.py --video      # also upload media/towerClimb.mp4 (288 MB)
  python scripts/deploy_jatos.py --check      # only check token + list study/components/assets
  python scripts/deploy_jatos.py --link       # also enable General Single links in the default batch and
                                              # write the study link to prolific/jatos_link.txt

Reads JATOS_URL, JATOS_TOKEN, JATOS_STUDY_ID from secrets.env.
"""
import argparse, http.cookiejar, json, pathlib, sys
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
TASK = ROOT / "task"
VIDEO = ROOT / "media" / "towerClimb.mp4"
COMPONENT_TITLE = "Film rating"


def load_env():
    env = {}
    for line in (ROOT / "secrets.env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    missing = [k for k in ("JATOS_URL", "JATOS_TOKEN", "JATOS_STUDY_ID") if not env.get(k)]
    if missing:
        sys.exit(f"Missing in secrets.env: {', '.join(missing)}")
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--link", action="store_true")
    a = ap.parse_args()

    env = load_env()
    base = env["JATOS_URL"].rstrip("/") + "/jatos/api/v1"
    sid = env["JATOS_STUDY_ID"]
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {env['JATOS_TOKEN']}"
    # Don't keep JATOS session cookies: once a cookie is sent, JATOS ignores the Bearer token -> 401.
    s.cookies.set_policy(http.cookiejar.DefaultCookiePolicy(allowed_domains=[]))

    def call(method, path, **kw):
        r = s.request(method, base + path, timeout=kw.pop("timeout", 60), **kw)
        if r.status_code >= 400:
            sys.exit(f"{method} {path} -> {r.status_code}: {r.text[:500]}")
        return r.json() if r.content and "json" in r.headers.get("content-type", "") else r

    tok = call("GET", "/admin/token")
    print("token ok:", json.dumps(tok.get("data", tok))[:200])
    # Resolve the study (numeric id or UUID) and use the UUID from here on.
    allp = call("GET", "/studies/properties").get("data", [])
    d = next((x for x in allp if str(x.get("id")) == sid or x.get("uuid") == sid), None)
    if d is None:
        sys.exit(f"Study {sid} not found among studies this token can access")
    sid = d["uuid"]
    print(f"study {sid}: {d.get('title')!r} uuid={d.get('uuid')} dir={d.get('dirName')}")
    comps = call("GET", f"/studies/{sid}/components").get("data", [])
    print("components:", [(c.get("id"), c.get("title"), c.get("htmlFilePath")) for c in comps])
    if a.check:
        assets = call("GET", f"/studies/{sid}/assets/structure")
        print("assets:", json.dumps(assets.get("data", assets))[:1500])
        return

    files = sorted(p for p in TASK.rglob("*") if p.is_file())
    for p in files:
        rel = p.relative_to(TASK).as_posix()
        with p.open("rb") as fh:
            call("POST", f"/studies/{sid}/assets/{rel}", files={"studyAssetsFile": (p.name, fh)})
        print("uploaded", rel)
    if a.video:
        print(f"uploading {VIDEO.name} ({VIDEO.stat().st_size / 1e6:.0f} MB)...")
        with VIDEO.open("rb") as fh:
            call("POST", f"/studies/{sid}/assets/{VIDEO.name}",
                 files={"studyAssetsFile": (VIDEO.name, fh, "video/mp4")}, timeout=3600)
        print("uploaded", VIDEO.name)

    if not any(c.get("htmlFilePath") == "index.html" for c in comps):
        c = call("POST", f"/studies/{sid}/components",
                 json={"title": COMPONENT_TITLE, "htmlFilePath": "index.html", "reloadable": True, "active": True})
        print("created component:", json.dumps(c.get("data", c))[:200])
    if a.link:
        make_link(call, base, sid, env)
    print("done")


def make_link(call, base, sid, env):
    """Enable General Single in the default batch and get its study link (one run per browser;
    reloads within a run are allowed because the component is reloadable)."""
    batches = call("GET", f"/studies/{sid}/batches").get("data", [])
    b = batches[0]
    types = set(b.get("allowedWorkerTypes") or [])
    if "GeneralSingle" not in types:
        types.add("GeneralSingle")
        call("PATCH", f"/batches/{b['id']}", json={"allowedWorkerTypes": sorted(types)})
        print("enabled GeneralSingle in batch", b["id"])
    r = call("POST", f"/studies/{sid}/studyCodes", params={"type": "GeneralSingle", "batchId": b["id"]})
    payload = r.get("data", r)
    code = payload[0] if isinstance(payload, list) else payload
    if isinstance(code, dict):
        code = code.get("code") or code.get("studyCode")
    link = f"{env['JATOS_URL'].rstrip('/')}/publix/{code}"
    (ROOT / "prolific" / "jatos_link.txt").write_text(link + "\n")
    print("study link:", link, "-> prolific/jatos_link.txt")


if __name__ == "__main__":
    main()
