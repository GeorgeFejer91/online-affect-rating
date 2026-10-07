"""Headless integration check for the optional 2D feedback view."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import subprocess

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "media" / "flubber-test.mp4"


def main():
    (ROOT / "tests/out").mkdir(exist_ok=True)
    if not VIDEO.exists():
        VIDEO.parent.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "color=c=black:s=640x360:r=30:d=5", "-c:v", "libx264", "-pix_fmt",
                        "yuv420p", str(VIDEO)], check=True)
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, accept_downloads=True)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            config = (ROOT / "task/js/config.js").read_text(encoding="utf-8").replace("preload: true", "preload: false")
            page.route("**/task/js/config.js", lambda route: route.fulfill(body=config, content_type="text/javascript"))
            experiment = (ROOT / "task/js/experiment.js").read_text(encoding="utf-8").replace(
                "const line = JSON.stringify(obj) + \"\\n\";",
                "(window.__ratingLines ||= []).push(obj); const line = JSON.stringify(obj) + \"\\n\";",
            ).replace("on_trial_finish: (d) => {", "on_trial_finish: (d) => { if (d.task === 'film') window.__film = d;")
            page.route("**/task/js/experiment.js", lambda route: route.fulfill(body=experiment, content_type="text/javascript"))
            url = f"http://127.0.0.1:{server.server_port}/task/index.html?dim=affect2d&reset=1&skip=intro&video=../media/flubber-test.mp4"
            page.goto(url)
            page.locator(".sticsa-table").wait_for(timeout=30000)
            for item in [1, 2, 6, 7, 8, 12, 14, 15, 18, 20, 21]:
                page.locator(f"input[name=sticsa_{item}][value='1']").check()
            page.locator("#jspsych-survey-html-form-next").click()
            page.locator(".cr-overlay-btn").click()
            page.keyboard.press("ArrowRight")
            page.keyboard.press("Space")
            page.wait_for_function("document.querySelector('.cr-video')?.currentTime > 0.1")
            assert page.locator(".cr-flubber").is_visible()
            assert page.locator(".cr-flubber-shape").get_attribute("d").startswith("M")
            page.screenshot(path=str(ROOT / "tests/out/flubber.png"))
            page.keyboard.press("g")
            assert page.locator(".cr-grid").is_visible()
            page.screenshot(path=str(ROOT / "tests/out/grid.png"))
            page.keyboard.press("f")
            assert page.locator(".cr-flubber").is_visible()
            page.wait_for_function("window.__ratingLines?.some(x => x.type === 'chunk' && x.events.some(e => e.e === 'end'))", timeout=15000)
            chunks = page.evaluate("window.__ratingLines.filter(x => x.type === 'chunk')")
            events = [event for chunk in chunks for event in chunk["events"]]
            modes = [event["mode"] for event in events if event["e"] == "feedback_switch"]
            assert modes == ["grid", "flubber"], modes
            samples = [row for chunk in chunks for row in chunk["samples"]]
            assert samples and all(len(row) == 6 for row in samples), "2D film sample schema changed"
            page.wait_for_function("window.__film?.feedback_final === 'flubber'")
            assert page.evaluate("window.__film.feedback_initial") == "flubber"
            assert not errors, errors
            grid_page = browser.new_page(viewport={"width": 1400, "height": 900})
            grid_page.route("**/task/js/config.js", lambda route: route.fulfill(body=config, content_type="text/javascript"))
            grid_page.goto(url + "&feedback=grid")
            grid_page.locator(".sticsa-table").wait_for(timeout=30000)
            for item in [1, 2, 6, 7, 8, 12, 14, 15, 18, 20, 21]:
                grid_page.locator(f"input[name=sticsa_{item}][value='1']").check()
            grid_page.locator("#jspsych-survey-html-form-next").click()
            grid_page.locator(".cr-grid").wait_for()
            assert grid_page.locator(".cr-grid").is_visible()
            assert not grid_page.locator(".cr-flubber").is_visible()
            browser.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
