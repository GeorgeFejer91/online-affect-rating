"""Create a Prolific *draft* study (never publishes) for one rating dimension.

Usage:
  python scripts/create_prolific_study.py --dim anxiety --places 6 --tag pilot [--dry-run]
  python scripts/create_prolific_study.py --dim random --places 6 --tag pilot
  python scripts/create_prolific_study.py --dim affect2d --places 6 --tag pilot --block <study-1 id>
  python scripts/create_prolific_study.py --dim affect2d --places 20 --tag main_c1 --quota-sex --block <pilot ids>

Builds the study from prolific/study_template.json + prolific/filters.json, points it at the
JATOS study link in prolific/jatos_link.txt (written by scripts/deploy_jatos.py --link), adds
the Prolific URL parameters and ?dim=, then runs `prolific study create` (draft only).
Publishing is a deliberate manual step:  scripts/prolific.sh study publish <id>  (or the web UI).
"""
import argparse, json, os, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECT_MOVIERATINGS = "6ac1c23dd2c370786a5fa2fa"

ap = argparse.ArgumentParser()
ap.add_argument("--dim", required=True, choices=["anxiety", "affect2d", "random"])
ap.add_argument("--places", type=int, required=True)
ap.add_argument("--tag", default="pilot")
ap.add_argument("--project", default=PROJECT_MOVIERATINGS)
ap.add_argument("--block", action="append", default=[], help="Prolific study ID whose participants are excluded")
ap.add_argument("--quota-sex", action="store_true",
                help="Quota sample balanced 50/50 on Prolific's Sex screener (Male/Female)")
ap.add_argument("--link", help="JATOS study link (default: prolific/jatos_link.txt)")
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()

study = json.loads((ROOT / "prolific/study_template.json").read_text(encoding="utf8"))
filters = json.loads((ROOT / "prolific/filters.json").read_text(encoding="utf8"))["filters"]

# Completion codes must match the redirect URLs in task/js/config.js
cfg = (ROOT / "task/js/config.js").read_text(encoding="utf8")
for c in study["completion_codes"]:
    if f"cc={c['code']}" not in cfg:
        sys.exit(f"Completion code {c['code']} not found in task/js/config.js")

link_file = ROOT / "prolific/jatos_link.txt"
link = a.link or (link_file.read_text().strip() if link_file.exists() else None)
if not link:
    sys.exit("No JATOS link: run scripts/deploy_jatos.py --link first, or pass --link")

params = "PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}"
if a.dim != "random":
    params += f"&dim={a.dim}"
study["external_study_url"] = f"{link}{'&' if '?' in link else '?'}{params}"
study["internal_name"] = f"vmp towerClimb {a.dim} {a.tag}"
study["total_available_places"] = a.places
study["project"] = a.project
if a.block:
    filters = filters + [{"filter_id": "previous_studies_blocklist", "selected_values": a.block}]
if a.quota_sex:
    study["study_type"] = "QUOTA"
    filters = filters + [{"filter_id": "sex", "selected_values": ["0", "1"], "weightings": {"0": 1, "1": 1}}]
study["filters"] = filters

out = ROOT / "prolific/generated" / f"{a.tag}_{a.dim}.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(study, indent=2, ensure_ascii=False), encoding="utf8")
print("wrote", out.relative_to(ROOT))
cost = a.places * study["reward"] / 100
print(f"{a.places} places x £{study['reward'] / 100:.2f} = £{cost:.2f} in rewards (plus Prolific fees)")
if a.dry_run:
    sys.exit(0)

# Call the CLI directly (on Windows a bare "bash" can resolve to WSL), with secrets.env in the environment.
env = dict(os.environ)
for line in (ROOT / "secrets.env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
cli = shutil.which("prolific") or str(ROOT / "bin" / ("prolific.exe" if os.name == "nt" else "prolific"))
r = subprocess.run([cli, "study", "create", "-t", str(out)], capture_output=True, text=True, encoding="utf8", env=env)
print(r.stdout[-3000:], r.stderr[-2000:])
sys.exit(r.returncode)
