#!/usr/bin/env python3
"""
build_case.py -- Parametric FreeCAD Part-API generator for a snap-fit
enclosure for a portable ESP32-S3 device (e-ink display + 2 mechanical
switches + LiPo battery), split into TWO printed parts (a bottom TRAY and
a top LID) joined by a continuous perimeter hook-and-lip snap, interrupted
at the USB-C port.

RUN IT
------
    freecadcmd build_case.py
or paste the whole file into FreeCAD's Python console, or run it as a Macro.
No manual GUI steps are required. Re-running is idempotent (it opens a
fresh in-memory document each time).

Outputs, written next to this script:
    case_bottom.stl            -- the tray, PRINT THIS (bed-ready: Z=0 is
                                   the floor's underside)
    case_top.stl                -- the lid, PRINT THIS (bed-ready: Z=0 is
                                   the skirt's free tip)
    case_assembled_preview.stl   -- both parts in their correct assembled
                                   position, for a visual fit-check in any
                                   STL viewer. NOT for printing -- it's a
                                   compound of the same two solids above,
                                   just positioned to show the mate. If
                                   you load case_bottom.stl and
                                   case_top.stl directly into a slicer and
                                   they look misaligned, that's this: each
                                   is intentionally zeroed to its own
                                   print-bed contact face, not to a shared
                                   assembly origin. Load this file instead
                                   to check the fit.
    case_preview.FCStd            -- both solids in one FreeCAD document
                                   (same assembled position), for
                                   inspection/editing in the GUI

To see the computed numbers behind every decision below, run:
    freecadcmd build_case.py --summary
which prints print_summary() and exits without exporting anything (fast,
for iterating on constants).

====================================================================
DESIGN OVERVIEW
====================================================================

LAYOUT: a single row, floor to floor: battery, then the MCU, then the
switch column, all sitting side by side in the plan view (not stacked in
Z) -- the battery and MCU zones share their dividing wall since they sit
flush against each other. The e-ink display is the only thing still
stacked in Z: it's adhesive-mounted above the battery+MCU row, spanning
both of their footprints, at DISPLAY_REST_Z (section 5). Only the display
trades case height for a smaller footprint now; the battery and MCU no
longer do.

SUPPORT: the MCU rests on a floor-level shelf pocket (shelf_frame()) with
open air below it for solder joints, plus a U-shaped retention wall on 3
sides (open at the USB-C edge) so a charging plug pushes against a
floor-anchored wall instead of relying on friction alone. The battery
sits directly on the tray floor (no shelf -- it's a solid cell, nothing
needs clearance beneath it) with a single retention wall between it and
the MCU (the wall the two zones share) so it can't slide sideways. The
display has NO posts, shelves, or walls holding it up in the tray at all
-- it's adhesive/tape-mounted directly on top of the battery+MCU row, at
DISPLAY_REST_Z (section 5); nothing in the printed tray registers the
display's position. It additionally gets a full lateral-confinement ring
molded into the LID (screen_lip + screen_wall in build_lid()), open only
on the segment facing the switch column.

SWITCHES: mounted "plate style" -- PCB, a 5mm air gap, then a 14x14mm hole
in the lid's own outer face that the switch upper housing pokes through
and rises above by design (this is how mechanical keyboards work). That
keeps the case a flat, uniform-height prism instead of needing a stepped
top to bury the switch's full housing height.

SNAP FIT: a continuous chamfered bead-in-groove around the tray/lid
perimeter, interrupted only at the USB-C notch, sized and checked against
PLA's real elongation-at-break (read from HARDWARE.md when present) via
snap_fit_strain() (section 6). No separate alignment pins -- the
bead/groove engagement plus the switch plate-hole engagement register the
lid in X/Y between them.

A second, smaller detent grips the display module itself against the
lid's screen retention wall (screen_snap_strain(), section 6) -- the
rigid module plays the "bead" half, the thin cantilevered screen_wall
plays the "groove" half, same physics as the main snap above just
checked separately since its thickness/flex-length differ. It's an
XY-plane (sideways) squeeze, not a Z-axis hook, because the Z room above
the display (STACK_TOP_MARGIN, 0.5mm) is too tight for a cantilever to
ever spring rather than jam -- see "Screen retention" in section 3.

VISIBLE SEAM: sits at the middle of the case height (SEAM_FRACTION=0.5).
The lid has its own full-height "cap wall" above the seam, flush with the
tray's own wall, and a thinner skirt hidden inside the tray's cavity below
the seam purely for the snap engagement.

ASSUMPTIONS: HARDWARE.md gives XY footprints for the display module and
MCU but not their Z thickness, and doesn't specify a switch PCB at all.
Every such figure is a named constant flagged "ASSUMPTION" or "STANDARD,
not from HARDWARE.md" in section 2, and all of them are also listed
together in print_summary() under "Assumed / generic figures" so nothing
is buried.

PLA CAVEAT: PLA's elongation-at-break is roughly 3-5x lower than ABS or
PETG, which matters for a snap fit meant to be opened/closed repeatedly.
snap_fit_strain() targets only ~30% of PLA's ultimate elongation as the
allowable design strain (a fatigue margin, not a one-shot-assembly
margin) -- see SNAP_STRAIN_SAFETY_FRACTION below. If this case will be
opened often, consider printing the lid in PETG instead.
"""

import os
import sys
import math

import FreeCAD as App
import Part
from FreeCAD import Vector

# ====================================================================
# 1. MATERIAL -- read from HARDWARE.md if present, else a flagged default
# ====================================================================

def read_elongation_from_hardware_md(path):
    """Pull the PLA elongation-at-break out of HARDWARE.md's filament
    table. Returns (fraction, source_string). Falls back to a generic
    published PLA figure (and says so) if the file or the row is
    missing."""
    generic_fraction = 0.11  # ~11%, typical published PLA elongation at break
    generic_source = ("GENERIC PLA figure (~11 percent), NOT a datasheet: "
                       "no HARDWARE.md found at '%s'" % path)
    if not os.path.isfile(path):
        return generic_fraction, generic_source
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return generic_fraction, generic_source

    for line in text.splitlines():
        if "Elongation at break" in line:
            # table row looks like: | **Elongation at break** | 11.2% |
            cells = [c.strip() for c in line.split("|") if c.strip()]
            for cell in cells:
                if cell.endswith("%"):
                    try:
                        pct = float(cell.rstrip("%"))
                        return pct / 100.0, ("HARDWARE.md filament table: "
                                              "elongation at break = %s" % cell)
                    except ValueError:
                        continue
    return generic_fraction, generic_source


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
_HARDWARE_MD = os.path.join(_SCRIPT_DIR, "HARDWARE.md")

ELONGATION_AT_BREAK, ELONGATION_SOURCE = read_elongation_from_hardware_md(_HARDWARE_MD)

# Fraction of ultimate elongation-at-break used as the *allowable design
# strain* for the snap-fit flex. Kept well below 1.0 because: (a) this
# joint is meant to be opened/closed repeatedly, not deformed once, and
# (b) PLA is a fairly brittle thermoplastic with little fatigue margin
# compared to ABS/PETG/nylon (see the module docstring's PLA CAVEAT).
SNAP_STRAIN_SAFETY_FRACTION = 0.30

# ====================================================================
# 2. COMPONENT DIMENSIONS -- HARDWARE.md values where given, flagged
#    assumptions everywhere else
# ====================================================================

# ---- Display: 2.13" SPI E-Ink HAT -----------------------------------
DISPLAY_MODULE_W = 65.0     # HARDWARE.md: full module footprint
DISPLAY_MODULE_D = 30.0     # HARDWARE.md
DISPLAY_ACTIVE_W = 48.55    # HARDWARE.md: active area
DISPLAY_ACTIVE_D = 23.71    # HARDWARE.md
# ASSUMPTION: HARDWARE.md gives no module thickness. 2.13" e-paper HATs
# are typically ~1.2 mm glass + ~1.6 mm PCB + adhesive/spacer, no pin
# header (this device wires to the MCU directly over SPI, not an RPi
# GPIO header) -> budget 4.0 mm. If a populated header is actually used,
# add ~8.5 mm and re-check DISPLAY clearance in print_summary().
DISPLAY_THICKNESS = 4.0

# ---- MCU: Seeed XIAO ESP32-S3 Sense (no camera) ----------------------
MCU_W = 21.0                # HARDWARE.md: board dimensions (long axis)
MCU_D = 17.5                # HARDWARE.md: board dimensions (short axis, USB-C edge)
# ASSUMPTION: XIAO-family boards are ~3.5 mm over the PCB+shield; budget
# 4.0 mm for the assembled board envelope (PCB + antenna/shield + solder).
MCU_THICKNESS = 4.0
# Ordinary solder-joint clearance under the MCU board, sitting on its own
# floor-level shelf (shelf_frame(), build_tray()).
MCU_SHELF_CLEARANCE = 1.0
USB_C_CUTOUT_W = 9.0       # ASSUMPTION: ~10x6mm opening, typical USB-C receptacle
USB_C_CUTOUT_H = 3.0
# ASSUMPTION: connector height above the board's bottom face -- typical
# USB-C receptacle (~3.2mm) sitting on a ~1.2mm PCB. VERIFY against the
# physical board before printing; the cutout has +/-1mm of vertical
# margin built in (see USB_C_CUTOUT_H) to absorb a modest error here.
USB_C_CENTER_Z_ABOVE_SHELF = 3.0

# microSD slot (the Sense expansion board's card reader): a wall opening
# so a card can be slid in/out without opening the case, on the same -Y
# wall as the USB-C port, positioned per the design brief -- 3mm above
# the USB-C notch's own top edge (MICROSD_GAP_ABOVE_USBC, section 5).
# ASSUMPTION: neither the slot's exact board-relative position nor its
# opening size is in HARDWARE.md. Sized for a standard microSD card
# (11 x 1.0mm cross-section, inserted edge-first) plus clearance for the
# card and its holder mechanism -- VERIFY against the physical board
# before printing, same as the USB-C figures above.
MICROSD_SLOT_W = 12.0       # ASSUMPTION: 11mm card width + slide clearance
MICROSD_SLOT_H = 2.0        # ASSUMPTION: ~1mm card thickness + holder/clearance margin
MICROSD_GAP_ABOVE_USBC = 3.0  # per design brief: slot sits 3mm above the USB-C notch's top

# ---- Battery: EEMB 603449 -------------------------------------------
BATTERY_W = 48.0            # measured on the physical cell (overrides HARDWARE.md's 51mm datasheet figure)
BATTERY_D = 34.0            # measured on the physical cell (overrides HARDWARE.md's 34.5mm datasheet figure)
BATTERY_T = 6.3             # HARDWARE.md

# ---- Switches: 2x Cherry MX2A Silent Blue on a hot-swap PCB ----------
SWITCH_HOLE = 14.0           # STANDARD Cherry MX plate-hole spec (14x14mm), also used as the footprint
SWITCH_PITCH = 19.05         # STANDARD keyboard key pitch (0.75in), not in HARDWARE.md
N_SWITCHES = 2
# LID opening per button. Deliberately separate from SWITCH_HOLE (14mm):
# SWITCH_HOLE still drives the PCB footprint/plate spec everywhere else
# in this file, this only enlarges the LID's cutout. At SWITCH_PITCH
# (19.05mm) two adjacent 19mm squares leave only 0.05mm between their
# edges -- see build_lid()'s comment for why that's cut as ONE merged
# rectangle instead of two separate (near-)overlapping boxes.
LID_BUTTON_HOLE = 19.0
# Custom hot-swap PCB: its outline isn't specified anywhere, so this
# margin beyond the switch bodies is sized generously for solder pads /
# socket clearance / routing -- 2.0mm is real, usable margin for a
# hot-swap socket's pads, close to the floor before the PCB itself
# becomes the risk, not the case.
SWITCH_PCB_MARGIN_X = 2.0
SWITCH_PCB_MARGIN_Y = 2.0
SWITCH_PCB_W = SWITCH_PITCH * (N_SWITCHES - 1) + SWITCH_HOLE + 2 * SWITCH_PCB_MARGIN_X
SWITCH_PCB_D = SWITCH_HOLE + 2 * SWITCH_PCB_MARGIN_Y
SWITCH_PCB_THICKNESS = 1.6   # STANDARD FR4 thickness, not in HARDWARE.md
# STANDARD mechanical-keyboard convention, not in HARDWARE.md:
PCB_TO_PLATE = 5.0                    # PCB top surface to underside of plate
SWITCH_HOUSING_ABOVE_PCB = 11.6       # PCB top to top of switch upper housing (informational)
# Clearance needed *below* the switch PCB for the YMDK/Kailh hot-swap
# socket body + the switch's through-PCB plunger pins (typical socket +
# pin protrusion is ~3-3.5mm). The actual value (SWITCH_PCB_BELOW_CLEARANCE)
# is DERIVED in section 5 from the MCU/battery/display stack's own height
# requirement instead, since the stack needs more height than the
# switches themselves do -- see section 5 for the real number.

# ====================================================================
# 3. PRINT / SHELL PARAMETERS
# ====================================================================

WALL_T = 2.0            # general shell wall thickness (floor, ceiling, sides)
CORNER_FILLET_OUTER = 8.0   # external vertical-corner radius -- "fits in the hand"
# Outer TOP/BOTTOM edge treatment: rounds the horizontal rim where the flat
# floor/ceiling face meets the outer wall -- the edges a palm/fingers
# actually rest against, not just the vertical corners. This is a
# SEQUENCE of progressively smaller CHAMFERS (rounded_edge_chamfer(),
# section 7), not a true fillet: a fillet on this rim runs along the same
# tangent-continuous straight+arc loop as CORNER_FILLET_OUTER's own
# rounded corners, and filleting a curved edge like that reliably bulges
# the shape outward at the corners in this OCCT version (confirmed on
# this shape -- the same bug the snap bead's chamfer, below, works around
# the same way). Each stage chamfers the edge the previous stage just
# created, approximating a round as a multi-facet profile rather than one
# flat bevel. Applied early, on the plain outer solid before any other
# feature, so the chamfer geometry stays simple.
# 4 stages is the practical ceiling for this OCCT version: a direct sweep
# against the actual tray/lid shapes shows 5-6 stage sequences at the same
# ~1.95mm total fail outright ("no suitable edges for chamfer or fillet")
# even though 4 stages at that total succeeds. The total (1.9mm) stays a
# comfortable margin under WALL_T/FLOOR_T/CEIL_T (2.0mm).
OUTER_EDGE_CHAMFER_STAGES = [0.7, 0.5, 0.4, 0.3]

# ---- Display window corner/edge treatment (build_lid()) --------------
# Same rounding idea as CORNER_FILLET_OUTER/OUTER_EDGE_CHAMFER_STAGES
# above, applied to the 50x25mm screen opening instead of the whole case
# -- deliberately smaller than both (2.5mm corner vs. 8.0mm; 0.5mm total
# rim bevel vs. 1.9mm), since a window this size would look wrong with
# exterior-scale rounding.
WINDOW_CORNER_R = 2.5
WINDOW_EDGE_CHAMFER_STAGES = [0.3, 0.2]

FIT_CLEARANCE_XY = 0.30     # per-side clearance around dropped-in components
FIT_CLEARANCE_Z = 0.50      # vertical clearance above components

ROW_GAP = 2.0            # gap between component zones (rib/wire-routing space)
BORDER = 2.0             # gap between innermost wall face and component zones

# ---- MCU retention -----------------------------------------------------
# The MCU's own shelf_frame (section 8) gives it somewhere to rest with
# under-board clearance, but a plain flat ledge provides NO in-plane
# retention at all -- friction only. That's a real problem specifically
# for this board: charging means repeatedly pushing a USB-C plug in
# through the case wall, a genuine horizontal shove aimed straight at
# the board. A U-shaped wall (back + 2 sides, open at the USB-C front
# for cable access) turns that push into compression against a wall
# anchored in the floor, instead of relying on friction to hold the
# board still. Uses a TIGHTER clearance than the general
# FIT_CLEARANCE_XY (0.30mm) specifically here -- the board still needs
# to drop in from above without binding, but the whole point is
# minimizing the slop it can shift through before the push force is
# actually caught.
MCU_RETENTION_CLEARANCE = 0.15
MCU_BACKSTOP_T = 2.0        # back wall thickness -- takes the insertion push
MCU_SIDE_WALL_T = 1.2       # side guide wall thickness -- stops off-axis rocking
MCU_SIDE_WALL_FRACTION = 0.6  # side walls cover only the back 60% of MCU's
                               # length, left loose (normal clearance) near the
                               # USB-C edge so the connector itself is never
                               # pinched and the board still drops in easily

# ---- Battery retention --------------------------------------------------
# The battery sits directly on the tray floor next to the MCU (not
# adhesive-stacked on top of it anymore, see section 4's layout), so it
# needs its own in-plane retention the same way the MCU does. A single
# wall between the battery and MCU zones does the job -- the two zones
# sit flush against each other, so this one wall is both the battery's
# retention and the MCU zone's own boundary on that side, rather than
# each getting a separate wall (they "share the same wall" per the
# layout brief). A cable notch through it lets the battery's power leads
# reach the MCU, same idea as the switch column's wire_notch
# (build_tray()).
BATTERY_WALL_T = 2.0

# ---- Screen retention -------------------------------------------------
# No lid-side snap TAB hanging from the ceiling: the only Z room
# available for a tab to hang from the ceiling and flex is
# STACK_TOP_MARGIN (0.5mm), and a beam that short is thousands of times
# stiffer than the case's own 5.5mm snap skirt (deflection ~ 1/L^3) --
# it would jam or not touch, never spring.
#
# The display has no posts, shelves, or walls in the TRAY at all (see the
# module docstring's SUPPORT note) -- it's adhesive/tape-mounted directly
# on top of the battery+MCU row. Its only retention is on the LID side:
# screen_lip and screen_wall (build_lid()) form a ring around its
# perimeter, open only on the segment facing the switch column.
#
# The physical module measured ~1mm longer along its 65mm (W) axis than
# the plain FIT_CLEARANCE_XY (0.30mm/side) pocket allowed for -- too
# tight to seat. SCREEN_LENGTH_EXTRA_CLEARANCE below adds that 1mm
# entirely on the FAR (+X) side of the pocket, not split evenly: the
# NEAR (-X) side is flush against the case's own exterior wall (only
# ~0.3mm of slack before hitting solid material there -- see lip_x0 in
# build_lid()), so all the growth has to happen on the +X side, which has
# several mm of open cavity to spare before the switch column.
SCREEN_LENGTH_EXTRA_CLEARANCE = 1.0  # added to lip_w's W-axis (65mm) span only, +X side

# ---- Screen snap-fit detent -------------------------------------------
# On top of the plain clearance-fit lip/wall above, add real assembly
# resistance: a small inward bead on screen_wall's two LONG sides only
# (the -Y and +Y segments, each spanning the module's full W-axis
# length) -- the module's rigid top-outer edge cams these chamfered
# beads outward as the lid is lowered into place, then the wall's own
# elastic spring-back squeezes the module's sides once seated. Deliberately
# NOT on the -X segment (already fused solid into the exterior wall, with
# only ~0.3mm of clearance to flex into -- too tight and not a free
# cantilever anyway) or the +X segment (already interrupted by
# SCREEN_WALL_BUTTON_NOTCH_W). Both long sides have >5mm of open cavity
# beyond them before the next exterior wall (see build_lid()), plenty of
# room to flex into. Checked separately from the main snap
# (screen_snap_strain(), section 6) since screen_wall's thickness
# (SCREEN_WALL_T) and cantilever length (SCREEN_RETENTION_WALL_H, section
# 5) both differ from the main snap's skirt. Deliberately NOT chamfered
# like the main bead/groove -- see the detent's own comment in
# build_lid() for why a lead-in ramp isn't worth it at this scale.
SCREEN_SNAP_INTERFERENCE = 0.15  # d -- see screen_snap_strain() for margin
SCREEN_SNAP_BAND_H = 1.0         # height of the detent band along the wall
SCREEN_SNAP_TIP_OFFSET = 0.3     # how far above screen_wall's own free tip the detent sits (BEAD_TIP_OFFSET's analog)
SCREEN_SNAP_OVERLAP_EPS = 0.1    # guaranteed-fuse overlap into the wall, same idea as OVERLAP_EPS elsewhere

# ---- Snap-fit geometry (see snap_fit_strain() for the math) ----------
# d (SNAP_INTERFERENCE) must clear 2*SKIRT_CLEARANCE with real margin: at
# exactly 2*SKIRT_CLEARANCE the bead's tip and the skirt's own clearance-
# inset surface sit at the identical radius (touching, not overlapping),
# which produces a mechanism that looks geometrically fine but doesn't
# actually snap together. 0.5mm here leaves 0.1mm of real engagement
# above that dead zone.
SNAP_FLEX_LENGTH = 5.5      # L: cantilever flex length = lid skirt depth (mm)
SNAP_SKIRT_T = 1.2          # t: thickness of the flexing lid skirt (mm)
SNAP_INTERFERENCE = 0.5     # d: radial bead/groove interference (mm)
SNAP_BEAD_BAND_H = 1.2      # height of the bead/groove band along the wall (mm)
# Chamfer size for the bead/groove ramp (see build_tray()'s comment for
# why it's a chamfer, not a fillet). The safe range for this OCCT version
# is NOT a fixed number -- it scales with the bead ring's own radial wall
# thickness (~SNAP_INTERFERENCE): at the current interference, a direct
# size sweep against the actual bead/groove rings shows ~0.28-0.30mm+
# throws a hard OCCT exception (caught by the try/except in
# build_tray()/build_lid(), which falls back to an unchamfered square
# ridge -- see the printed WARNING there if that ever triggers), while
# 0.20mm stays reliably clean with real margin below that boundary.
# Re-test with a direct sweep any time SNAP_INTERFERENCE, SNAP_BEAD_BAND_H,
# or BEAD_Z0 change, rather than assuming this value carries over.
BEAD_CHAMFER_SIZE = 0.2

# ====================================================================
# 4. DERIVED LAYOUT (plan view) -- SINGLE ROW, FLOOR TO FLOOR: BATTERY,
#    MCU, SWITCH COLUMN, LEFT TO RIGHT. ONLY THE SCREEN IS STILL
#    Z-STACKED, ABOVE THE BATTERY+MCU ROW.
#
#    +---+------------------------+
#    |sw1|                        |   The battery and MCU sit side by
#    +---+       SCREEN            |   side on the tray floor (sharing
#    |sw2|  (battery + MCU on     |   their dividing wall), with the
#    |   |   the floor, screen     |   screen adhesive-stacked above
#    |   |   adhesive-stacked      |   both of them (see section 5) --
#    |   |   above both)           |   only the screen trades case
#    +---+------------------------+   height for footprint now.
# ====================================================================

SCREEN_W, SCREEN_L = DISPLAY_MODULE_W, DISPLAY_MODULE_D  # 65 x 30, landscape

# Switch column: reuse the switch-PCB footprint from section 2, pitch
# direction along Y (stacked vertically, narrow width) so it adds as
# little width as possible next to the row.
SWITCH_COL_W, SWITCH_COL_L = SWITCH_PCB_D, SWITCH_PCB_W

# Battery + MCU row: battery, the shared retention wall, then the MCU --
# all side by side along X. Row depth is the bounding box of whichever
# member is deepest (screen sits above the whole row, so it's included
# too even though it isn't part of the row itself).
STACK_ROW_W = BATTERY_W + BATTERY_WALL_T + MCU_D
STACK_D = max(SCREEN_L, BATTERY_D, MCU_W)

CONTENT_W = STACK_ROW_W + ROW_GAP + SWITCH_COL_W
CONTENT_D = max(STACK_D, SWITCH_COL_L)

INTERNAL_W = CONTENT_W + 2 * BORDER
INTERNAL_D = CONTENT_D + 2 * BORDER

EXTERNAL_W = INTERNAL_W + 2 * WALL_T
EXTERNAL_D = INTERNAL_D + 2 * WALL_T

# Battery + MCU row (local internal coordinates):
STACK_X0 = BORDER
STACK_Y0 = BORDER + (CONTENT_D - STACK_D) / 2.0  # centered if switches are taller

# Screen: flush against the far interior wall (the one opposite the
# switch column, away from ROW_GAP), same as the row itself -- centered
# in Y within the row's own band. SCREEN_W (65) is wider than the
# battery alone (51) so the screen overlaps most of the MCU's footprint
# too, which is the point: it's meant to sit over both.
SCREEN_X0 = 0.0
SCREEN_Y0 = STACK_Y0 + (STACK_D - SCREEN_L) / 2.0

# Battery: flush against the row's own -X edge (the case's far interior
# wall), centered in Y within the row's band.
BATTERY_X0 = STACK_X0
BATTERY_Y0 = STACK_Y0 + (STACK_D - BATTERY_D) / 2.0

# Switch column, beside the row:
SWITCH_COL_X0 = STACK_X0 + STACK_ROW_W + ROW_GAP
SWITCH_COL_Y0 = BORDER + (CONTENT_D - SWITCH_COL_L) / 2.0

# MCU: beside the battery, across their shared retention wall (X extent
# is MCU's short/USB-C edge, MCU_D; long axis MCU_W runs along Y). Flush
# with the row's own -Y edge so the MCU's USB-C short edge sits close to
# the case's -Y (top) wall -- same reasoning as the old Z-stacked layout,
# just applied in-plane now instead of offset in Y from the battery.
MCU_X0 = BATTERY_X0 + BATTERY_W + BATTERY_WALL_T
MCU_Y0 = STACK_Y0

# ====================================================================
# 5. DERIVED Z STACK
# ====================================================================
#
# Internal cavity height is set by the taller of the battery/MCU (both on
# the tray floor now, see section 4) plus the display adhesive-stacked
# above them, not by the switch's plate-mount geometry: that stack still
# needs more height than the switches ever do, so the cavity height is
# set by it, and the switch PCB's own shelf is derived (raised) to keep
# its plate gap correct at whatever height that turns out to be.
#
# Battery and MCU both sit on the tray floor side by side (section 4),
# each at its own height: the MCU rests on its own floor-level shelf
# (build_tray()) with under-board clearance; the battery sits directly on
# the floor (a solid cell, nothing needs clearance beneath it) behind its
# own retention wall. The display is adhesive-stacked above BOTH of them,
# with NO post, shelf, or wall holding it up -- nothing printed registers
# its position vertically beyond the adhesive itself.
#
#   0                                   tray floor top
#   + MCU_SHELF_CLEARANCE               ordinary solder-joint clearance
#   = MCU bottom
#   + MCU_THICKNESS
#   = MCU top (MCU_TOP_Z); battery top (BATTERY_TOP_Z) sits at BATTERY_T,
#     directly off the floor -- the display rests above whichever of the
#     two is taller
#   + DISPLAY_STANDOFF_H                assembly/adhesive-layer air gap
#   = display's resting height (DISPLAY_REST_Z)
#   + DISPLAY_THICKNESS
#   = display top
#   + STACK_TOP_MARGIN                  clearance to the plate
#   = INTERNAL_CAVITY_H                 lid's inner (plate) face
#
MCU_TOP_Z = MCU_SHELF_CLEARANCE + MCU_THICKNESS       # = MCU's own physical top
BATTERY_TOP_Z = BATTERY_T                             # = battery's own physical top (rests flat on the floor)

# Standoff air gap reserved above the battery+MCU row's own top before
# the display starts -- headroom for the adhesive/foam-tape layer that
# holds the display in place, since it has no post or shelf to rest on.
DISPLAY_STANDOFF_H = 5.0

DISPLAY_REST_Z = max(MCU_TOP_Z, BATTERY_TOP_Z) + DISPLAY_STANDOFF_H   # = display's resting height
DISPLAY_TOP_Z = DISPLAY_REST_Z + DISPLAY_THICKNESS
STACK_TOP_MARGIN = 0.5  # deliberately tight -- see print_summary()'s strain-margin numbers
INTERNAL_CAVITY_H = DISPLAY_TOP_Z + STACK_TOP_MARGIN

# Switch PCB shelf, DERIVED so the plate still sits exactly PCB_TO_PLATE
# above the switch PCB at whatever height the stack requires (much taller
# than the switches themselves need -- that's fine, it just means a lot
# of unused clearance under the switch PCB).
SWITCH_PCB_BELOW_CLEARANCE = INTERNAL_CAVITY_H - PCB_TO_PLATE - SWITCH_PCB_THICKNESS
assert SWITCH_PCB_BELOW_CLEARANCE > 0, (
    "stack (%.2f) leaves no room for the switch PCB's own plate gap" % INTERNAL_CAVITY_H)
SWITCH_PCB_TOP_Z = SWITCH_PCB_BELOW_CLEARANCE + SWITCH_PCB_THICKNESS

FLOOR_T = WALL_T
CEIL_T = WALL_T
EXTERNAL_H = FLOOR_T + INTERNAL_CAVITY_H + CEIL_T

# --------------------------------------------------------------------
# How the two parts share the internal cavity height, AND where the
# VISIBLE parting line sits.
#
# The tray's wall runs from the floor up to the seam (TRAY_EXTERNAL_H);
# the lid has its own full-width, WALL_T-thick "cap wall" from the seam up
# to the ceiling, same profile as the tray's wall so the two meet flush.
# Below the seam, hidden inside the tray's cavity, the lid's wall
# continues down as a thin, nested skirt (SNAP_SKIRT_T thick) for
# ENGAGE_DEPTH more, purely for the snap engagement -- invisible from
# outside either way. A single flat butt joint between tray wall and lid
# skirt would leave the two occupying disjoint Z-ranges with no overlap
# for a bead/groove to ever engage in, which is why the skirt has to
# nest INSIDE the tray's cavity instead.
#
# SEAM_FRACTION controls where the visible seam sits as a fraction of
# EXTERNAL_H (0.5 = middle).
SEAM_FRACTION = 0.5
ENGAGE_DEPTH = SNAP_FLEX_LENGTH  # also the cantilever flex length used below

TRAY_EXTERNAL_H = EXTERNAL_H * SEAM_FRACTION  # the seam itself
TRAY_WALL_INTERNAL_H = TRAY_EXTERNAL_H - FLOOR_T
assert TRAY_WALL_INTERNAL_H > ENGAGE_DEPTH + 2.0, (
    "SEAM_FRACTION puts the seam too close to the floor -- the tray wall "
    "(%.1fmm) has to be taller than the engagement depth (%.1fmm) plus "
    "room for the bead" % (TRAY_WALL_INTERNAL_H, ENGAGE_DEPTH))

LID_CAP_WALL_H = INTERNAL_CAVITY_H - TRAY_WALL_INTERNAL_H  # lid's visible wall, seam to ceiling
LID_EXTERNAL_H = ENGAGE_DEPTH + LID_CAP_WALL_H + CEIL_T
EXTERNAL_H_CHECK = TRAY_EXTERNAL_H + LID_CAP_WALL_H + CEIL_T
assert abs(EXTERNAL_H_CHECK - EXTERNAL_H) < 1e-9

# Global Z the lid's local Z=0 (its skirt's free tip) lands at once seated:
LID_PLACEMENT_Z = TRAY_EXTERNAL_H - ENGAGE_DEPTH

# Per-side running clearance so the skirt can slide freely inside the
# tray's cavity before it reaches the bead band.
SKIRT_CLEARANCE = 0.2

# --------------------------------------------------------------------
# Bead Z-position: the lid's skirt is a cantilever fixed where it meets
# the cap wall and free at its lower tip. Only the length of skirt
# BETWEEN the fixed end and wherever the bead pushes actually bends --
# material beyond the push point just gets carried along, unbent. Since
# strain scales as 1/L^2 (snap_fit_strain()), the bead needs to sit near
# the skirt's FREE end (near LID_PLACEMENT_Z), not its fixed end, so the
# true flex length is close to the full ENGAGE_DEPTH the strain formula
# assumes -- a bead near the fixed end instead would silently understate
# the real strain by a large factor.
#
# BEAD_TIP_OFFSET is how far short of the exact tip the bead actually
# sits (headroom so the bead ring doesn't land exactly on the skirt's
# flat bottom edge). The TRUE distance from the fixed end to the push
# point is therefore ENGAGE_DEPTH - BEAD_TIP_OFFSET, not ENGAGE_DEPTH
# itself -- snap_fit_strain() uses that true distance
# (SNAP_TRUE_FLEX_LENGTH, below), not ENGAGE_DEPTH directly, since even a
# small gap here matters once squared into the strain formula.
BEAD_TIP_OFFSET = 0.15  # how far the bead sits above the skirt's free tip
BEAD_Z0 = LID_PLACEMENT_Z + BEAD_TIP_OFFSET  # near the skirt's free tip, not the rim
GROOVE_Z0_LOCAL = BEAD_Z0 - LID_PLACEMENT_Z  # == BEAD_TIP_OFFSET, near the lid's own local Z=0

# The TRUE cantilever flex length used by snap_fit_strain() (section 6):
# distance from the skirt's fixed end (the seam) down to where the bead
# actually pushes (BEAD_Z0), not the full ENGAGE_DEPTH. See the long
# comment above for why the two differ by exactly BEAD_TIP_OFFSET.
SNAP_TRUE_FLEX_LENGTH = ENGAGE_DEPTH - BEAD_TIP_OFFSET

# How tall the switch stack rises above the finished case's outer top
# surface -- expected, see the module docstring's SWITCHES note:
SWITCH_PROTRUSION_ABOVE_CASE = (FLOOR_T + SWITCH_PCB_TOP_Z + SWITCH_HOUSING_ABOVE_PCB) - EXTERNAL_H

# Screen retention wall height (lid-local Z frame, see build_lid()):
# hoisted to module level (rather than computed inline in build_lid(),
# the older pattern) so screen_snap_strain() below can use the same
# cantilever length the actual geometry uses, instead of a second,
# possibly-drifting copy of the formula.
SCREEN_WALL_T = 1.5
SCREEN_WALL_CLEARANCE = 0.3
SCREEN_RETENTION_WALL_H = (EXTERNAL_H - CEIL_T) - (FLOOR_T + DISPLAY_REST_Z + SCREEN_WALL_CLEARANCE)
assert SCREEN_RETENTION_WALL_H > 0, (
    "no room for a screen retention wall above the display's resting height -- "
    "raise DISPLAY_STANDOFF_H/STACK_TOP_MARGIN or tighten SCREEN_WALL_CLEARANCE")

# USB-C cutout Z (global, from tray bottom): measured from the MCU's own
# floor-level shelf clearance.
USB_C_CENTER_Z = FLOOR_T + MCU_SHELF_CLEARANCE + USB_C_CENTER_Z_ABOVE_SHELF

# USB-C notch Z-range (global), shared by build_tray() and build_lid() so
# the two openings line up exactly. Sized purely from the connector's own
# position (USB_C_CENTER_Z, USB_C_CUTOUT_H) plus a placement-tolerance
# margin -- it has no bead term in it at all, so its size is not driven by
# the snap bead's own position.
#
# It happens to OVERLAP the bead band in Z at the current case height
# (BEAD_Z0 sits near the middle of the case via SEAM_FRACTION=0.5; the
# connector is roughly mid-height on the MCU's floor-level shelf too).
# That overlap isn't a bug to fix by moving the bead -- the bead's
# Z-position is constrained by the strain calculation (section 6) to stay
# near the skirt's free tip, and the connector's Z-position is fixed by
# the hardware. Where they overlap, the notch cut simply removes the
# bead/groove locally over the notch's own ~9-11mm width -- the
# "interrupted at the USB-C port" behavior described at the top of this
# file. It costs a short, harmless gap in an otherwise continuous
# ~270mm perimeter bead, not a structural problem. Both build_tray() and
# build_lid() apply the cut unconditionally (it's a no-op wherever there's
# no material), since which part the port actually falls in depends on
# SEAM_FRACTION and the component stack -- currently entirely within the
# lid's cap wall, but this stays correct if that ever shifts.
USB_C_NOTCH_Z0 = USB_C_CENTER_Z - USB_C_CUTOUT_H / 2.0 - 0.5
USB_C_NOTCH_Z1 = USB_C_CENTER_Z + USB_C_CUTOUT_H / 2.0 + 0.5
USB_C_NOTCH_HEIGHT = USB_C_NOTCH_Z1 - USB_C_NOTCH_Z0
assert USB_C_NOTCH_Z0 > FLOOR_T, "USB-C notch would dip into the floor slab"

# microSD slot Z-range (global), same -Y wall as the USB-C notch, same X
# center (MICROSD_SLOT_X below) -- stacked directly above it per the
# design brief, MICROSD_GAP_ABOVE_USBC clear of the notch's own top edge.
# Shared by build_tray() and build_lid() the same way the USB-C notch is
# (section 8): applied unconditionally in both, a no-op wherever there's
# no material at that Z, so it stays correct regardless of which part it
# actually falls in as the constants above change.
MICROSD_SLOT_Z0 = USB_C_NOTCH_Z1 + MICROSD_GAP_ABOVE_USBC
MICROSD_SLOT_Z1 = MICROSD_SLOT_Z0 + MICROSD_SLOT_H
assert MICROSD_SLOT_Z1 < EXTERNAL_H - CEIL_T, (
    "microSD slot (%.2f-%.2f) runs into the ceiling (%.2f) -- reduce "
    "MICROSD_GAP_ABOVE_USBC or MICROSD_SLOT_H" % (MICROSD_SLOT_Z0, MICROSD_SLOT_Z1, EXTERNAL_H - CEIL_T))


# ====================================================================
# 6. SNAP-FIT ENGINEERING CHECK
# ====================================================================

def snap_fit_strain():
    """Cantilever-beam snap-fit strain, using the standard first-order
    formula from plastics snap-fit design guides (e.g. Bayer/GE):

        strain = 1.5 * deflection * thickness / flex_length^2

    treating the lid's skirt as a cantilever FIXED where it meets the cap
    wall (its rigid, ceiling-attached end) and FREE at its lower tip,
    deflected outward by the bead's interference as it rides over the
    tray's bump during assembly. flex_length is the distance from that
    fixed end to where the bead actually pushes -- for a cantilever, only
    the material BETWEEN the fixed end and the push point bends; material
    beyond the push point just gets carried along. That distance is
    SNAP_TRUE_FLEX_LENGTH (section 5): ENGAGE_DEPTH minus BEAD_TIP_OFFSET,
    since the bead sits near the skirt's free tip but not exactly AT it --
    see BEAD_Z0's comment in section 5. Using plain ENGAGE_DEPTH here
    instead would overstate flex_length (understating strain, since strain
    scales as 1/L^2), which is why the true, shorter distance is used.
    Returns a dict with the computed strain, the allowable strain, and
    pass/fail.
    """
    strain = 1.5 * SNAP_INTERFERENCE * SNAP_SKIRT_T / (SNAP_TRUE_FLEX_LENGTH ** 2)
    allowable = ELONGATION_AT_BREAK * SNAP_STRAIN_SAFETY_FRACTION
    margin_pct = (allowable - strain) / strain * 100.0 if strain else float("inf")
    return {
        "strain": strain,
        "allowable": allowable,
        "passes": strain <= allowable,
        "margin_pct": margin_pct,
    }


def screen_snap_strain():
    """Same cantilever-beam formula as snap_fit_strain() above, applied to
    the screen retention wall's own detent (section 3's "Screen snap-fit
    detent") instead of the main tray/lid snap: fixed end where
    screen_wall meets the ceiling, free tip at the wall's bottom edge,
    true flex length = SCREEN_RETENTION_WALL_H minus SCREEN_SNAP_TIP_OFFSET
    (the detent sits near the free tip, not at it, same convention as
    BEAD_TIP_OFFSET), thickness SCREEN_WALL_T. Checked separately from
    snap_fit_strain() because both t and L differ from the main snap's
    skirt/bead."""
    true_flex_length = SCREEN_RETENTION_WALL_H - SCREEN_SNAP_TIP_OFFSET
    strain = 1.5 * SCREEN_SNAP_INTERFERENCE * SCREEN_WALL_T / (true_flex_length ** 2)
    allowable = ELONGATION_AT_BREAK * SNAP_STRAIN_SAFETY_FRACTION
    margin_pct = (allowable - strain) / strain * 100.0 if strain else float("inf")
    return {
        "strain": strain,
        "allowable": allowable,
        "passes": strain <= allowable,
        "margin_pct": margin_pct,
    }


# ====================================================================
# 7. GEOMETRY HELPERS (raw Part-module solids + booleans only)
# ====================================================================

def _vertical_edges(shape, height):
    """Return the shape's edges that run straight up in Z by `height` --
    i.e. the vertical corner edges of an extruded rectangular profile."""
    out = []
    for e in shape.Edges:
        p0, p1 = e.Vertexes[0].Point, e.Vertexes[1].Point
        if (abs(p0.x - p1.x) < 1e-6 and abs(p0.y - p1.y) < 1e-6
                and abs(abs(p0.z - p1.z) - height) < 1e-6):
            out.append(e)
    return out


def rounded_box(w, d, h, radius, origin=Vector(0, 0, 0)):
    """A w x d x h box with its 4 vertical edges filleted to `radius`."""
    box = Part.makeBox(w, d, h, origin)
    if radius <= 1e-6:
        return box
    edges = _vertical_edges(box, h)
    return box.makeFillet(radius, edges)


def horizontal_band_ring(outer_w, outer_d, outer_r, inset, band_h, z0, origin_xy):
    """A thin closed ring (outer rounded-rect minus a smaller concentric
    rounded-rect) of height `band_h` starting at z0. `inset` is how far
    the inner boundary sits inside the outer one on each side. Used to
    build both the tray's snap bead and the lid's mating groove cavity."""
    ox, oy = origin_xy
    outer = rounded_box(outer_w, outer_d, band_h, outer_r, Vector(ox, oy, z0))
    inner_r = max(outer_r - inset, 0.1)
    inner = rounded_box(outer_w - 2 * inset, outer_d - 2 * inset, band_h,
                         inner_r, Vector(ox + inset, oy + inset, z0))
    return outer.cut(inner)


def shelf_frame(w, d, rim_w, height, z0, origin_xy, floor_r=1.0):
    """A hollow rectangular frame (picture-frame ledge): outer footprint
    w x d, a rim `rim_w` wide all around, standing `height` tall from z0.
    A board dropped on top rests on the rim with open air below it down
    to the tray floor -- this is the 'shelf pocket' the brief asks for,
    as opposed to standoff posts."""
    ox, oy = origin_xy
    outer = rounded_box(w, d, height, floor_r, Vector(ox, oy, z0))
    inner_w, inner_d = w - 2 * rim_w, d - 2 * rim_w
    inner = Part.makeBox(inner_w, inner_d, height + 2, Vector(ox + rim_w, oy + rim_w, z0 - 1))
    return outer.cut(inner)


def stadium_slot_y(center_x, z0, width, height, y0, depth):
    """A stadium/capsule-shaped cutter (a rectangle with full-semicircle
    rounded ends, radius = height/2) in the X-Z plane, extruded through
    `depth` along +Y starting at y0. This is the real USB-C connector
    shape -- a flat rounded slot, not a sharp-cornered rectangle, which
    reads as a generic (USB-A-like) opening instead. Built from a box
    plus two cylinders rather than a wire+face, to avoid any 2D-sketch
    topology edge cases -- box/cylinder fuses have been reliable
    throughout this script, chamfered or filleted surfaces have not
    (see build_tray()'s bead comment)."""
    r = height / 2.0
    straight_len = width - height
    assert straight_len >= 0, "stadium width must be >= height (radius = height/2 needs room)"
    box = Part.makeBox(straight_len, depth, height, Vector(center_x - straight_len / 2.0, y0, z0))
    cyl1 = Part.makeCylinder(r, depth, Vector(center_x - straight_len / 2.0, y0, z0 + r), Vector(0, 1, 0))
    cyl2 = Part.makeCylinder(r, depth, Vector(center_x + straight_len / 2.0, y0, z0 + r), Vector(0, 1, 0))
    return box.fuse(cyl1).fuse(cyl2)


# ====================================================================
# 8. PART BUILDERS
# ====================================================================

def outer_footprint_origin():
    """External footprint origin so the internal cavity's (0,0) lands at
    (WALL_T, WALL_T) inside it."""
    return Vector(0, 0, 0)


def build_tray():
    """Bottom shell: floor + a perimeter wall that runs the FULL internal
    cavity height (its rim meets the ceiling directly, see section 5) +
    component shelves/fences + an inward snap bead near the rim + the
    USB-C notch."""
    # Solid block for the whole tray height, corners rounded first (cheap
    # and robust), cavities cut afterwards.
    solid = rounded_box(EXTERNAL_W, EXTERNAL_D, TRAY_EXTERNAL_H, CORNER_FILLET_OUTER)

    # Round the OUTER BOTTOM edge (where the floor's underside meets the
    # outer wall) -- this is what actually rests against a palm, not just
    # the vertical corners. Done here, on the plain solid before any other
    # feature exists, matching this file's established pattern: fillet/
    # chamfer operations go on the simplest shape available, not a fully-
    # featured one. See OUTER_EDGE_CHAMFER_STAGES's own comment for why
    # this is a multi-stage chamfer, not a true fillet. Wall extends in
    # +Z from the floor (Z=0), so direction=+1.
    solid = rounded_edge_chamfer(solid, 0.0, OUTER_EDGE_CHAMFER_STAGES, direction=1)

    # Hollow out the internal cavity above the floor.
    inner_r = max(CORNER_FILLET_OUTER - WALL_T, 0.1)
    cavity = rounded_box(INTERNAL_W, INTERNAL_D, TRAY_WALL_INTERNAL_H + 1, inner_r,
                          Vector(WALL_T, WALL_T, FLOOR_T))
    tray = solid.cut(cavity)

    # Snap bead: a ridge on the INSIDE of the tray's cavity wall, near the
    # rim, protruding INWARD into the cavity by SNAP_INTERFERENCE. The
    # lid's skirt (built in build_lid()) nests inside this same cavity and
    # rides past this bead on the way in -- see section 5's docstring for
    # why the bead has to live on the cavity wall (not the outside face)
    # for the two parts to actually make contact.
    bead_z0 = BEAD_Z0  # near the skirt's free tip -- see section 5 for why (strain-calc fix)
    # OVERLAP_EPS: the bead's outer boundary is grown by this much beyond
    # the cavity wall's own inner face, and "inset" grown by the same
    # amount, so the actual protrusion into the cavity (SNAP_INTERFERENCE)
    # is unchanged but the bead now has real volumetric overlap with the
    # tray's wall rather than an exactly-coincident face. Needed because
    # fuse()'ing the CHAMFERED bead onto the tray using an exactly
    # coincident face left 2 disconnected solids instead of 1 (an OCCT
    # tolerance issue, confirmed by testing: the unchamfered bead fused
    # cleanly, the chamfered one did not) -- and that 2-solid result then
    # corrupted every later boolean op on the tray (one fuse silently
    # returned an empty shape). A tiny guaranteed overlap sidesteps the
    # coincident-face case entirely.
    OVERLAP_EPS = 0.1
    bead_ring = horizontal_band_ring(
        INTERNAL_W + 2 * OVERLAP_EPS, INTERNAL_D + 2 * OVERLAP_EPS,
        inner_r + OVERLAP_EPS, SNAP_INTERFERENCE + OVERLAP_EPS,
        SNAP_BEAD_BAND_H, bead_z0, (WALL_T - OVERLAP_EPS, WALL_T - OVERLAP_EPS))
    # Chamfer the bead's top/bottom edges so it's a gentle ramp, not a
    # square step -- eases both insertion and removal. NOT a *fillet*
    # (constant-radius round): OCCT fillets a horizontal rim edge on a
    # plan-rounded rectangle by extending the same continuous chain
    # through the corner arcs (tangent-connected), and the resulting
    # corner blend geometrically bulges outward by close to the full
    # fillet radius (a torus-around-a-convex-corner effect), silently
    # growing/shrinking the cavity footprint by ~2x the radius and
    # invalidating the interference/strain numbers below. A chamfer cuts a
    # bounded flat facet instead and cannot bulge past the original
    # surface.
    bead_edges = [e for e in bead_ring.Edges if _is_horizontal_ring_edge(e)]
    try:
        bead_ring = bead_ring.makeChamfer(BEAD_CHAMFER_SIZE, bead_edges)
    except Part.OCCError:
        # Not cosmetic if this triggers: a square bead riding into a
        # chamfered groove has no lead-in ramp at all, which is exactly
        # what a rough/binding snap feels like -- see BEAD_CHAMFER_SIZE's
        # comment for the safe range.
        print("WARNING: bead chamfer failed (OCCT) -- tray bead is an "
              "UNCHAMFERED SQUARE ridge, not the smooth ramp this design "
              "relies on. Reduce BEAD_CHAMFER_SIZE and re-test.")
    tray = tray.fuse(bead_ring)

    # Component shelves, all on the tray floor. Battery and MCU sit side
    # by side on the floor (section 4); the display has NO shelf, post,
    # or wall in the tray at all -- see the module docstring's SUPPORT
    # note. It's adhesive-stacked directly on top of the battery+MCU row.
    #
    # MCU: plain floor-level shelf, same pattern used everywhere a
    # component sits directly on the floor.
    tray = tray.fuse(shelf_frame(
        MCU_D + 2 * FIT_CLEARANCE_XY, MCU_W + 2 * FIT_CLEARANCE_XY,
        1.5, MCU_SHELF_CLEARANCE, FLOOR_T,
        (WALL_T + MCU_X0 - FIT_CLEARANCE_XY, WALL_T + MCU_Y0 - FIT_CLEARANCE_XY)))

    # MCU retention: a U-shaped wall (back + 2 sides, open at the USB-C
    # front) so charging -- pushing a USB-C plug straight at the board --
    # is resisted by a floor-anchored wall, not just friction on the
    # shelf's flat ledge above. Uses MCU_RETENTION_CLEARANCE (0.15mm),
    # tighter than the general FIT_CLEARANCE_XY (0.30mm) used everywhere
    # else, and rises to MCU_TOP_Z (5.0mm here).
    mcu_x0 = WALL_T + MCU_X0 - MCU_RETENTION_CLEARANCE
    mcu_x1 = WALL_T + MCU_X0 + MCU_D + MCU_RETENTION_CLEARANCE
    mcu_back_y = WALL_T + MCU_Y0 + MCU_W + MCU_RETENTION_CLEARANCE
    backstop = Part.makeBox(
        mcu_x1 - mcu_x0, MCU_BACKSTOP_T, MCU_TOP_Z,
        Vector(mcu_x0, mcu_back_y, FLOOR_T))
    tray = tray.fuse(backstop)

    # Side guide walls: only the back MCU_SIDE_WALL_FRACTION of MCU's
    # length, overlapping OVERLAP_EPS_MCU into the backstop's own
    # footprint for a guaranteed fuse (same coincident-face pattern
    # documented at the snap bead, below) -- left open near the USB-C
    # edge so the connector and its cable clearance are never pinched.
    OVERLAP_EPS_MCU = 0.1
    side_wall_y0 = WALL_T + MCU_Y0 + MCU_W * (1.0 - MCU_SIDE_WALL_FRACTION)
    side_wall_y1 = mcu_back_y + OVERLAP_EPS_MCU
    left_side_wall = Part.makeBox(
        MCU_SIDE_WALL_T, side_wall_y1 - side_wall_y0, MCU_TOP_Z,
        Vector(mcu_x0 - MCU_SIDE_WALL_T, side_wall_y0, FLOOR_T))
    right_side_wall = Part.makeBox(
        MCU_SIDE_WALL_T, side_wall_y1 - side_wall_y0, MCU_TOP_Z,
        Vector(mcu_x1, side_wall_y0, FLOOR_T))
    tray = tray.fuse(left_side_wall)
    tray = tray.fuse(right_side_wall)

    # Battery retention wall: stands on the floor between the battery and
    # MCU zones, from the floor up to BATTERY_T (the battery's own
    # height) -- keeps the battery from sliding toward the MCU (and vice
    # versa), which is the only in-plane retention it has (nothing else
    # touches it; the battery has no shelf, since it's a solid cell that
    # needs no under-board clearance). Runs the battery's own Y span
    # (BATTERY_D), sitting flush at BATTERY_X0 + BATTERY_W and reaching
    # to MCU_X0 -- exactly BATTERY_WALL_T wide, so it also doubles as the
    # MCU zone's own -X boundary: wherever the MCU's own left_side_wall
    # (above) exists, this wall overlaps it (BATTERY_WALL_T (2.0mm) is
    # thicker than the 1.35mm gap between MCU_X0 and that side wall's
    # near face), a real volumetric overlap rather than a coincident
    # face, so the two fuse into one shared wall exactly as intended.
    battery_wall_x0 = WALL_T + BATTERY_X0 + BATTERY_W
    battery_wall_y0 = WALL_T + BATTERY_Y0
    battery_wall = Part.makeBox(
        BATTERY_WALL_T, BATTERY_D, BATTERY_T,
        Vector(battery_wall_x0, battery_wall_y0, FLOOR_T))
    tray = tray.fuse(battery_wall)

    # Cable pass-through for the battery's power leads, through the
    # battery/MCU wall -- same size/style as the switch column's own
    # wire_notch below, centered on the wall's length and mid-height.
    BATTERY_WIRE_NOTCH_W, BATTERY_WIRE_NOTCH_H = 6.0, 4.0
    battery_wire_y0 = battery_wall_y0 + BATTERY_D / 2.0 - BATTERY_WIRE_NOTCH_W / 2.0
    battery_wire_z0 = FLOOR_T + BATTERY_T / 2.0 - BATTERY_WIRE_NOTCH_H / 2.0
    battery_wire_cutter = Part.makeBox(
        BATTERY_WALL_T + 2.0, BATTERY_WIRE_NOTCH_W, BATTERY_WIRE_NOTCH_H,
        Vector(battery_wall_x0 - 1.0, battery_wire_y0, battery_wire_z0))
    tray = tray.cut(battery_wire_cutter)

    # Display: NOTHING is fused into the tray for it -- no posts, no
    # shelf, no wall. It rests adhesive-mounted directly on top of the
    # battery+MCU row, at DISPLAY_REST_Z (section 5). Its only retention
    # comes from the LID side (screen_lip + screen_wall, build_lid()).

    # Switch column: shelf_frame on the SWITCH_COL_W x SWITCH_COL_L
    # footprint beside the stack. Its shelf height
    # (SWITCH_PCB_BELOW_CLEARANCE) is DERIVED (section 5) and much taller
    # than the switches themselves need -- just unused clearance under
    # the switch PCB, harmless.
    # floor_r matches the lid skirt's own corner radius (skirt_r,
    # build_lid()) rather than the small default (1.0mm): the switch
    # column sits flush against the cavity's own far wall/corner, and the
    # skirt reaches down into this shelf's own Z range there, sweeping a
    # LARGER radius through that same corner than the shelf's default
    # radius would leave room for. Sharp corners here would overlap the
    # skirt (confirmed: ~30mm^3 via tray.common(lid)) -- matching the
    # radii removes the conflict at its source.
    # DERIVED (not a flat 2.0mm) so the shelf's inner pocket -- where the
    # switch PCB actually rests -- lands exactly on SWITCH_HOLE (14mm),
    # not 14.6mm: a flat 2.0mm rim only cancels SWITCH_PCB_MARGIN_Y, and
    # leaves the 2*FIT_CLEARANCE_XY added to the shelf's outer footprint
    # (line below) leaking straight into the inner opening instead of
    # being absorbed by the rim.
    SWITCH_SHELF_RIM_W = ((SWITCH_COL_W + 2 * FIT_CLEARANCE_XY) - SWITCH_HOLE) / 2.0
    switch_shelf_floor_r = max(CORNER_FILLET_OUTER - WALL_T - SKIRT_CLEARANCE, 0.1)
    tray = tray.fuse(shelf_frame(
        SWITCH_COL_W + 2 * FIT_CLEARANCE_XY, SWITCH_COL_L + 2 * FIT_CLEARANCE_XY,
        SWITCH_SHELF_RIM_W, SWITCH_PCB_BELOW_CLEARANCE, FLOOR_T,
        (WALL_T + SWITCH_COL_X0 - FIT_CLEARANCE_XY, WALL_T + SWITCH_COL_Y0 - FIT_CLEARANCE_XY),
        floor_r=switch_shelf_floor_r))

    # Wire pass-through: the switch column's shelf_frame is a continuous
    # ring (unlike the MCU's own open-front U-wall), so its wall facing
    # the battery+MCU row would otherwise block routing the switch wires
    # to the MCU. Cut a small notch through JUST that wall (the one
    # facing the row, -X side) so wires have a clear, deliberate path
    # from the switch PCB across ROW_GAP to the MCU, which now sits
    # immediately next door. Centered along the switch column's length,
    # mid-height in its shelf.
    wire_notch_w, wire_notch_h = 6.0, 4.0
    wire_notch_x0 = WALL_T + SWITCH_COL_X0 - FIT_CLEARANCE_XY - 1.0  # 1mm overshoot into the open gap
    wire_notch_depth = SWITCH_SHELF_RIM_W + 2.0  # punches cleanly through the rim wall
    wire_notch_y0 = WALL_T + SWITCH_COL_Y0 + SWITCH_COL_L / 2.0 - wire_notch_w / 2.0
    wire_notch_z0 = SWITCH_PCB_BELOW_CLEARANCE / 2.0 - wire_notch_h / 2.0
    wire_cutter = Part.makeBox(
        wire_notch_depth, wire_notch_w, wire_notch_h,
        Vector(wire_notch_x0, wire_notch_y0, wire_notch_z0))
    tray = tray.cut(wire_cutter)

    # Button divider: the lid's plate hole over these two switches is ONE
    # merged opening (build_lid()'s comment), so nothing up top separates
    # the two switches -- this wall, standing inside the switch shelf,
    # does that job instead:
    #   - 5mm thick (Y direction, the axis the switches are stacked on) --
    #     SWITCH_PITCH - SWITCH_HOLE = 19.05 - 14 = 5.05mm is the actual
    #     free gap between the two switch bodies, and 5mm fits it almost
    #     exactly.
    #   - Centered on the shelf's own Y-midpoint (the same midpoint
    #     wire_notch_y0 above is centered on, i.e. the gap between the two
    #     switches).
    #   - Half the shelf's INNER cavity width (X direction) long, anchored
    #     to the shelf's far (+X) inner wall and stopping at the cavity's
    #     own midpoint -- short of the near (-X) inner wall where
    #     wire_cutter (just above) punches through, so this wall can't
    #     block that cable path.
    #   - Sharp corners, matching the shelf's own corners just above.
    # Z-range: floor to SWITCH_PCB_BELOW_CLEARANCE -- flush with the
    # shelf/button-box top (not up to the plate plane), so it separates
    # the two switches through their below-PCB/hot-swap-socket zone
    # without poking up into the open finger/keycap space above the PCB.
    # ASSUMPTION: the actual switch PCB needs a matching keepout slot cut
    # into it at this X/Y position so it can still seat flush on the shelf
    # rim around this wall -- verify against the real PCB layout before
    # printing, since its outline isn't specified anywhere (section 2).
    BUTTON_DIVIDER_T = 5.0
    switch_inner_w = (SWITCH_COL_W + 2 * FIT_CLEARANCE_XY) - 2 * SWITCH_SHELF_RIM_W
    switch_inner_x0 = WALL_T + SWITCH_COL_X0 - FIT_CLEARANCE_XY + SWITCH_SHELF_RIM_W
    divider_len = switch_inner_w / 2.0
    divider_x0 = switch_inner_x0 + switch_inner_w - divider_len
    divider_y_mid = WALL_T + SWITCH_COL_Y0 + SWITCH_COL_L / 2.0
    divider_y0 = divider_y_mid - BUTTON_DIVIDER_T / 2.0
    divider_h = SWITCH_PCB_BELOW_CLEARANCE
    divider = Part.makeBox(divider_len, BUTTON_DIVIDER_T, divider_h,
                            Vector(divider_x0, divider_y0, FLOOR_T))
    tray = tray.fuse(divider)

    # USB-C notch through the -Y wall (the top of the case, the screen
    # row's own exterior-facing edge -- MCU is rotated so its USB-C short
    # edge faces this wall). Sized to USB_C_NOTCH_Z0/HEIGHT (section 5):
    # just the actual connector position plus a small placement-tolerance
    # margin. STADIUM-shaped (rounded ends), not a sharp rectangle -- a
    # sharp rectangle reads as a generic slot; the rounded-end "capsule"
    # is what actually looks like USB-C.
    usbc_cx = WALL_T + MCU_X0 + MCU_D / 2.0
    notch_w = USB_C_CUTOUT_W + 0.5  # +1mm clearance per side for the plug/cable
    cutter = stadium_slot_y(usbc_cx, USB_C_NOTCH_Z0, notch_w, USB_C_NOTCH_HEIGHT, -2.0, 12.0)
    tray = tray.cut(cutter)

    # microSD slot, same -Y wall, same X center as the USB-C notch,
    # MICROSD_GAP_ABOVE_USBC above it (section 5/2) -- same STADIUM shape
    # as the USB-C cutter for a clean, print-friendly rounded-end opening.
    sd_cutter = stadium_slot_y(usbc_cx, MICROSD_SLOT_Z0, MICROSD_SLOT_W, MICROSD_SLOT_H, -2.0, 12.0)
    tray = tray.cut(sd_cutter)

    return tray


def build_lid():
    """Top shell: a flat ceiling (with display window + switch plate
    holes), a full-width "cap wall" below it (the lid's OWN visible outer
    wall, matching the tray's profile so the two meet flush at the seam
    -- see section 5), and below THAT, a separate, narrower skirt that
    NESTS INSIDE the tray's cavity for ENGAGE_DEPTH, hidden, purely for
    the snap engagement. Local Z=0 is the skirt's free tip; the ceiling
    sits at the top, local Z=LID_EXTERNAL_H. main() translates the whole
    thing up by LID_PLACEMENT_Z to seat it for the preview."""
    ceiling = rounded_box(EXTERNAL_W, EXTERNAL_D, CEIL_T, CORNER_FILLET_OUTER,
                           Vector(0, 0, ENGAGE_DEPTH + LID_CAP_WALL_H))
    # Round the OUTER TOP edge (where the ceiling's top face meets the
    # outer wall) -- the other half of "comfortable in the hand" (see
    # OUTER_EDGE_CHAMFER_STAGES's comment, and the matching bottom-edge
    # treatment in build_tray()). Done here, on the plain ceiling solid
    # before fusing with anything else, same reasoning as always in this
    # file. Wall extends in -Z from the ceiling's top face, so
    # direction=-1.
    ceiling = rounded_edge_chamfer(ceiling, LID_EXTERNAL_H, OUTER_EDGE_CHAMFER_STAGES, direction=-1)

    # Cap wall: the lid's own visible outer wall, from the seam up to the
    # ceiling -- same OUTER footprint/profile as the tray's own wall
    # (build_tray()) so the two are flush and continuous at the seam, not
    # a visible step.
    inner_r = max(CORNER_FILLET_OUTER - WALL_T, 0.1)  # matches build_tray()'s cavity radius
    skirt_r = max(inner_r - SKIRT_CLEARANCE, 0.1)
    # The cavity is cut to match the SKIRT's own (SKIRT_CLEARANCE-inset)
    # footprint exactly, not the tray's full INTERNAL_W -- so it meets the
    # skirt at a flush, EXACTLY COINCIDENT boundary with no radial gap.
    # Cutting it at INTERNAL_W instead (matching the tray) would leave a
    # SKIRT_CLEARANCE-wide gap between the skirt's outer face and the cap
    # wall's inner face that never touches, so fuse()'ing them gives 2
    # disconnected solids instead of 1. A bridging ring sized to overlap
    # both sides of that gap doesn't work either -- its outer edge,
    # straddling the seam, ends up occupying the same space as the tray's
    # own wall just below the seam. Matching the cavity to the skirt's
    # footprint directly avoids both problems -- no gap, and nothing
    # reaches outside the tray's own hollow cavity radius, ever.
    cap_wall_outer = rounded_box(EXTERNAL_W, EXTERNAL_D, LID_CAP_WALL_H, CORNER_FILLET_OUTER,
                                  Vector(0, 0, ENGAGE_DEPTH))
    cap_wall_cavity = rounded_box(
        INTERNAL_W - 2 * SKIRT_CLEARANCE, INTERNAL_D - 2 * SKIRT_CLEARANCE, LID_CAP_WALL_H + 2, skirt_r,
        Vector(WALL_T + SKIRT_CLEARANCE, WALL_T + SKIRT_CLEARANCE, ENGAGE_DEPTH - 1))
    cap_wall = cap_wall_outer.cut(cap_wall_cavity)
    lid = ceiling.fuse(cap_wall)

    # Skirt: sized to slide inside the tray's INTERNAL_W x INTERNAL_D
    # cavity with a small running clearance, using the same corner radius
    # as that cavity so it nests flush. Its outer footprint is EXACTLY the
    # cap wall's cavity footprint above (same dimensions, same origin, same
    # radius) so the two meet at a flush, coincident boundary with no gap
    # -- see the long comment above cap_wall_cavity for why that matters.
    skirt_outer = rounded_box(
        INTERNAL_W - 2 * SKIRT_CLEARANCE, INTERNAL_D - 2 * SKIRT_CLEARANCE,
        ENGAGE_DEPTH, skirt_r, Vector(WALL_T + SKIRT_CLEARANCE, WALL_T + SKIRT_CLEARANCE, 0))
    # NOTE: this cavity MUST use a rounded corner too (matching skirt_r
    # minus the wall thickness), not a sharp Part.makeBox -- a sharp
    # cavity cut from a rounded outer wall makes the wall vanish at the
    # corners (the rounded outer surface is pulled in further than the
    # sharp cavity corner sticks out once SNAP_SKIRT_T < the corner's own
    # cut-in depth), splitting the ring into 4 disconnected straight
    # segments. Caught by checking len(skirt.Solids) == 4 instead of 1.
    skirt_cavity_r = max(skirt_r - SNAP_SKIRT_T, 0.1)
    skirt_cavity = rounded_box(
        INTERNAL_W - 2 * SKIRT_CLEARANCE - 2 * SNAP_SKIRT_T,
        INTERNAL_D - 2 * SKIRT_CLEARANCE - 2 * SNAP_SKIRT_T,
        ENGAGE_DEPTH + 2, skirt_cavity_r,
        Vector(WALL_T + SKIRT_CLEARANCE + SNAP_SKIRT_T, WALL_T + SKIRT_CLEARANCE + SNAP_SKIRT_T, -1))
    skirt = skirt_outer.cut(skirt_cavity)
    lid = lid.fuse(skirt)

    # Skirt-to-cap-wall bridge: even with skirt_outer and cap_wall_cavity
    # set to EXACTLY the same footprint, fuse()'ing two solids that only
    # share an exactly-coincident face -- no actual 3D overlap -- produces
    # 2 disconnected solids instead of 1 (the same failure mode as the
    # coincident-face bead issue, section 8, just a lateral/radial
    # coincidence instead of a horizontal one). Fixed with a small ring
    # reaching OVERLAP_EPS beyond the skirt's own outer footprint,
    # straddling the Z boundary, giving genuine volumetric overlap with
    # BOTH the skirt and the cap wall. Sized to stay well inside the
    # tray's actual cavity radius (max reach is INTERNAL_W - 0.1mm) so it
    # can never collide with the tray's own wall material.
    OVERLAP_EPS_BRIDGE = 0.15
    bridge_ring = horizontal_band_ring(
        INTERNAL_W - 2 * SKIRT_CLEARANCE + 2 * OVERLAP_EPS_BRIDGE,
        INTERNAL_D - 2 * SKIRT_CLEARANCE + 2 * OVERLAP_EPS_BRIDGE,
        skirt_r + OVERLAP_EPS_BRIDGE, SNAP_SKIRT_T + OVERLAP_EPS_BRIDGE,
        1.0, ENGAGE_DEPTH - 0.5,
        (WALL_T + SKIRT_CLEARANCE - OVERLAP_EPS_BRIDGE, WALL_T + SKIRT_CLEARANCE - OVERLAP_EPS_BRIDGE))
    lid = lid.fuse(bridge_ring)

    # Mating groove, cut into the skirt's OUTER face: a SHALLOW recess
    # that reaches SNAP_INTERFERENCE further out than the skirt's nominal
    # outer surface (to make room for the bead's tip) plus a small extra
    # bite (GROOVE_EXTRA_DEPTH) inward for a bit of positive engagement,
    # at the same global Z the tray's bead sits at (BEAD_Z0, section 5 --
    # near the skirt's free tip, not the rim, so the strain calculation's
    # flex-length assumption holds -- see snap_fit_strain()).
    # The pocket's inset is deliberately kept LESS than SNAP_SKIRT_T: an
    # inset of SNAP_SKIRT_T + SNAP_INTERFERENCE or more cuts deeper than
    # the skirt wall itself is thick and severs the skirt ring at the
    # groove band into disconnected solids. Keeping a real wall thickness
    # behind the pocket keeps the skirt one continuous tube.
    GROOVE_EXTRA_DEPTH = 0.4
    assert SNAP_INTERFERENCE + GROOVE_EXTRA_DEPTH < SNAP_SKIRT_T, (
        "groove would cut deeper than the skirt is thick -- reduce "
        "GROOVE_EXTRA_DEPTH or increase SNAP_SKIRT_T")
    groove_inset = SNAP_INTERFERENCE + GROOVE_EXTRA_DEPTH
    groove_z0_local = GROOVE_Z0_LOCAL
    groove_ring = horizontal_band_ring(
        INTERNAL_W - 2 * SKIRT_CLEARANCE + 2 * SNAP_INTERFERENCE,
        INTERNAL_D - 2 * SKIRT_CLEARANCE + 2 * SNAP_INTERFERENCE,
        skirt_r + SNAP_INTERFERENCE, groove_inset,
        SNAP_BEAD_BAND_H, groove_z0_local,
        (WALL_T + SKIRT_CLEARANCE - SNAP_INTERFERENCE, WALL_T + SKIRT_CLEARANCE - SNAP_INTERFERENCE))
    # Matching chamfer on the groove -- see the long comment in build_tray()
    # for why this is a chamfer and not a fillet.
    groove_edges = [e for e in groove_ring.Edges if _is_horizontal_ring_edge(e)]
    try:
        groove_ring = groove_ring.makeChamfer(BEAD_CHAMFER_SIZE, groove_edges)
    except Part.OCCError:
        print("WARNING: groove chamfer failed (OCCT) -- lid groove is an "
              "UNCHAMFERED SQUARE pocket. Reduce BEAD_CHAMFER_SIZE and re-test.")
    lid = lid.cut(groove_ring)

    # Display window: sized independently of SCREEN_W/SCREEN_L (the full
    # module footprint, 65x30, used for the case sizing above) -- fixed at
    # a smaller, explicit HOLE_W x HOLE_D instead, still centered over the
    # module footprint via SCREEN_X0/SCREEN_Y0. NOTE: active area is
    # DISPLAY_ACTIVE_W x DISPLAY_ACTIVE_D (48.55 x 23.71), so this leaves
    # only ~0.7mm/0.65mm bezel per side -- tight, verify against the real
    # module's black border before printing (a 0.5mm placement error would
    # start showing glass edge).
    HOLE_W, HOLE_D = 50.0, 25.0
    win_w = HOLE_W
    win_d = HOLE_D
    # Shifted 2mm off-center along X: closer to the case's exterior wall
    # (SCREEN_X0==0, the screen module's own flush edge, section 4) and
    # correspondingly farther from the switch column on the opposite (+X)
    # side of the same axis.
    WINDOW_X_SHIFT = 2.0
    win_x = WALL_T + SCREEN_X0 + (SCREEN_W - win_w) / 2.0 - WINDOW_X_SHIFT
    win_y = WALL_T + SCREEN_Y0 + (SCREEN_L - win_d) / 2.0
    # Rounded corners (WINDOW_CORNER_R) and a beveled top rim
    # (WINDOW_EDGE_CHAMFER_STAGES) -- the same "flat cut is sharp, curve
    # reads as finished" idea behind CORNER_FILLET_OUTER/
    # OUTER_EDGE_CHAMFER_STAGES on the case's own exterior, just sized
    # down for a 50x25mm opening instead of a 93x45mm case (both
    # constants, section 2). Rounding the corners can only make the
    # opening SMALLER there (material is added back at the corners, never
    # removed), so it can't eat into the tight ~0.7mm/0.65mm bezel margin
    # noted above -- safe regardless of how close that margin already is.
    # The rim bevel uses the exact same rounded_edge_chamfer() helper the
    # exterior edges use (section 7/9), applied to this cutting tool
    # BEFORE it's subtracted, same idiom as the snap bead/groove rings:
    # chamfering the tool's own top rim leaves a beveled entrance once
    # it's cut from the ceiling. Only the TOP rim (the side actually seen
    # and touched from outside) -- not the underside, which is where the
    # screen retention lip (below) is built flush against this same
    # win_w/win_d boundary; beveling that edge too would leave the lip's
    # own cut not lining up with the window's actual (now-tapered)
    # boundary at the top of its span.
    # Height is CEIL_T+1 (not the +2 overshoot used elsewhere in this file
    # for a plain straight cut) so the tool's TOP face lands exactly at
    # LID_EXTERNAL_H -- the ceiling's real outer surface, and the only
    # place rounded_edge_chamfer() has an edge to find and bevel from; the
    # bottom face still overshoots 1mm past the ceiling's underside for a
    # clean cut there.
    window = rounded_box(win_w, win_d, CEIL_T + 1, WINDOW_CORNER_R,
                          Vector(win_x, win_y, LID_EXTERNAL_H - CEIL_T - 1))
    window = rounded_edge_chamfer(window, LID_EXTERNAL_H, WINDOW_EDGE_CHAMFER_STAGES, direction=-1)
    lid = lid.cut(window)

    # Screen retention lip: a continuous picture-frame rib hanging down
    # from the ceiling's underside around the window, sized to the
    # display's own layout footprint (SCREEN_W/L +/- FIT_CLEARANCE_XY,
    # section 4) -- this is the display's only lateral confinement, since
    # the tray contributes no support or retention for it at all (see the
    # module docstring's SUPPORT note). It reaches down only SCREEN_LIP_H
    # from the ceiling, stopping SCREEN_LIP_CLEARANCE short of where the
    # module's top surface sits (DISPLAY_TOP_Z) -- deliberately NOT an
    # interference fit against the already-tight STACK_TOP_MARGIN; this
    # stops the module sliding sideways in its pocket, not clamps it
    # vertically.
    SCREEN_LIP_CLEARANCE = 0.2
    SCREEN_LIP_H = STACK_TOP_MARGIN - SCREEN_LIP_CLEARANCE
    assert SCREEN_LIP_H > 0, (
        "no room for a screen retention lip -- tighten SCREEN_LIP_CLEARANCE "
        "or STACK_TOP_MARGIN")
    lip_x0 = WALL_T + SCREEN_X0 - FIT_CLEARANCE_XY
    lip_y0 = WALL_T + SCREEN_Y0 - FIT_CLEARANCE_XY
    # SCREEN_LENGTH_EXTRA_CLEARANCE added entirely on the +X (far) side --
    # lip_x0 above is unchanged, so all the extra room appears at the
    # lip_x0+lip_w end. See its own comment (section 3) for why: the -X
    # side is already flush against the exterior wall with no slack.
    lip_w = SCREEN_W + 2 * FIT_CLEARANCE_XY + SCREEN_LENGTH_EXTRA_CLEARANCE
    lip_d = SCREEN_L + 2 * FIT_CLEARANCE_XY
    lip_z0 = LID_EXTERNAL_H - CEIL_T - SCREEN_LIP_H
    lip_outer = Part.makeBox(lip_w, lip_d, SCREEN_LIP_H, Vector(lip_x0, lip_y0, lip_z0))
    lip_inner = Part.makeBox(win_w, win_d, SCREEN_LIP_H + 2, Vector(win_x, win_y, lip_z0 - 1))
    screen_lip = lip_outer.cut(lip_inner)
    lid = lid.fuse(screen_lip)

    # Screen retention WALL: a taller, structural ring around the display
    # module's own footprint, hanging from the lid's ceiling down into the
    # hollow cap-wall cavity -- what the shallow lip above can't be, since
    # its depth is capped at STACK_TOP_MARGIN (a fraction of a mm) before
    # it would cut into the module's own physical body. This wall uses
    # lip_w/lip_d (the display's layout footprint, section 4) as its INNER
    # opening, so the module still drops through with the same clearance;
    # the wall material sits OUTSIDE that boundary, in room that's free on
    # 3 sides (Y top/bottom have several mm of margin; the +X side facing
    # the switch column has ROW_GAP to spare). The near/-X edge needs
    # nothing extra -- lip_x0 already overlaps into the case's own WALL_T
    # exterior wall there, so this ring's -X segment fuses harmlessly into
    # that existing solid wall.
    #
    # Z-range: from just above DISPLAY_REST_Z (plus SCREEN_WALL_CLEARANCE
    # of assembly-tolerance headroom) up to the ceiling -- the display has
    # nothing else in the tray at that Z range to collide with (section 5).
    # SCREEN_WALL_T/SCREEN_WALL_CLEARANCE/SCREEN_RETENTION_WALL_H are
    # module-level now (section 5) so screen_snap_strain() can share the
    # exact same cantilever length this geometry uses.
    screen_wall_z0 = LID_EXTERNAL_H - CEIL_T - SCREEN_RETENTION_WALL_H
    screen_wall_outer = rounded_box(
        lip_w + 2 * SCREEN_WALL_T, lip_d + 2 * SCREEN_WALL_T, SCREEN_RETENTION_WALL_H, 1.0,
        Vector(lip_x0 - SCREEN_WALL_T, lip_y0 - SCREEN_WALL_T, screen_wall_z0))
    screen_wall_inner = Part.makeBox(
        lip_w, lip_d, SCREEN_RETENTION_WALL_H + 2, Vector(lip_x0, lip_y0, screen_wall_z0 - 1))
    screen_wall = screen_wall_outer.cut(screen_wall_inner)

    # Gap in the +X segment (the one facing the switch column, closer to
    # the buttons): a 15mm through-gap centered on that segment's own
    # Y-midpoint, full wall thickness and full height. That segment's real
    # length is lip_d (SCREEN_L + 2*FIT_CLEARANCE_XY = 30.6mm at this
    # file's current constants), so a centered 15mm cut leaves ~7.8mm of
    # wall on each side.
    SCREEN_WALL_BUTTON_NOTCH_W = 15.0
    notch_y0 = lip_y0 + lip_d / 2.0 - SCREEN_WALL_BUTTON_NOTCH_W / 2.0
    notch_x0 = lip_x0 + lip_w - 0.5  # 0.5mm overshoot on each side for a clean through-cut
    notch_cutter = Part.makeBox(
        SCREEN_WALL_T + 1.0, SCREEN_WALL_BUTTON_NOTCH_W, SCREEN_RETENTION_WALL_H + 2,
        Vector(notch_x0, notch_y0, screen_wall_z0 - 1))
    screen_wall = screen_wall.cut(notch_cutter)

    # Screen snap-fit detent (section 3): two straight bars on the wall's
    # -Y and +Y inner faces only (see that section's comment for why not
    # all 4 sides), near screen_wall's own free tip -- SCREEN_SNAP_TIP_OFFSET
    # short of it, same "push the bead near the free end so the strain
    # formula's flex length is nearly the full cantilever" logic as the
    # main snap's BEAD_Z0 (build_tray()). Plain boxes, deliberately NOT
    # chamfered like the main bead/groove: at SCREEN_SNAP_INTERFERENCE's
    # scale (0.15mm), a lead-in bevel would be smaller than this printer's
    # resolvable feature size and risks a degenerate OCCT chamfer on such
    # a thin (0.15mm-proud) bump -- a square-edged bump is both safer to
    # generate and, if anything, gives slightly MORE of the "push it home"
    # resistance that's the actual point here. Each bar reaches
    # SCREEN_SNAP_OVERLAP_EPS INTO the wall (guaranteed volumetric fuse,
    # same coincident-face workaround as OVERLAP_EPS elsewhere) and
    # SCREEN_SNAP_INTERFERENCE beyond the wall's inner face, into the
    # pocket -- that's the actual interference the rigid module has to
    # push past on the way in.
    snap_z0 = screen_wall_z0 + SCREEN_SNAP_TIP_OFFSET
    near_bar = Part.makeBox(
        lip_w, SCREEN_SNAP_INTERFERENCE + SCREEN_SNAP_OVERLAP_EPS, SCREEN_SNAP_BAND_H,
        Vector(lip_x0, lip_y0 - SCREEN_SNAP_OVERLAP_EPS, snap_z0))
    far_bar = Part.makeBox(
        lip_w, SCREEN_SNAP_INTERFERENCE + SCREEN_SNAP_OVERLAP_EPS, SCREEN_SNAP_BAND_H,
        Vector(lip_x0, lip_y0 + lip_d - SCREEN_SNAP_INTERFERENCE, snap_z0))
    screen_wall = screen_wall.fuse(near_bar).fuse(far_bar)

    lid = lid.fuse(screen_wall)

    # Switch plate holes: each button's opening is LID_BUTTON_HOLE (19mm)
    # square, larger than SWITCH_HOLE (the 14x14mm plate spec that still
    # drives the PCB footprint). At the fixed SWITCH_PITCH (19.05mm) that
    # leaves only 0.05mm between two adjacent 19mm squares' edges, so
    # rather than cut N_SWITCHES separate boxes and rely on OCCT to fuse a
    # 0.05mm sliver cleanly out of the mesh, this cuts ONE rectangle sized
    # to span every button position -- a single hole by construction. The
    # switches are stacked along Y, so the merge is along Y; X width is
    # just LID_BUTTON_HOLE.
    sw_cx = WALL_T + SWITCH_COL_X0 + SWITCH_COL_W / 2.0
    first_cy = WALL_T + SWITCH_COL_Y0 + SWITCH_PCB_MARGIN_X + SWITCH_HOLE / 2.0
    last_cy = first_cy + (N_SWITCHES - 1) * SWITCH_PITCH
    hole_y0 = first_cy - LID_BUTTON_HOLE / 2.0
    hole_span_y = (last_cy - first_cy) + LID_BUTTON_HOLE
    hole = Part.makeBox(LID_BUTTON_HOLE, hole_span_y, CEIL_T + 2,
                         Vector(sw_cx - LID_BUTTON_HOLE / 2.0, hole_y0,
                                LID_EXTERNAL_H - CEIL_T - 1))
    lid = lid.cut(hole)

    # USB-C notch (on the -Y wall, see build_tray()): matches the tray's
    # notch in X/Y so the opening is continuous across whichever part(s)
    # it actually falls in -- currently entirely within the cap wall (the
    # connector sits above the seam), converted to the lid's own local
    # frame (local Z=0 is LID_PLACEMENT_Z in global terms). Same STADIUM
    # shape as the tray's cutter -- see build_tray()'s comment.
    usbc_cx = WALL_T + MCU_X0 + MCU_D / 2.0
    notch_w = USB_C_CUTOUT_W + 2.0
    notch_z0_local = USB_C_NOTCH_Z0 - LID_PLACEMENT_Z
    cutter = stadium_slot_y(usbc_cx, notch_z0_local, notch_w, USB_C_NOTCH_HEIGHT, -2.0, 12.0)
    lid = lid.cut(cutter)

    # microSD slot (see build_tray()): same X center and shape as the
    # USB-C notch, converted to the lid's own local Z frame the same way.
    sd_z0_local = MICROSD_SLOT_Z0 - LID_PLACEMENT_Z
    sd_cutter = stadium_slot_y(usbc_cx, sd_z0_local, MICROSD_SLOT_W, MICROSD_SLOT_H, -2.0, 12.0)
    lid = lid.cut(sd_cutter)

    return lid


def _is_horizontal_ring_edge(edge):
    """Edges of a horizontal_band_ring that run in a horizontal plane
    (i.e. the top/bottom rims of the ring, which is what we want to round
    into a bead profile) -- both endpoints share the same Z."""
    p0, p1 = edge.Vertexes[0].Point, edge.Vertexes[1].Point
    return abs(p0.z - p1.z) < 1e-6


def _edges_at_z(shape, z_level):
    """Edges of `shape` lying entirely in the horizontal plane at
    z_level -- used to select an outer perimeter rim (top or bottom face
    boundary) for chamfering, on a shape simple enough (no other feature
    at that exact Z) that this can't accidentally catch an unrelated
    internal edge."""
    out = []
    for e in shape.Edges:
        p0, p1 = e.Vertexes[0].Point, e.Vertexes[1].Point
        if abs(p0.z - z_level) < 1e-6 and abs(p1.z - z_level) < 1e-6:
            out.append(e)
    return out


def rounded_edge_chamfer(shape, z_level, sizes, direction):
    """Approximate a smooth ROUND on the horizontal rim at z_level (where
    a flat top/bottom face meets the outer wall) using a SEQUENCE of
    progressively smaller chamfers instead of one true fillet -- see
    OUTER_EDGE_CHAMFER's comment for why a true fillet reliably bulges
    this specific shape (a plan-rounded rectangle) instead of rounding it.
    Each stage chamfers the edge the previous stage just created, which
    sits further into the wall -- `direction` is +1 if the wall extends
    toward +Z from z_level (the tray's bottom edge) or -1 if it extends
    toward -Z (the lid's top edge). The cumulative effect is a multi-facet
    profile that reads as genuinely rounded rather than one flat bevel.
    sum(sizes) should stay comfortably under the wall thickness at
    z_level -- there's no assert here because the caller already knows
    that geometry; makeChamfer will raise on its own if a stage is too
    large for what's left."""
    current_z = z_level
    for size in sizes:
        edges = _edges_at_z(shape, current_z)
        shape = shape.makeChamfer(size, edges)
        current_z += direction * size
    return shape


# ====================================================================
# 9. SUMMARY / CHECKLIST
# ====================================================================

def print_summary():
    snap = snap_fit_strain()
    screen_snap = screen_snap_strain()
    print("=" * 72)
    print("ESP32-S3 PORTABLE CASE -- computed dimensions")
    print("=" * 72)
    print()
    print("Filament: %s" % ELONGATION_SOURCE)
    print()
    print("-- Footprint / layout --")
    print("External footprint : %.2f x %.2f mm" % (EXTERNAL_W, EXTERNAL_D))
    print("Internal cavity     : %.2f x %.2f mm" % (INTERNAL_W, INTERNAL_D))
    print("Battery+MCU row footprint: %.2f x %.2f mm at (%.2f, %.2f)" % (STACK_ROW_W, STACK_D, STACK_X0, STACK_Y0))
    print("  Battery (floor, retention wall): %.2f x %.2f mm at (%.2f, %.2f)" % (BATTERY_W, BATTERY_D, BATTERY_X0, BATTERY_Y0))
    print("  MCU (floor, shelf + U-wall): %.2f x %.2f mm at (%.2f, %.2f)" % (
        MCU_D, MCU_W, MCU_X0, MCU_Y0))
    print("  Screen (adhesive-stacked above the row, no posts) : %.2f x %.2f mm at (%.2f, %.2f)" % (SCREEN_W, SCREEN_L, SCREEN_X0, SCREEN_Y0))
    print("Switch column (beside the row): %.2f x %.2f mm at (%.2f, %.2f)" % (
        SWITCH_COL_W, SWITCH_COL_L, SWITCH_COL_X0, SWITCH_COL_Y0))
    print()
    print("-- Height (Z) budget, from tray floor top -- set by the battery+MCU+screen stack, not the switches --")
    print("Internal cavity height (= PCB-to-plate stack): %.2f mm" % INTERNAL_CAVITY_H)
    print("  MCU shelf clearance     : %.2f mm" % MCU_SHELF_CLEARANCE)
    print("  MCU thickness           : %.2f mm  -> MCU top at Z=%.2f" % (MCU_THICKNESS, MCU_TOP_Z))
    print("  battery thickness       : %.2f mm  -> battery top at Z=%.2f (rests flat on the floor)" % (BATTERY_T, BATTERY_TOP_Z))
    print("  display standoff        : %.2f mm  -> display resting height at Z=%.2f" % (DISPLAY_STANDOFF_H, DISPLAY_REST_Z))
    print("  display thickness       : %.2f mm  -> display top at Z=%.2f" % (DISPLAY_THICKNESS, DISPLAY_TOP_Z))
    print("  -> margin below plate: %.2f mm (deliberately tight)" % STACK_TOP_MARGIN)
    print("Switch PCB shelf (derived to keep the %.1fmm plate gap correct at this height): %.2f mm" % (
        PCB_TO_PLATE, SWITCH_PCB_BELOW_CLEARANCE))
    print("External case height (tray+lid, assembled)  : %.2f mm" % EXTERNAL_H)
    print("  VISIBLE SEAM at Z=%.2f mm (%.0f%% up the case)" % (
        TRAY_EXTERNAL_H, 100.0 * SEAM_FRACTION))
    print("  tray external height (floor to seam)        : %.2f mm" % TRAY_EXTERNAL_H)
    print("  lid external height (cap wall + ceiling, above the seam): %.2f mm" % (LID_CAP_WALL_H + CEIL_T))
    print("  lid external height total (incl. hidden skirt below the seam): %.2f mm" % LID_EXTERNAL_H)
    print("  lid's skirt is HIDDEN, nested inside the tray's cavity, reaching %.2fmm" % ENGAGE_DEPTH)
    print("  below the seam for the snap engagement only -- not visible from outside")
    print("  bead/groove sit near Z=%.2f (close to the skirt's free tip, not the seam --" % BEAD_Z0)
    print("  needed for the strain check below to be accurate, see snap_fit_strain())")
    print("Switch stack protrudes above outer case top : %.2f mm (expected -- see the module docstring's SWITCHES note)" % SWITCH_PROTRUSION_ABOVE_CASE)
    print()
    print("-- Snap-fit strain check (cantilever beam, Bayer/GE formula) --")
    print("skirt depth (ENGAGE_DEPTH) = %.2f mm, true flex length L (skirt depth minus" % ENGAGE_DEPTH)
    print("  BEAD_TIP_OFFSET) = %.2f mm, skirt thickness t = %.2f mm, interference d = %.2f mm" % (
        SNAP_TRUE_FLEX_LENGTH, SNAP_SKIRT_T, SNAP_INTERFERENCE))
    print("computed strain   : %.2f%%" % (snap["strain"] * 100))
    print("allowable strain  : %.2f%% (= %.0f%% of %.1f%% elongation-at-break)" % (
        snap["allowable"] * 100, SNAP_STRAIN_SAFETY_FRACTION * 100, ELONGATION_AT_BREAK * 100))
    print("result            : %s (%.0f%% margin)" % ("PASS" if snap["passes"] else "FAIL -- reduce interference or increase flex length", snap["margin_pct"]))
    print()
    print("-- Screen snap-fit detent strain check (same formula, screen_wall's own bars) --")
    print("wall cantilever (SCREEN_RETENTION_WALL_H) = %.2f mm, true flex length L (minus" % SCREEN_RETENTION_WALL_H)
    print("  SCREEN_SNAP_TIP_OFFSET) = %.2f mm, wall thickness t = %.2f mm, interference d = %.2f mm" % (
        SCREEN_RETENTION_WALL_H - SCREEN_SNAP_TIP_OFFSET, SCREEN_WALL_T, SCREEN_SNAP_INTERFERENCE))
    print("computed strain   : %.2f%%" % (screen_snap["strain"] * 100))
    print("allowable strain  : %.2f%% (= %.0f%% of %.1f%% elongation-at-break)" % (
        screen_snap["allowable"] * 100, SNAP_STRAIN_SAFETY_FRACTION * 100, ELONGATION_AT_BREAK * 100))
    print("result            : %s (%.0f%% margin)" % (
        "PASS" if screen_snap["passes"] else "FAIL -- reduce interference or move the detent nearer the free tip",
        screen_snap["margin_pct"]))
    print()
    print("-- Assumed / generic figures (not in HARDWARE.md) --")
    for name, val, note in [
        ("Display module thickness", DISPLAY_THICKNESS, "e-paper HAT glass+PCB, no pin header assumed"),
        ("MCU assembled thickness", MCU_THICKNESS, "XIAO board + antenna/shield + solder"),
        ("MCU USB-C connector center height", USB_C_CENTER_Z_ABOVE_SHELF, "above MCU shelf -- verify against real board"),
        ("microSD slot width", MICROSD_SLOT_W, "11mm card + slide clearance -- verify against real board"),
        ("microSD slot height", MICROSD_SLOT_H, "card thickness + holder margin -- verify against real board"),
        ("Switch PCB thickness", SWITCH_PCB_THICKNESS, "standard FR4"),
        ("PCB-to-plate gap", PCB_TO_PLATE, "universal keyboard-plate convention"),
        ("Switch key pitch", SWITCH_PITCH, "standard 0.75in / 19.05mm keyboard pitch"),
        ("Switch housing height above PCB", SWITCH_HOUSING_ABOVE_PCB, "informational, Cherry MX typical"),
        ("Below-switch-PCB clearance", SWITCH_PCB_BELOW_CLEARANCE, "hot-swap socket + plunger pin protrusion"),
    ]:
        print("  %-38s %6.2f mm  (%s)" % (name, val, note))
    print()
    print("-- Pre-print checklist --")
    print("  [ ] Print a small test coupon (~15mm of perimeter wall, one")
    print("      switch plate hole) to verify the %.1fmm snap interference" % SNAP_INTERFERENCE)
    print("      and the 14x14mm plate-hole fit on YOUR printer before the full print.")
    print("  [ ] Confirm actual e-ink module thickness and MCU thickness against")
    print("      the physical parts -- both are ASSUMPTIONS above, not datasheet values.")
    print("  [ ] Confirm the XIAO's USB-C connector Z-position against the real board;")
    print("      the cutout has %.1fmm of height to absorb a modest placement error." % USB_C_CUTOUT_H)
    print("  [ ] Confirm the microSD slot's actual position on the Sense board -- its")
    print("      opening is placed %.1fmm above the USB-C notch by assumption, not a" % MICROSD_GAP_ABOVE_USBC)
    print("      measured board position; re-check card insertion/removal clears the case.")
    print("  [ ] If this case will be opened/closed often, consider printing the LID")
    print("      in PETG (elongation-at-break ~20-30%%) instead of PLA (%.1f%%) for a" % (ELONGATION_AT_BREAK * 100))
    print("      more durable snap; re-run with ELONGATION_AT_BREAK adjusted to check margin.")
    print("  [ ] Slice with >=3 perimeters on the lid skirt / tray bead region so the")
    print("      %.1fmm flex wall is solid, not sparse-infill." % SNAP_SKIRT_T)
    print("  [ ] Same for the screen retention wall (screen_wall, %.1fmm thick) -- the" % SCREEN_WALL_T)
    print("      new %.2fmm snap detent on its long sides needs solid perimeters too," % SCREEN_SNAP_INTERFERENCE)
    print("      not sparse infill, to actually flex/spring instead of just crushing.")
    print("  [ ] The display is adhesive/foam-tape mounted with no posts, shelves, or")
    print("      walls holding it up in the tray -- make sure the adhesive bond is solid")
    print("      before closing the case; nothing else registers its vertical position.")
    print("      The battery rests against its retention wall in-plane but is still")
    print("      loose in Z -- tape it down too.")
    print("=" * 72)


# ====================================================================
# 10. MAIN: build, validate, export
# ====================================================================

def export_stl(shape, path, linear_deflection=0.05, angular_deflection=0.3):
    import MeshPart
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=linear_deflection,
                                   AngularDeflection=angular_deflection, Relative=False)
    mesh.write(path)


def main():
    if not snap_fit_strain()["passes"]:
        print("WARNING: snap-fit strain check FAILS with current constants -- "
              "the geometry will still be generated, but see print_summary().")
    if not screen_snap_strain()["passes"]:
        print("WARNING: screen snap-fit detent strain check FAILS with current "
              "constants -- the geometry will still be generated, but see print_summary().")

    print_summary()

    doc = App.newDocument("ESP32CaseGen")

    print("Building tray...")
    tray = build_tray()
    if not tray.isValid():
        print("WARNING: tray solid failed OCCT validity check (isValid() == False).")

    print("Building lid...")
    lid = build_lid()
    if not lid.isValid():
        print("WARNING: lid solid failed OCCT validity check (isValid() == False).")

    out_dir = _SCRIPT_DIR
    bottom_path = os.path.join(out_dir, "case_bottom.stl")
    top_path = os.path.join(out_dir, "case_top.stl")
    fcstd_path = os.path.join(out_dir, "case_preview.FCStd")

    print("Exporting %s ..." % bottom_path)
    export_stl(tray, bottom_path)
    print("Exporting %s ..." % top_path)
    export_stl(lid, top_path)

    # NOTE on the two files above: each is exported zeroed to its own
    # print-bed contact face (tray floor at Z=0; lid's skirt tip at its
    # own local Z=0) -- that's deliberate and correct for slicing them as
    # two independent print jobs. It also means loading both STLs
    # straight into a generic viewer/slicer WITHOUT repositioning one of
    # them will show them sitting at the wrong relative height (both
    # starting at Z=0 instead of the lid seated LID_PLACEMENT_Z above the
    # tray) -- looks like a fit mismatch, isn't one. The combined file
    # below exists purely to check the fit visually in any STL viewer.
    lid_placed = lid.copy()
    lid_placed.translate(Vector(0, 0, LID_PLACEMENT_Z))
    assembled_path = os.path.join(out_dir, "case_assembled_preview.stl")
    print("Exporting %s (visual fit-check only, NOT for printing) ..." % assembled_path)
    export_stl(Part.makeCompound([tray, lid_placed]), assembled_path)

    tray_obj = doc.addObject("Part::Feature", "CaseBottom")
    tray_obj.Shape = tray
    lid_obj = doc.addObject("Part::Feature", "CaseTop")
    lid_obj.Shape = lid_placed
    doc.recompute()
    doc.saveAs(fcstd_path)
    print("Saved %s" % fcstd_path)

    print()
    print("Done. Bounding boxes:")
    print("  tray: %s" % tray.BoundBox)
    print("  lid : %s" % lid.BoundBox)


if __name__ == "__main__":
    if "--summary" in sys.argv:
        print_summary()
    else:
        main()
else:
    # Pasted into the FreeCAD Python console or run as a Macro: __name__
    # won't be "__main__", so just run it.
    if "--summary" in sys.argv:
        print_summary()
    else:
        main()
