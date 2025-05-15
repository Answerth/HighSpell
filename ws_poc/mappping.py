import json, os

DATA_DIR = "data"
MAP_FILE = os.path.join(DATA_DIR, "npc_mapping.json")
PENDING_FILE = os.path.join(DATA_DIR, "pending_npcs.json")

# load or init
os.makedirs(DATA_DIR, exist_ok=True)
try:
    with open(MAP_FILE) as f:
        npc_map = json.load(f)
except FileNotFoundError:
    npc_map = {}

try:
    with open(PENDING_FILE) as f:
        pending = json.load(f)
except FileNotFoundError:
    pending = {}

def record_npc(npc_id):
    """
    If we've seen this NPC before, nothing to do.
    Otherwise, increment pending count and save.
    """
    sid = str(npc_id)
    if sid not in npc_map:
        pending[sid] = pending.get(sid, 0) + 1
        with open(PENDING_FILE, "w") as f:
            json.dump(pending, f, indent=2)
