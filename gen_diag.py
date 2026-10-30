#!/usr/bin/env python3
"""Generate the 3x 128-pin DIN 41612 (CD128) diagnostic pass-through board.

  gen_diag.py board   write diag.kicad_pcb (no tracks) and diag.dsn for Freerouting
  gen_diag.py import  read diag.ses and write the tracks into diag.kicad_pcb

Every connector is 4 rows (a-d) x 32 positions, 2.54 mm grid, 1.0 mm holes
(TE/ERNI 364918-E drill pattern). Pin <row><n> of all three connectors is one net.
"""
import json
import re
import sys

PITCH = 2.54
ROWS = "abcd"
COLS = 32
PAD = 1.6
DRILL = 1.0
MOUNT_DRILL = 2.8
TRACK = 0.15
CLEAR = 0.15
VIA = 0.6
VIA_DRILL = 0.3
GAP = 16.0           # free routing space between connectors
EDGE = 5.3           # male row a -> board edge (mating face overhangs)
MARGIN = 6.0         # board edge to outer row/column
PCB = "diag.kicad_pcb"
PRO = "diag.kicad_pro"
MIN_TRACK = 0.127
DSN = "diag.dsn"
SES = "diag.ses"

# (reference, value, row-a y of the connector); y grows downwards, row d is above row a
CONNECTORS = [
    ("J1", "MALE_RA_364918-E", 0.0),
    ("J2", "FEMALE_128", -(3 * PITCH + GAP)),
    ("J3", "FEMALE_128", -2 * (3 * PITCH + GAP)),
]
MALE = "J1"

BOARD_L = -(COLS - 1) * PITCH - 5.08 - MARGIN
BOARD_R = 5.08 + MARGIN
BOARD_B = EDGE
BOARD_T = CONNECTORS[-1][2] - 3 * PITCH - MARGIN - 3.0  # room for the title text


def pins(row_a_y):
    """(name, x, y) of every pin; pin 1 at x=0, pin 32 at the left."""
    return [
        (f"{r}{n}", -(n - 1) * PITCH, row_a_y - i * PITCH)
        for n in range(1, COLS + 1)
        for i, r in enumerate(ROWS)
    ]


def net_names():
    return [f"{r}{n}" for n in range(1, COLS + 1) for r in ROWS]


def net_ids():
    return {name: i + 1 for i, name in enumerate(net_names())}


def footprint(ref, value, row_a_y, ids):
    x0, x1 = -(COLS - 1) * PITCH - 2.5, 2.5
    y0, y1 = row_a_y - 3 * PITCH - 2.5, row_a_y + 2.5
    out = [
        f'  (footprint "{value}" (layer "F.Cu") (at 0 0)',
        f'    (property "Reference" "{ref}" (at {x0 + 8} {y0 - 1.5}) (layer "F.SilkS") (effects (font (size 1.5 1.5) (thickness 0.25))))',
        f'    (property "Value" "{value}" (at {x0 + 40} {y0 - 1.5}) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))',
        f'    (fp_rect (start {x0} {y0}) (end {x1} {y1}) (stroke (width 0.15) (type solid)) (fill none) (layer "F.SilkS"))',
        f'    (fp_text user "1" (at 0 {y1 + 1.5}) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
        f'    (fp_text user "32" (at {-(COLS - 1) * PITCH} {y1 + 1.5}) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
    ]
    for name, x, y in pins(row_a_y):
        out.append(
            f'    (pad "{name}" thru_hole circle (at {x:.2f} {y:.2f}) (size {PAD} {PAD}) (drill {DRILL}) '
            f'(layers "*.Cu" "*.Mask") (net {ids[name]} "{name}"))'
        )
    if ref == MALE:
        for x in (-(COLS - 1) * PITCH - 5.08, 5.08):
            out.append(
                f'    (pad "" np_thru_hole circle (at {x:.2f} {row_a_y + PITCH:.2f}) '
                f'(size {MOUNT_DRILL} {MOUNT_DRILL}) (drill {MOUNT_DRILL}) (layers "*.Cu" "*.Mask"))'
            )
    out.append("  )")
    return "\n".join(out)


def write_board(tracks=""):
    ids = net_ids()
    out = [
        '(kicad_pcb (version 20241229) (generator "gen_diag") (generator_version "1.0")',
        "  (general (thickness 1.6) (legacy_teardrops no))",
        '  (paper "A3")',
        "  (layers",
        '    (0 "F.Cu" signal) (2 "B.Cu" signal)',
        '    (9 "F.Adhes" user "F.Adhesive") (11 "B.Adhes" user "B.Adhesive")',
        '    (13 "F.Paste" user) (15 "B.Paste" user)',
        '    (5 "F.SilkS" user "F.Silkscreen") (7 "B.SilkS" user "B.Silkscreen")',
        '    (1 "F.Mask" user) (3 "B.Mask" user)',
        '    (25 "Edge.Cuts" user) (27 "Margin" user)',
        '    (31 "F.CrtYd" user "F.Courtyard") (29 "B.CrtYd" user "B.Courtyard")',
        '    (35 "F.Fab" user) (33 "B.Fab" user))',
        "  (setup",
        f"    (pad_to_mask_clearance 0)",
        "    (pcbplotparams (layerselection 0x00000000_00000000_55555555_5755f5ff) (outputdirectory \"gerber/\")))",
        '  (net 0 "")',
    ]
    out += [f'  (net {i} "{n}")' for n, i in ids.items()]
    out += [footprint(ref, value, y, ids) for ref, value, y in CONNECTORS]
    out.append(
        f'  (gr_rect (start {BOARD_L:.2f} {BOARD_T:.2f}) (end {BOARD_R:.2f} {BOARD_B:.2f}) '
        '(stroke (width 0.1) (type solid)) (fill none) (layer "Edge.Cuts"))'
    )
    out.append(
        f'  (gr_text "DIN41612 CD128 DIAG PASS-THROUGH  J1=male (364918-E)  J2,J3=female" '
        f'(at {(BOARD_L + BOARD_R) / 2:.2f} {BOARD_T + 1.8:.2f}) (layer "F.SilkS") '
        "(effects (font (size 1.2 1.2) (thickness 0.2))))"
    )
    out.append(tracks)
    out.append(")")
    with open(PCB, "w") as f:
        f.write("\n".join(out) + "\n")


def write_project():
    """Board rules matching a standard 2-layer PCBWay process."""
    rules = {
        "min_clearance": MIN_TRACK,
        "min_track_width": MIN_TRACK,
        "min_via_diameter": 0.5,
        "min_through_hole_diameter": 0.3,
        "min_via_annular_width": 0.15,
        "min_copper_edge_clearance": 0.3,
        "min_hole_to_hole": 0.25,
        "min_hole_clearance": 0.25,
    }
    net_class = {"name": "Default", "clearance": CLEAR, "track_width": TRACK, "via_diameter": VIA, "via_drill": VIA_DRILL}
    pro = {"board": {"design_settings": {"rules": rules}}, "net_settings": {"classes": [net_class], "meta": {"version": 3}}}
    with open(PRO, "w") as f:
        json.dump(pro, f, indent=2)


def um(v):
    return round(v * 1000)


def write_dsn():
    ids = net_ids()
    # DSN y axis points up
    boundary = " ".join(
        f"{um(x)} {um(-y)}"
        for x, y in [(BOARD_L, BOARD_B), (BOARD_R, BOARD_B), (BOARD_R, BOARD_T), (BOARD_L, BOARD_T), (BOARD_L, BOARD_B)]
    )
    images = []
    places = []
    for ref, _, row_a_y in CONNECTORS:
        pin_lines = "\n".join(
            f'      (pin Pad {name} {um(x)} {um(-y)})' for name, x, y in pins(row_a_y)
        )
        images.append(f"    (image {ref}\n{pin_lines}\n    )")
        places.append(f"    (component {ref} (place {ref} 0 0 front 0))")
    nets = "\n".join(
        f'    (net {n} (pins {" ".join(f"{ref}-{n}" for ref, _, _ in CONNECTORS)}))' for n in ids
    )
    dsn = f"""(pcb {DSN}
  (parser (string_quote ") (space_in_quoted_tokens on) (host_cad "gen_diag") (host_version "1.0"))
  (resolution um 1)
  (unit um)
  (structure
    (layer F.Cu (type signal) (property (index 0)))
    (layer B.Cu (type signal) (property (index 1)))
    (boundary (path pcb 0 {boundary}))
    (via Via)
    (rule (width {um(TRACK)}) (clearance {um(CLEAR)}))
  )
  (placement
{chr(10).join(places)}
  )
  (library
{chr(10).join(images)}
    (padstack Pad
      (shape (circle F.Cu {um(PAD)}))
      (shape (circle B.Cu {um(PAD)}))
      (attach off)
    )
    (padstack Via
      (shape (circle F.Cu {um(VIA)}))
      (shape (circle B.Cu {um(VIA)}))
      (attach off)
    )
  )
  (network
{nets}
    (class default {" ".join(ids)}
      (circuit (use_via Via))
      (rule (width {um(TRACK)}) (clearance {um(CLEAR)}))
    )
  )
  (wiring)
)
"""
    with open(DSN, "w") as f:
        f.write(dsn)


def import_ses():
    ids = net_ids()
    text = open(SES).read()
    scale = 1 / float(re.search(r"\(resolution um (\d+)\)", text).group(1)) / 1000  # ses unit -> mm
    tracks = []
    for m in re.finditer(r'\(net "?(\w+)"?\s', text):
        start = m.start()
        depth = 0
        for i in range(start, len(text)):
            depth += text[i] == "("
            depth -= text[i] == ")"
            if depth == 0:
                end = i
                break
        block = text[start:end]
        net = m.group(1)
        if net not in ids:
            continue
        for layer, width, coords in re.findall(r"\(path (\S+) (\d+)\s+([-\d\s]+)\)", block):
            xy = [int(v) * scale for v in coords.split()]
            pts = [(xy[i], -xy[i + 1]) for i in range(0, len(xy), 2)]
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                tracks.append(
                    f'  (segment (start {x0:.4f} {y0:.4f}) (end {x1:.4f} {y1:.4f}) '
                    f'(width {max(int(width) * scale, MIN_TRACK):.4f}) (layer "{layer}") (net {ids[net]}))'
                )
        for x, y in re.findall(r"\(via \S+ (-?\d+) (-?\d+)", block):
            tracks.append(
                f'  (via (at {int(x) * scale:.4f} {-int(y) * scale:.4f}) (size {VIA}) (drill {VIA_DRILL}) '
                f'(layers "F.Cu" "B.Cu") (net {ids[net]}))'
            )
    write_board("\n".join(tracks))
    print(f"imported {len(tracks)} track/via items")


if __name__ == "__main__":
    if sys.argv[1:] == ["board"]:
        write_board()
        write_dsn()
        write_project()
    elif sys.argv[1:] == ["import"]:
        import_ses()
    else:
        sys.exit(__doc__)
