from collections import Counter

# define which opcodes you want to keep
KEEP_OPCODES = {"tree_up", "tree_down", "npc_kill", "inventory_full"}

summary = Counter()
dropped = Counter()

def should_keep(opcode):
    """Return True if we forward this opcode."""
    if opcode in KEEP_OPCODES:
        summary[opcode] += 1
        return True
    else:
        dropped[opcode] += 1
        return False

def record_summary(opcode=None, print_report=False):
    """If print_report, dump the kept vs dropped counts, else no-op."""
    if print_report:
        print("\n=== OPCODE SUMMARY ===")
        print("Kept:"); 
        for op, cnt in summary.items():
            print(f"  {op}: {cnt}")
        print("Dropped:")
        for op, cnt in dropped.items():
            print(f"  {op}: {cnt}")
