#!/usr/bin/env python3
# local_ws_proxy.py

import asyncio
import json
import sys
from collections import Counter

import websockets

# ─── Configuration ────────────────────────────────────────────────────────────
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8765

KEEP_OPCODES = {
    "tree_up",
    "tree_down",
    "npc_kill",
    "inventory_full",
    # add more opcodes to keep here…
}

_kept = Counter()
_dropped = Counter()

def should_keep(opcode: str) -> bool:
    if opcode in KEEP_OPCODES:
        _kept[opcode] += 1
        return True
    else:
        _dropped[opcode] += 1
        return False

def print_summary():
    print("\n\n=== OPCODE SUMMARY ===")
    print("Kept:")
    for op, cnt in _kept.items():
        print(f"  {op}: {cnt}")
    print("Dropped:")
    for op, cnt in _dropped.items():
        print(f"  {op}: {cnt}")
    print("======================\n")

# ─── Proxy Handler ────────────────────────────────────────────────────────────
async def proxy_handler(client_ws, path):
    target_ws_url = PROXY.target
    print(f"[Proxy] Client connected → forwarding to {target_ws_url}")

    async with websockets.connect(target_ws_url) as upstream_ws:
        async def pipe(src, dst):
            async for raw in src:
                # try parsing JSON to extract opcode
                try:
                    msg = json.loads(raw)
                    opcode = str(msg[0])
                except Exception:
                    # non-JSON or malformed frames: forward unfiltered
                    await dst.send(raw)
                    continue

                if should_keep(opcode):
                    await dst.send(raw)
                # otherwise, drop it silently (but counted)

        # bidirectional pump
        await asyncio.gather(
            pipe(client_ws, upstream_ws),
            pipe(upstream_ws, client_ws),
        )

# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <target_websocket_url>")
        sys.exit(1)

    target_url = sys.argv[1]
    PROXY = type("P", (), {"target": target_url})  # simple namespace

    loop = asyncio.get_event_loop()

    # Schedule the server under the running loop
    server = loop.run_until_complete(
        websockets.serve(proxy_handler, LISTEN_HOST, LISTEN_PORT, ping_interval=None)
    )

    print(f"[Proxy] Listening on ws://{LISTEN_HOST}:{LISTEN_PORT}/")
    print(f"[Proxy] Forwarding connections to: {target_url}")

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user (Ctrl+C)")
        print_summary()
    finally:
        # close server and loop
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()
        sys.exit(0)
