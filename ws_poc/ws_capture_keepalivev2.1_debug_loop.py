# ws_capture_once.py

from playwright.sync_api import sync_playwright
import sys

def main():
    pw = sync_playwright().start()
    browser = pw.firefox.launch(headless=False)
    page = browser.new_context().new_page()

    seen = []

    def on_ws(ws):
        url = ws.url
        if url not in seen:
            seen.append(url)
            print(f"→ Detected WS URL: {url}", flush=True)

    page.on("websocket", on_ws)

    print("▶️  Browser launched. Navigate/log in as needed.")
    page.goto("https://highspell.com/")

    # 1) Wait until you see the printed WS URL(s)
    input("\n🕵️  When you see the WS URL above, press ENTER to capture it...")

    if not seen:
        print("❌  No WS URLs detected! Exiting without closing browser.")
        sys.exit(1)

    # 2) Echo all URLs captured
    print("\nAll captured WS URLs:")
    for i, url in enumerate(seen, 1):
        print(f"  {i}. {url}")

    chosen = seen[0]
    print(f"\n✅  Using URL: {chosen}")

    # 3) Now you can use `chosen` in your proxy/monitoring script,
    #    all while this browser session remains alive.

    input("\n🔒  Press ENTER when you’re done and want to close the browser...")

    browser.close()
    pw.stop()
    print("👋  Browser closed. Goodbye!")

if __name__ == "__main__":
    main()
