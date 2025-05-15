# ws_capture_keepalive.py

from playwright.sync_api import sync_playwright, TimeoutError
import re

def main():
    # ─── Start Playwright & Firefox ─────────────────────────────────────────────
    pw = sync_playwright().start()
    browser = pw.firefox.launch(headless=False)
    context = browser.new_context()        # add proxy={"server": ...} if you like
    page    = context.new_page()

    ws_urls = []

    # ─── Listener for ANY WebSocket the page opens ───────────────────────────────
    def on_ws(ws):
        ws_urls.append(ws.url)
        print(f"→ Detected WS URL: {ws.url}")

    page.on("websocket", on_ws)

    # ─── Navigate to the game page ────────────────────────────────────────────────
    page.goto("https://highspell.com/")

    # ─── Wait for the *first* WebSocket, up to 50 s ───────────────────────────────
    try:
        first_ws = page.wait_for_event("websocket", timeout=50_000)
        ws_url   = first_ws.url
        print(f"\n→ Captured WS URL: {ws_url}")
    except TimeoutError:
        print(f"\n⚠️ No WebSocket detected in 50 s. URLs seen: {ws_urls}")
        if not ws_urls:
            raise RuntimeError("No WebSocket connections detected at all!")
        ws_url = ws_urls[0]
        print(f"→ Falling back to first seen URL: {ws_url}")

    print(f"\nUsing WebSocket URL: {ws_url}")

    # ─── KEEP THE BROWSER OPEN until you hit ENTER ────────────────────────────────
    input("\n✅ Browser is still running. Press ENTER to close it and exit script.")

    # ─── Clean up ─────────────────────────────────────────────────────────────────
    browser.close()
    pw.stop()

if __name__ == "__main__":
    main()
