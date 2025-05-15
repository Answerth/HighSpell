# ws_capture_inline.py
import sys
sys.stdout.reconfigure(line_buffering=True)

from playwright.sync_api import sync_playwright

def main():
    pw      = sync_playwright().start()
    browser = pw.firefox.launch(headless=False)
    page    = browser.new_context().new_page()

    all_ws_urls = set()
    def on_ws(ws):
        url = ws.url
        if url not in all_ws_urls:
            all_ws_urls.add(url)
            print(f"→ Detected NEW WS URL: {url}", flush=True)

    page.on("websocket", on_ws)
    page.goto("https://highspell.com/")

    print("\n🔥 WebSocket scanner running.  Press Ctrl+C to quit.\n")

    try:
        while True:
            # hand control back to Playwright so we see URLs immediately
            page.wait_for_timeout(100)  # 100 ms
    except KeyboardInterrupt:
        pass
    finally:
        print("\n👋 Closing browser and exiting.")
        browser.close()
        pw.stop()

if __name__ == "__main__":
    main()
