import json
import logging
import datetime
import time
import threading
import pychrome

# ─────── CONFIGURATION ──────────────────────────────────────────────────────────
RAW_LOG_PATH       = "raw_ws.log"
COMBAT_LOG_PATH    = "combat.log"
AMENDED_LOG_PATH   = "amended_raw.log"

MAX_INVENTORY_SLOT = 27
PLAYER_FILTER_ENABLED = True
PLAYER_FILTER         = {"621523", "665460"}

USER_MAP = {
    "621523": "Answerth",
    "665460": "Answerth2"
}

CHAT_FILTERS = {
    "global": {"enabled": True, "op_code": 90, "terms": []},
    "local":  {"enabled": True, "op_code": 12, "terms": []},
}

# ─────── OPCODE CONSTANTS ───────────────────────────────────────────────────────
OP_HIT_EVENT     = 8
OP_SKILL_XP      = 7
OP_INVENTORY_UPD = 6
OP_HP_EVENT      = 13
OP_DROP_EVENT    = 5

# Load lookup tables
with open("npcs_minified.json", encoding="utf-8") as f:
    NPC_MAP = {n["_id"]: n["name"] for n in json.load(f)}

with open("items.json", encoding="utf-8") as f:
    ITEM_MAP = {i["id"]: i["name"] for i in json.load(f)}

# Combat logger
logging.basicConfig(
    filename=COMBAT_LOG_PATH,
    filemode="a",
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO
)
logger = logging.getLogger()


# ─────── UTILITIES ──────────────────────────────────────────────────────────────
def should_log_player(player_id: str) -> bool:
    return True if not PLAYER_FILTER_ENABLED else (player_id in PLAYER_FILTER)

def resolve_user(player_id: str) -> str:
    return USER_MAP.get(player_id, f"Player/{player_id}")

def format_hit_event(attacker: str, defender: str, dmg: int, ts: str) -> str:
    att_name = NPC_MAP.get(attacker) or resolve_user(attacker)
    def_name = NPC_MAP.get(defender) or resolve_user(defender)
    return f"{ts} {att_name} hit {def_name}: {dmg}"

def format_drop_event(item_id: str, qty: int, ts: str) -> str:
    item = ITEM_MAP.get(item_id, f"Item#{item_id}")
    return f"{ts} → Drop: {item} x{qty}"


# ─────── FRAME HANDLER ───────────────────────────────────────────────────────────
def handle_frame(**kwargs):
    payload = kwargs.get("response", {}).get("payloadData", "")
    ts      = datetime.datetime.now().isoformat()

    # 1) Raw dump
    with open(RAW_LOG_PATH, "a", encoding="utf-8") as rawf:
        rawf.write(f"{ts} {payload}\n")

    # Prepare amended line
    tag           = "[UNHANDLED]"
    amended_line  = f"{ts} {payload}"

    if payload.startswith("42"):
        _, batch = json.loads(payload[2:])
        for op, pl in batch:

            if op == OP_HIT_EVENT:
                attacker, defender, dmg = pl
                if PLAYER_FILTER_ENABLED and not (
                    should_log_player(attacker) or should_log_player(defender)
                ):
                    continue
                line = format_hit_event(attacker, defender, dmg, ts)
                tag  = "[TRACKED]"
                logger.info(line)

            elif op == OP_DROP_EVENT:
                _, item_id, qty, *_ = pl
                line = format_drop_event(item_id, qty, ts)
                tag  = "[TRACKED]"
                logger.info(line)

            elif CHAT_FILTERS["global"]["enabled"] and op == CHAT_FILTERS["global"]["op_code"]:
                pid, username, msg = pl
                line = f"{ts} GLOBAL_CHAT {username}: {msg}"
                tag  = "[TRACKED]" if not CHAT_FILTERS["global"]["terms"] or any(t in msg for t in CHAT_FILTERS["global"]["terms"]) else "[IGNORED]"

            elif CHAT_FILTERS["local"]["enabled"] and op == CHAT_FILTERS["local"]["op_code"]:
                pid, _, msg = pl
                user = resolve_user(str(pid))
                line = f"{ts} LOCAL_CHAT {user}: {msg}"
                tag  = "[TRACKED]" if not CHAT_FILTERS["local"]["terms"] or any(t in msg for t in CHAT_FILTERS["local"]["terms"]) else "[IGNORED]"

            elif op == 9:
                item_id, = pl
                name = ITEM_MAP.get(item_id, f"Item#{item_id}")
                line = f"{ts} PICKUP {name}"
                tag  = "[TRACKED]"

            elif op == 103:
                _, slot_idx, item_id, qty, *rest = pl
                item_name = ITEM_MAP.get(item_id, f"Item#{item_id}")
                if slot_idx >= MAX_INVENTORY_SLOT:
                    line = f"{ts} INVENTORY FULL – could not place {item_name}"
                else:
                    line = f"{ts} {item_name} placed in inventory slot {slot_idx+1} x{qty}"
                tag  = "[TRACKED]"

            else:
                continue

            amended_line = f"{line} {tag}"
            break

    # 3) Append to amended log
    with open(AMENDED_LOG_PATH, "a", encoding="utf-8") as amf:
        amf.write(amended_line + "\n")

    # 4) Echo amended to console
    print(amended_line)


# ─────── BROWSER SETUP & LOOP ───────────────────────────────────────────────────
browser = pychrome.Browser(url="http://127.0.0.1:9222")
tabs    = browser.list_tab()
if not tabs:
    raise RuntimeError("Start Chrome with --remote-debugging-port=9222")
tab = tabs[0]

tab.start()
tab.Network.enable()
tab.Page.enable()

# Inject hook so window.gameSocket is set in-page on load
hook_js = r'''
(function(){
  if(!window.io) return;
  const orig = window.io;
  function hookedIo(...args){
    const s = orig(...args);
    window.gameSocket = s;
    return s;
  }
  Object.assign(hookedIo, orig);
  window.io = hookedIo;
})();
'''
tab.Page.addScriptToEvaluateOnNewDocument(source=hook_js)

tab.Page.navigate(url="https://highspell.com/game")
tab.Network.webSocketFrameReceived = handle_frame

# ─────── MOVE SENDER ────────────────────────────────────────────────────────────
player_id = 661513
def send_move(x: int, y: int):
    """Send a movement command to (x,y) via the in-page Socket.IO instance."""
    payload = json.dumps([ "0", [[1, [player_id, x, y]]] ])
    js = f'window.gameSocket.send("42"+{json.dumps(payload)});'
    tab.Runtime.evaluate(expression=js)
    print(f"→ Sent move to ({x},{y})")

# ─────── INPUT THREAD ───────────────────────────────────────────────────────────
def input_loop():
    """Continuously prompt for 'x,y' and send moves."""
    while True:
        try:
            coords = input("Enter x,y (or 'quit'): ").strip()
            if coords.lower() in ("quit", "exit"):
                break
            x_str, y_str = coords.split(",")
            x, y = int(x_str), int(y_str)
            send_move(x, y)
        except Exception as e:
            print("Invalid input:", e)

threading.Thread(target=input_loop, daemon=True).start()

print("✅ Listening for WebSocket frames. Enter coordinates in console to move.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    tab.stop()
    print("Stopped listening.")
