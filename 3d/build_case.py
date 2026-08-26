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
WHAT CHANGED FROM THE BRIEF, AND WHY (read this before printing)
====================================================================

1. SWITCHES ARE MOUNTED "PLATE STYLE", NOT FULLY ENCLOSED.
   Cherry MX-family switches are designed to poke *through* a mounting
   plate: PCB -> 5 mm air gap -> plate (a 14x14 mm hole) -> switch upper
   housing and stem rise ~6.6 mm proud of the plate's outer face. That is
   how every mechanical keyboard works, and it is far more sensible here
   than trying to bury an 18 mm-tall switch stack inside a fully closed
   box. So the LID's outer face *is* the plate: it has two 14x14 mm holes
   the switches clip into, and the switches (with a keycap you add, or
   bare-stem) stick up above the case surface by design. This keeps the
   case a flat, uniform-height prism (see point 2) instead of needing a
   stepped/two-tier top -- a stepped shell would look nicer but adds a
   lot of boolean/fillet risk for a first-print part, and the brief did
   not ask for it.

2. UNIFORM CASE HEIGHT, NOT A TALLEST-COMPONENT-DRIVEN HEIGHT.
   Because the switches vent through the plate (point 1), the internal
   cavity only has to clear the *plate gap* (10.6 mm, see
   INTERNAL_CAVITY_H below), not the switch's full housing height
   (18+ mm). The battery, display module and MCU all fit comfortably
   inside that 10.6 mm with room to spare -- see print_summary() for the
   per-component margin. This is what "minimize the footprint against
   real dimensions" turned into in the Z axis too.

3. UNSPECIFIED THICKNESSES ARE FLAGGED, NOT GUESSED SILENTLY.
   HARDWARE.md gives XY footprints for the display module and the MCU,
   but not their Z thickness, and doesn't specify a switch-PCB size at
   all. Every such number below is a named constant with an "ASSUMPTION"
   or "STANDARD, not from HARDWARE.md" comment, and they are all also
   listed together in print_summary() under "Assumed / generic figures"
   so nothing is buried. Two numbers matter enough to call out here:
     - PCB-to-plate gap = 5.0 mm and plate-hole = 14.0 mm square are the
       universal mechanical-keyboard convention (not a Cherry Silent Blue
       or YMDK-socket-specific figure, but the geometry both parts are
       designed to).
     - Filament elongation-at-break (11.2%) *is* a real datasheet number,
       read from HARDWARE.md, used directly in the snap-fit strain
       calculation below -- not a generic PLA figure.

4. PLA IS A MARGINAL MATERIAL FOR A REPEATED-USE SNAP FIT, AND THIS
   DESIGN SAYS SO EXPLICITLY. PLA's 11.2% elongation-at-break is roughly
   3-5x lower than ABS or PETG. A snap-fit designed to the same
   deflection you'd use in ABS will crack a PLA lip after a handful of
   open/close cycles. To stay safely inside PLA's real limit, the
   cantilever strain calculation below (see snap_fit_strain()) targets
   only ~30% of PLA's ultimate elongation as the allowable design strain
   (a fatigue/repeated-cycle margin, not a one-shot-assembly margin).
   That constrains the interference to a modest 0.5 mm and pushes the
   flex length to 6 mm to keep strain low -- i.e. a deliberately gentle,
   low-force snap rather than an aggressive ABS-style hook. If the
   printed part will be opened and closed often (this is a wearable/
   portable device, so: yes), consider printing the lid in PETG even if
   the rest is PLA; the snap geometry parametrizes cleanly either way
   (just raise ELONGATION_AT_BREAK below to PETG's ~20-30% and re-run
   --summary to see the new margin).

5. NO ALIGNMENT PINS -- CONFIRMED, NOT JUST OMITTED. The continuous
   bead-and-groove perimeter (see build_snap_features()) constrains the
   lid to the tray in X and Y (the groove is a close XY fit around the
   bead) as soon as it's more than ~1 mm seated, and the plate-hole /
   switch-housing engagement adds a second independent XY registration
   near the switches. Separate cylindrical pins would be redundant per
   the brief, and were left out.

6. THE SNAP IS A SYMMETRIC CHAMFERED BEAD-IN-GROOVE, NOT A BARBED HOOK.
   A barbed/sawtooth hook (steep release face) is easy to press together
   but hard or destructive to pull apart. The brief asks for something
   "low profile with a curve structure so is easy to mount and
   disassemble" -- i.e. reversible -- so both flanks of the bead and
   groove are identically chamfered (equal lead-in and lead-out angles),
   not a curved fillet -- see the comment in build_tray() for why a true
   filleted round was tried and rejected (it silently bulges the part's
   outer footprint at the rounded corners, an OCCT geometry artifact, not
   a deliberate choice). A chamfer still gives a gentle, symmetric ramp
   instead of a sharp square step, which is what actually delivers "easy
   to mount and disassemble"; it trades a little retention force for
   genuine reversibility, the right trade for a device opened for battery
   swaps/reprogramming.

7. UNVERIFIED FIT: the 14x14 mm plate hole is the *nominal* Cherry MX
   dimension for laser-cut steel; FDM parts print undersized/oversized
   depending on your printer's calibration, and the 0.5 mm snap
   interference is a first-pass number, not a measured one. Print a
   small test coupon (see print_summary()'s checklist) with one plate
   hole and ~15 mm of the snap perimeter before committing to a full
   3-hour print of both shells.

8. PORTRAIT LAYOUT: SCREEN + SWITCHES SIDE BY SIDE, MCU NESTED UNDER
   THE SCREEN, BATTERY IN ITS OWN ROW -- NOT UNDER THE SCREEN. A later
   revision asked for a narrower, portrait-oriented case: display module
   rotated 90 deg (so its 30mm side is the case width), the 2 switches
   stacked vertically next to the screen's long edge instead of below it,
   and the MCU and battery both tucked underneath the screen to remove
   their footprint from the plan view entirely.
     - MCU-under-screen WORKS, with real margin: MCU shelf + 4mm board
       tops out at 5.0mm above the floor; the display then needs 4mm
       more, landing at 9.0mm against the fixed 10.6mm PCB-to-plate
       budget (point 2) -- 1.6mm to spare. The display sits on its own
       elevated shelf frame (rim height = MCU shelf height + MCU
       thickness), NOT directly on the MCU board, so the display's
       weight never bears on the PCB.
     - BATTERY-under-screen DOES NOT FIT, for two independent reasons,
       both hard geometry, not a preference: (a) battery (6.3mm) +
       display (4mm) = 10.6mm, using the ENTIRE height budget with zero
       margin for a shelf/divider between a LiPo pouch cell and the
       display glass -- not something to build without a real separator;
       (b) the battery's narrow dimension (34.5mm) is already 4.5mm
       *wider* than the portrait screen (30mm), so it doesn't fit under
       the screen in plan either, independent of height. The battery
       therefore keeps its own row below the screen+switch block.
   Net result: footprint drops from 75.05x104.5mm to ~65x112.5mm --
   noticeably narrower for a one-hand portrait grip (the main goal),
   modestly less total area, at the cost of being somewhat longer. Case
   height (14.6mm) is unaffected -- it was and remains set by the switch
   plate-gap requirement (point 1/2), independent of this XY replan.

9. COMPACT / NEAR-SQUARE LAYOUT: A 90x60mm REQUEST ISN'T REACHABLE, SO
   THIS TARGETS THE SMALLEST REAL PACKING INSTEAD (~82.5 x 80.5mm). The
   90x60mm ask runs into the same kind of hard floor as point 8: the
   display module's short side (30mm) and the battery's short side
   (34.5mm) sum to 64.5mm, and because they can't Z-stack (point 8),
   *some* axis of the case has to be at least that long once you add any
   gap, border, or wall -- already past a 60mm target before switches or
   margins even enter the picture. That's arithmetic, not a design
   choice, so rather than force-fit 60mm and silently produce a case that
   doesn't hold the hardware, this targets the smallest footprint an
   exhaustive-by-hand search of plausible packings actually found:
     - Tried: display+switches paired (the portrait layout, point 8) with
       battery alone below -> ~67x112.5mm (elongated, previous revision).
     - Tried: display+battery stacked in a shared column with switches
       beside -> ~97x76mm (the leftover space beside the short switch
       column next to the tall display+battery stack is wasted).
     - Used: display ALONE in one row, battery+switches PAIRED
       side-by-side in the other -> ~82.5x80.5mm. This pairs the two
       *shorter* items together so neither row wastes much space against
       the other, which is what actually shrinks the footprint (not just
       shuffling which component is "under" which).
   The screen is back to its natural LANDSCAPE orientation (65x30, not
   rotated) since pairing battery+switches -- not the screen -- is what
   makes row 2 wide, so there's no more reason to rotate the screen. The
   MCU still nests under the screen exactly as in point 8 (unaffected --
   that margin depends only on Z, not on this XY replan); it's rotated
   90deg in-plane so its USB-C edge faces the case's -Y (top) wall instead
   of -X, since that's now the screen row's own exterior-facing edge.
   Component margins were also tightened (switch-PCB margin 4/5mm ->
   3mm each; BORDER and ROW_GAP 3.0mm -> 2.5mm) as part of chasing this
   target -- still real clearance, just less generous than points 1-8's
   first pass.
   Case height (14.6mm) is unaffected, same reasoning as point 8.

   Two more geometry bugs surfaced getting the nested-skirt nested-under
   version of this layout to actually export a valid solid (both are
   fixed and asserted/commented at their exact location in the code, not
   just narrated here):
     - build_lid()'s skirt cavity cut used a SHARP-cornered box against a
       ROUNDED-cornered outer wall. At the corners, the rounding pulls the
       outer surface in further than the sharp cavity corner sticks out,
       so the wall vanishes there, splitting the skirt into 4 disconnected
       pieces. Fixed by rounding the cavity cut to match (same pattern
       used everywhere else -- always round both sides of a shell cut
       with a consistent offset, never mix sharp and rounded).
     - The bead/groove chamfer size (originally tuned to nearly reach the
       band's half-height, for the most pronounced ramp) turned out to be
       numerically fragile on the groove's thin ring wall at this
       geometry: an invalid split solid at 0.6mm, a hard OCCT exception at
       0.75mm, clean at 0.4mm -- all confirmed by direct testing, not
       guessed. Also, fuse()'ing the CHAMFERED bead onto the tray (as
       opposed to an unchamfered one, which fused cleanly) left the two
       as separate touching-but-unmerged solids -- an OCCT coincident-
       face tolerance issue -- which then silently corrupted a LATER,
       unrelated fuse (the display shelf) into an empty shape with no
       exception raised. Fixed by (a) using a conservative, tested-safe
       BEAD_CHAMFER_SIZE (0.3mm) and (b) giving the bead a small
       guaranteed volumetric overlap into the wall (OVERLAP_EPS = 0.1mm)
       instead of relying on an exactly coincident face. Both fixes are
       now general (BEAD_CHAMFER_SIZE and the overlap pattern), not
       specific to this layout, and both are covered by print_summary()
       and the isValid()/solid-count checks already wired into main().

   Also added: case_assembled_preview.stl, a compound of both parts in
   their correct assembled position, purely for visually checking the
   fit in any STL viewer -- see the "Outputs" note above for why
   case_bottom.stl and case_top.stl loaded together, unmodified, will
   look misaligned (each is intentionally zeroed to its own print-bed
   contact face, which is correct for slicing but not for eyeballing the
   mate).

10. 85x60mm: WIDTH IS REACHABLE, LENGTH STILL ISN'T -- AND THE MCU WAS
    NEVER THE REASON. A later request for 85x60mm noted the XIAO's small
    footprint and asked why the case was still that big. To be clear: the
    MCU was already contributing ZERO footprint as of point 8 -- it's
    nested entirely under the display and has been since the portrait
    revision. The case size comes from the DISPLAY MODULE (65x30mm,
    HARDWARE.md) and the BATTERY (51x34.5mm, HARDWARE.md), plus the
    switch PAIR's standard 19.05mm pitch -- none of which involve the
    MCU at all.
      Concretely, even at a hypothetical ZERO margin, zero gap, and zero
    wall thickness (not buildable, just a lower bound): 2 switches at
    19.05mm pitch need >=33.05mm of PCB length by themselves, and pairing
    that with the display's own 30mm depth already floors the content
    length at 63mm -- over the 60mm target before a single millimeter of
    real margin, gap, or wall is added. So 60mm is off the table
    regardless of how this is packed.
      85mm of width, on the other hand, had real slack (point 9's layout
    used 82.5mm), so margins were tightened further to use that
    headroom: SWITCH_PCB_MARGIN_X/Y 3.0mm -> 2.0mm, ROW_GAP and BORDER
    2.5mm -> 2.0mm (WALL_T stayed at 2.0mm -- that's a structural
    minimum for a printed snap-fit wall, not a packing margin, and
    shouldn't be cut further). Net result: ~79 x 77mm, comfortably under
    the 85mm width cap with room to spare, and as close to 60mm length as
    the switch-pitch/display-depth floor allows. Everything else about
    the layout (point 9's row arrangement, the MCU-under-display nesting,
    the snap-fit geometry) is unchanged -- this was purely a margin
    tightening pass, re-verified with the same isValid()/solid-count/
    overlap checks as every revision before it.

11. FULL BATTERY-MCU-DISPLAY Z-STACK, SWITCHES BESIDE IT -- CASE GROWS
    TO ~20.3mm TALL. A later request asked for both switches next to the
    screen (not paired with the battery, point 9/10's arrangement) and
    for the battery to also fold in under the MCU (which was already
    under the screen) to remove its footprint entirely: floor-to-ceiling,
    battery -> MCU -> screen, switches beside that whole column.
      This does NOT fit in the 10.6mm height point 1-10 used (set by the
    switch plate-gap requirement): battery (6.3mm) + MCU (4mm) + display
    (4mm) = 14.3mm of pure component thickness alone, before any of the
    standoff clearance a real stack needs. Confirmed and presented to the
    user as a choice before building: keep the 14.6mm case and battery in
    its own row (simpler, no new structural risk), or grow the case to
    fit the full stack. The user chose to grow the case.
      The real Z stack, including standoff clearance (not just component
    thickness), from the tray floor:
        + BATTERY_SHELF_CLEARANCE (0.5mm, tape/adhesive) + BATTERY_T
          (6.3mm) = battery top, Z=6.8
        + MCU_SHELF_CLEARANCE (1.0mm -- NOT optional: without it the
          MCU's underside, solder joints and all, would rest flush on
          the battery pouch's top surface) + MCU_THICKNESS (4.0mm)
          = MCU top, Z=11.8
        + DISPLAY_THICKNESS (4.0mm, display rests directly on posts at
          the MCU's top, no extra standoff, same convention point 8
          used) = display top, Z=15.8
        + STACK_TOP_MARGIN (0.5mm, deliberately tight, matching the
          tightness accepted everywhere else in this design) =
          INTERNAL_CAVITY_H = 16.3mm
      External case height: FLOOR_T + 16.3 + CEIL_T = 20.3mm, up from
    14.6mm (+39%). This is taller than the ~19.3mm estimate given when
    presenting the choice -- that estimate didn't yet account for
    MCU_SHELF_CLEARANCE (the standoff above the battery), which turned
    out to be necessary once worked through properly; flagging the
    correction here rather than quietly using the smaller number.
      The switch PCB's own shelf is DERIVED (section 5) from this new,
    much taller cavity, so its plate gap (PCB_TO_PLATE, 5mm) stays
    correct -- it just means a lot of unused clearance under the switch
    PCB now, which is harmless.
      STRUCTURAL APPROACH -- why corner posts, not shelf_frame's ring:
    shelf_frame() (used for MCU-under-display in point 8, and for the
    switch PCB and battery here) builds a continuous ring whose walls are
    solid for the full height from z0 to z0+height. That's fine when
    nothing else occupies the footprint underneath. Here, the MCU's
    shelf needs to reach UP AND OVER the battery -- a full ring would run
    solid from the floor, colliding with the battery pouch across its
    entire perimeter. A new helper, corner_posts(), holds the MCU (and,
    above it, the display) up on 4 small square posts (3mm for the MCU,
    4mm for the display) instead of a ring. The MCU's posts are an
    accepted minor intrusion into the battery's nominal footprint --
    unavoidable, since the MCU sits centered above the battery's middle,
    but small (4 x 3x3mm = 36mm^2, ~2% of the battery's own footprint)
    and a flexible LiPo pouch tolerates small localized standoffs fine
    (common in real product design). The display's posts, by contrast,
    land in the margin strips beside the battery (the display, at 65mm
    wide, is wider than the battery's 51mm) and clear it entirely with
    no intrusion at all -- verified by construction, not assumed.
      Layout: since battery+MCU+display now share one XY footprint (just
    at different Z), the plan view collapses to a single row: the stack
    (65 x 34.5mm, the bounding box of the display's width and the
    battery's depth) beside the switch column. Net footprint: see
    print_summary() for the exact number this run -- expect noticeably
    smaller than point 10's 79x77mm in one dimension, taller in the
    other, and the case itself is ~39% thicker. This is the real
    trade-off of trading case height for footprint, not a free win.

12. USB-C NOTCH SHRUNK (~16mm -> ~9mm TALL); WIRE PASS-THROUGH ADDED FOR
    THE SWITCHES. Two follow-up fixes once the taller stacked case (point
    11) was built:
      - The USB-C notch was cut FULL WALL HEIGHT (floor to rim) in every
        revision through point 11, specifically to guarantee it also
        interrupted the snap bead near the rim (see the old comment,
        still findable in git history). That was reasonable when the
        wall was ~14-18mm tall and the connector's own 6mm opening was a
        large fraction of it; on THIS case's 18.3mm wall it produced a
        visibly oversized ~16mm-tall opening for a 6mm port. Fixed:
        USB_C_NOTCH_Z0/Z1 (section 5) now bound the notch to the actual
        connector position (with a small placement-tolerance margin) up
        to just past the bead band -- ~9.1mm, not the full wall. Still
        taller than the bare 6mm port because the bead genuinely sits
        only ~0.5mm above the connector's own top at this case height
        (not enough room for a separate thin wall between two openings
        without an unprintable sliver), but a real, deliberate size, not
        an arbitrary full-height cut. Both build_tray() and build_lid()
        now share these Z bounds instead of computing overshoots
        independently, so the two openings stay in lock-step by
        construction if any of the underlying constants change.
      - No path existed for wiring the switches to the MCU: the switch
        column's shelf_frame is a continuous ring (unlike the stack's
        corner posts), so its wall facing the stack fully blocks direct
        routing. Added a small (6x4mm) cut through JUST that one wall,
        centered on the switch column's own length, mid-height in its
        shelf -- clear of both the floor and the switch PCB's resting
        surface. The display doesn't need an equivalent hole: it shares
        the stack's own footprint with the MCU directly below it, so its
        wires can simply run down through the open gaps between the
        corner posts (point 11) with no wall in the way at all.

13. MCU PULLED BACK OUT OF THE Z-STACK -- ITS SUPPORT POSTS WERE INSIDE
    THE BATTERY'S OWN FOOTPRINT AND BLOCKED IT FROM BEING INSERTED. A
    follow-up report: the battery couldn't actually go in. Checked, and
    it was a real, serious defect, not cosmetic -- MCU's 4 corner posts
    (point 11) spanned the floor up to MCU_POST_H (7.8mm), TALLER than
    the 6.3mm battery itself, standing squarely inside the battery's own
    51x34.5mm footprint (MCU is narrow, 17.5mm, and centered -- entirely
    within the battery's span, unlike the display's posts, which are
    wide enough to land in the margin strips beside the battery and
    genuinely clear it). No repositioning within the existing footprint
    fixes this: MCU is only 17.5mm wide, the margins beside the battery
    are only ~7mm, and the battery uses effectively the entire stack
    footprint in the other axis too (34.5 of 34.5mm), so there's no
    unused 2D space left for a floor-touching support anywhere within
    the battery's footprint.
      Considered and rejected: bridging MCU in from the display's posts
    (which DO clear the battery) via a cantilevered shelf. Worked through
    the actual geometry -- ANY support that touches the floor within the
    battery's XY footprint physically collides with the battery's own
    volume (a pouch cell isn't hollow; a rib or post passing through the
    middle of its footprint at low Z passes through the cell itself, not
    around it). The only way to avoid that is a genuinely floating
    horizontal bridge with a ~15-16mm unsupported span, starting only
    above the battery's own top surface -- a real FDM print risk
    (bridging that far, over an enclosed cavity where support material
    would be unreachable after printing, is not something to ship
    unverified).
      Fix: MCU goes back to a PLAIN floor-level shelf_frame (the same
    simple pattern every component used before point 11 ever stacked
    anything), in its own row below the battery+display stack and the
    switch column, rotated so its USB-C edge faces the case's +Y (bottom)
    wall instead of -Y. This is the same pattern that was always
    known to work -- not a new risk, a reversion of the one part of
    point 11 that didn't. Side benefit: removing MCU_THICKNESS and its
    standoff clearance from the vertical stack drops the internal cavity
    from 16.3mm back to 12.3mm, and the external case height from 20.3mm
    to 16.3mm -- shorter than point 11's version, at the cost of a
    taller (not wider) footprint from MCU's own new row. Net footprint:
    see print_summary() for the exact number this run.

14. MCU BACK IN THE STACK -- FOOTPRINT MUST NOT GROW, TRADE HEIGHT
    INSTEAD. Point 13's fix grew the footprint (93x45.05mm ->
    93x68.05mm) to give MCU a safe floor-level shelf. Explicit follow-up
    instruction: keep the footprint at point 11/13's original 93x45.05mm
    -- do not make the case bigger in X or Y, thicker is fine. So MCU
    goes back into the 3-layer stack, and the battery-blocking problem
    (point 13) has to be solved a different way this time, one that
    doesn't touch the floor inside the battery's footprint at all.
      CANTILEVER BRACKETS, not floor posts: MCU now rests on 2 small
    brackets (2.7mm thick) that reach in horizontally from the display's
    existing corner posts -- which DO clear the battery (point 11,
    verified) -- rather than posts of MCU's own that would repeat point
    13's mistake. Each bracket's UNDERSIDE sits at BATTERY_TOP_Z + a
    0.3mm air gap (never touching the battery pouch, anywhere along its
    span, by construction) and its far end is fused directly into the
    solid body of a display post. Verified by the same battery-insertion-
    volume probe used to catch point 13's bug in the first place --
    zero overlap between the full battery footprint (floor to its own
    top surface) and the tray, this time confirmed BEFORE calling it
    done, not after a report.
      This is NOT a free fix -- it trades a print-reliability risk for
    keeping the footprint fixed:
      - Cantilever span: ~19.5mm unsupported on each side (computed from
        the actual geometry, not estimated) once the bracket clears the
        display post -- there is nothing beneath it for that entire run,
        since the battery occupies the space below. This is a real
        bridging/overhang challenge for FDM; 15-20mm bridges are
        achievable on printers with strong part cooling (the target
        Bambu A1 qualifies) but are NOT a sure thing without a test
        print, which is why print_summary()'s checklist calls out
        printing the tray alone first and inspecting the brackets before
        committing the rest of the assembly.
      - MCU_SHELF_CLEARANCE was widened from 1.0mm to 3.0mm specifically
        to make the bracket thicker (2.7mm net, after the 0.3mm air gap)
        for rigidity over that span -- this is the "make it thicker, not
        bigger" trade the brief authorized, spent on the bracket rather
        than on general margin.
      - Case height grows accordingly: 22.3mm external (was 20.3mm with
        point 11's floor-blocking posts, 16.3mm with point 13's
        footprint-growing fix). Of the three approaches tried across
        points 11/13/14, this is the only one that is BOTH functionally
        correct (verified battery clearance) AND holds the footprint --
        every other combination traded one for the other.
      A full 4-post cage under MCU (rather than 2 cantilevers) was
    considered and rejected: with the footprint fixed, MCU's near/far
    edges are equally centered over the battery, so a "front and back"
    pair of brackets would need the SAME ~19.5mm reach as the left/right
    pair, just adding 2 more long cantilevers for marginally better
    torsional stability -- not worth the extra unsupported-span risk for
    a component this light (~2g).

15. SNAP-FIT STRAIN CALCULATION BUG FOUND AND FIXED (not requested, found
    while implementing point 16). Re-deriving the tray/lid wall split for
    point 16 required re-examining exactly where the snap bead sits
    relative to the skirt's fixed and free ends -- and that surfaced a
    real, previously-uncaught error: the bead was positioned near the
    TRAY's rim, i.e. near the skirt's FIXED end (where it meets the
    ceiling/cap wall), not its free tip. For a cantilever fixed at one
    end and free at the other, only the material BETWEEN the fixed end
    and wherever a load is applied actually bends -- material beyond the
    load point just moves along, unbent. With the bead only ~2mm from the
    fixed end (verified numerically, not estimated), the true worst-case
    flex length at final seating was ~2mm, while snap_fit_strain() was
    computing strain using SNAP_FLEX_LENGTH (6mm) -- since strain scales
    as 1/L^2, the real strain was roughly 9x higher than reported: ~22%,
    which is ABOVE PLA's own 11.2% elongation-at-break, not just above
    the 30%-of-that design allowance the check was targeting. The check
    would have reported PASS with a comfortable margin while the part was
    likely to crack on the final push of assembly -- a false negative in
    the one safety check this design leans on most.
      Fixed by moving the bead (BEAD_Z0, section 5) to sit near the
    skirt's FREE tip instead (close to LID_PLACEMENT_Z), so the push
    point is close to s=ENGAGE_DEPTH measured from the fixed end -- which
    is what the formula assumed all along. This is a geometry fix, not a
    formula fix: snap_fit_strain() itself is unchanged, and now correctly
    describes the actual mechanics. Every strain PASS reported before
    this point in the project's history should be read as unverified for
    the reason above; this run's numbers are the first genuinely correct
    ones.

16. VISIBLE SEAM MOVED TO THE MIDDLE OF THE CASE (was ~91% up, near the
    top). The nested-skirt design (points 12-14's structure) has the
    tray's own wall run the full internal cavity height and the lid
    nested thin and hidden behind it -- which means the VISIBLE seam is
    always exactly at TRAY_EXTERNAL_H, the tray's own rim, regardless of
    how deep the lid's hidden skirt reaches. That put the seam near the
    very top of the case, not requested and not obviously implied by
    anything earlier. Fixed by giving the lid its own full-width "cap
    wall" (build_lid()) -- same profile as the tray's wall, so the two
    meet flush, no visible step -- running from a new SEAM_FRACTION-
    controlled Z (0.5 = middle) up to the ceiling. The tray's own wall now
    stops AT the seam instead of at the plate line. Below the seam,
    hidden inside the tray's cavity exactly as before, the lid's thin
    skirt continues down ENGAGE_DEPTH more for the snap engagement --
    invisible from outside either way, so this didn't need to move.
      SEAM_FRACTION is a real parameter, not a one-off number: 0.5 is
    this run's choice, but any value is geometrically valid as long as
    the resulting tray wall is taller than ENGAGE_DEPTH plus room for the
    bead (enforced by an assert). Total case height (EXTERNAL_H) is
    unaffected -- this only redistributes how much of that fixed height
    belongs to each printed part.

17. OUTER TOP/BOTTOM EDGES CHAMFERED, per an explicit "comfortable in the
    hand" follow-up -- the original brief's rounded-corners request
    (CORNER_FILLET_OUTER) only rounds the 4 VERTICAL corners; the
    horizontal edges where the flat floor/ceiling meet the outer wall
    (what a palm or fingers actually rest against) were still sharp
    90-degree edges.
      This is a CHAMFER, not a true fillet, for the same reason the bead
    and USB-C notch are chamfers (points 6 and 12): the horizontal rim
    where a flat face meets CORNER_FILLET_OUTER's own rounded vertical
    corners is a tangent-continuous straight+arc loop, and filleting a
    curved edge like that reliably bulges the shape outward at the
    corners in this OCCT version, by close to the fillet radius itself --
    confirmed by testing this specific case before committing to it
    (isolated the rounded_box shape, chamfered it, verified the bounding
    box was unchanged and the 45-degree cut plane landed exactly where
    computed, not assumed safe by analogy to the earlier bead fix).

18. EDGE ROUNDING MADE SMOOTHER (multi-facet, not one flat bevel), per a
    "make it more rounded" follow-up to point 17. A single chamfer reads
    as a flat cut corner, not "rounded" -- and simply making that one
    chamfer bigger runs into a real ceiling fast: its reach is bounded by
    WALL_T/FLOOR_T/CEIL_T (2.0mm), so there's not much room to make ONE
    facet more convincingly curve-like before it eats the whole wall
    cross-section at the edge.
      A true fillet remains off the table (point 17's reasoning is
    unchanged -- still the same OCCT bulge behavior on this shape).
    Instead, rounded_edge_chamfer() (section 7) applies a SEQUENCE of
    progressively smaller chamfers (OUTER_EDGE_CHAMFER_STAGES = [0.9,
    0.6, 0.3], summing to 1.8mm), each one chamfering the edge the
    previous stage just created (which sits further into the wall) --
    the classic CAD trick for faking a round out of chamfers when a true
    fillet isn't available. The result is a 3-facet profile that reads as
    genuinely rounded from a normal viewing/handling distance, not a
    single visible bevel line.
      Verified the same way every fillet/chamfer decision in this file
    has been: built the multi-stage sequence on the bare rounded_box
    shape in isolation first, confirmed the bounding box stayed exactly
    93x45.05mm through all 3 stages (no bulge, no drift), and probed
    specific (X,Z) points with isInside() to confirm the facet
    transitions land where computed -- not assumed safe by extrapolating
    from the single-chamfer case, which is a different (much larger,
    much safer) chamfer-to-wall-thickness ratio.

19. SNAP-FIT CONNECTION SHRUNK -- AND A FIRST ATTEMPT AT IT SILENTLY
    DISABLED THE MECHANISM ENTIRELY, CAUGHT BY THE FIT-CHECK BEFORE
    SHIPPING. "Make the snap connection smaller" touches 3 independent
    numbers (SNAP_FLEX_LENGTH, SNAP_INTERFERENCE, SNAP_BEAD_BAND_H), and
    they don't fail the same way when pushed too far.
      First attempt: L 6.0->5.0mm, d 0.5->0.4mm, band 1.6->1.2mm. The
    strain check (point 15's fix) reported a clean PASS. But the actual
    boolean fit-check -- tray.common(lid), the same probe that caught the
    ORIGINAL butt-joint bug way back at the start of the nested-skirt
    design -- came back with EXACTLY 0mm^3 of overlap. Traced it: d=0.4mm
    landed exactly on 2*SKIRT_CLEARANCE (0.2mm x2), so the bead's tip and
    the skirt's own clearance-inset surface sat at the identical radius --
    touching, not overlapping. The strain formula has no way to know
    this; it just computes a number from d and L, blind to whether d is
    even large enough to produce real interference in the first place.
    A geometrically "safe" strain number and a functioning mechanism are
    two different claims, and only checking the first one would have
    shipped a case whose two halves don't actually snap together at all.
      Fixed by leaving d at its known-good 0.5mm (0.1mm of real
    engagement above the SKIRT_CLEARANCE dead zone) and shrinking ONLY L,
    more modestly, to 5.5mm (strain check re-passes at 13% margin) plus
    the band height to 1.2mm (purely cosmetic, doesn't touch either the
    strain formula or the dead-zone threshold). Re-verified the same way
    the original bug was caught: tray.common(lid) volume is nonzero again
    (9.88mm^3, matching every previously-validated iteration) and
    confined to just the bead's own Z-band, not spread across the whole
    wall or missing entirely.
      Side effect: BEAD_CHAMFER_SIZE (0.3mm) also had to be re-tested
    against the bead ring's new radial wall thickness (~SNAP_INTERFERENCE)
    during the first attempt -- it had been safe at the old thickness but
    landed on the wrong side of a new OCCT failure boundary at the
    smaller one (0.25mm+ threw a hard exception, 0.2mm and below stayed
    clean, confirmed by a direct size sweep). Reverting d to 0.5mm
    restored the original wall thickness this value was tested against,
    so 0.3mm is correct again -- but this is a reminder that the bead
    chamfer's safe range is NOT a fixed constant; it scales with whatever
    SNAP_INTERFERENCE currently is, and needs re-verification (not
    inheritance) every time that changes.

20. MCU MOVED TO THE BOTTOM OF THE STACK, CANTILEVER BRACKETS REMOVED.
    Feedback on point 14's design: "having the MCU on top to the battery
    is not working as good" -- the ~19.5mm unsupported cantilever
    brackets were the single riskiest feature in the whole case (flagged
    as such in point 14 itself and in print_summary()'s checklist), and
    apparently didn't hold up well in practice.
      Stack order flipped to MCU (bottom) -> battery -> display (top),
    instead of point 14's battery (bottom) -> MCU (middle, on brackets)
    -> display (top). This isn't a cosmetic reshuffle -- it changes which
    pair of components needs to clear which. Point 13's original problem
    was specifically that MCU's footprint (17.5x21mm) sits centered
    WITHIN the battery's much larger footprint (51x34.5mm), so any
    floor-touching support for MCU-above-battery lands inside the
    battery's own volume. Flipping the order swaps who's "above" whom:
    now it's the battery that needs support above MCU, and the battery's
    OWN corners -- at its own, larger, footprint -- land clear of MCU's
    small centered footprint by construction (MCU is only 17.5mm wide
    within the battery's 51mm span, and only 21mm within the battery's
    34.5mm depth once offset toward -Y for USB-C access; margins work
    out to >=8.5mm on every side, checked arithmetically before writing
    any geometry code). That's exactly the same "corners clear the
    smaller component beneath" condition the display's posts already
    relied on above the battery in every revision since point 11 -- so
    battery-above-MCU can reuse plain 4-corner posts, the same proven
    pattern, instead of a bracket.
      Net effect: BOTH stacked pairs (MCU->battery and battery->display)
    now use ordinary floor-reaching corner posts. The bracket
    construction -- left_bracket/right_bracket, BATTERY_TOP_AIR_GAP,
    MCU_SUPPORT_H, the whole ~45-line block -- is deleted outright, not
    parameterized around. MCU_SHELF_CLEARANCE, which point 14 had
    widened from 1.0mm to 3.0mm specifically to thicken the bracket for
    rigidity, goes back to a plain 1.0mm standoff clearance -- there's no
    bracket left to thicken. That alone drops the internal cavity height
    (and therefore the external case height) by roughly the 2mm point 14
    had spent on bracket material, on top of whatever the new,
    shorter/simpler height-chain arithmetic works out to -- see
    print_summary() for the exact number this run.
      Footprint is untouched (still 93x45.05mm, point 14's fixed target)
    -- this change only reorders the Z-stack and swaps which support
    pattern applies to which pair, it doesn't touch X/Y layout at all
    beyond MCU's own X0/Y0 shifting to be centered under the battery
    instead of the display.
      Verified the same way every stacked-support claim in this file has
    been verified since point 13's bug: a boolean insertion-volume probe
    for MCU's own new floor slot (zero overlap with the tray) in addition
    to the pre-existing battery and display probes, not just "no
    exception was thrown."

21. MCU RETENTION WALLS -- POINT 20'S PLAIN SHELF PROVIDED NO IN-PLANE
    GRIP, AND THIS BOARD GETS PUSHED ON REPEATEDLY. Follow-up request
    after point 20: "the MCU section" needs to be "more stable" because
    charging means pushing a USB-C plug into it, by hand, an unknown
    number of times over the device's life -- not a one-time assembly
    force.
      shelf_frame() (point 20, and originally point 8) is deliberately
    just a flat ledge -- height MCU_SHELF_CLEARANCE tall, open air below
    for solder joints, per the brief's "shelf pocket, not standoff posts"
    requirement. That's correct for VERTICAL support, but it provides
    ZERO in-plane retention: nothing about a flat ledge stops a board
    resting on it from sliding sideways under a horizontal shove. The
    general per-side FIT_CLEARANCE_XY (0.30mm) drop-in gap made this
    concrete, not theoretical -- the board was already free to shift
    within that gap with nothing to catch it.
      Fix: a U-shaped wall around 3 sides of the MCU's footprint --
    solid, floor-anchored, rising to MCU_TOP_Z (the same height
    convention the stack's corner posts already use) -- open only on the
    4th side, the USB-C edge, where the cable actually needs unobstructed
    access and where a wall would do nothing useful anyway (push force
    points AWAY from that edge, not into it):
      - MCU_BACKSTOP_T (2.0mm): a solid wall directly behind the board
        (opposite the USB-C edge), at MCU_RETENTION_CLEARANCE (0.15mm --
        tighter than the general 0.30mm, since the whole point is
        minimizing slide-before-contact) instead of open air. A push on
        the connector is now compression against a wall rooted in the
        floor, not friction against a ledge.
      - Two MCU_SIDE_WALL_T (1.2mm) guide walls along the board's long
        edges, covering only the back MCU_SIDE_WALL_FRACTION (60%) of
        its length -- enough to stop the board twisting/rocking under an
        off-center push, while leaving the USB-C end at its normal
        looser clearance so the connector itself is never pinched and
        the board still drops straight in from above without binding.
      Geometrically safe for the same reason point 20's corner posts
    were: this wall sits entirely within MCU's own small footprint
    (17.5x21mm), which was already established (point 20) to be well
    clear of the battery's corner posts in X, and it only rises to
    MCU_TOP_Z -- exactly up to the battery's own resting height, not
    into it. Confirmed after building: tray is still a single valid
    solid, and the same MCU/battery/display insertion-volume probes used
    since point 13 all still read exactly 0mm^3 overlap -- the new walls
    add material without blocking anything else's insertion path.

22. LID BUTTON HOLES ENLARGED TO ONE MERGED OPENING; A DIVIDER ADDED
    INSIDE THE TRAY TO KEEP THE TWO BUTTONS SEPARATE. Explicit request:
    "make the holes in the top case bigger, 1.9x1.9cm each" -- which, at
    this design's fixed SWITCH_PITCH (19.05mm), the request itself
    predicted would merge the two switches' separate 14x14mm plate holes
    into one continuous opening (0.05mm would be left between two 19mm
    squares -- not a real wall). Rather than cut two boxes and hope OCCT
    cleans up that sliver, build_lid() now cuts ONE rectangle sized to
    span both button positions -- a single hole by construction (see its
    comment for the exact box math).
      With the plate no longer separating the two switches, a follow-up
    request added a wall INSIDE the tray's switch shelf to do that job
    instead ("a small divider ... to make the buttons in place"):
    5mm thick (not arbitrary -- SWITCH_PITCH - SWITCH_HOLE = 5.05mm is the
    actual free gap between the two switch bodies at this pitch, and 5mm
    fits it almost exactly), centered on the gap between the switches,
    half the shelf's inner cavity long so it can't reach the wire
    pass-through notch on the shelf's near wall (an explicit "don't block
    the cable hole" constraint), sharp corners (it's a plain Part.makeBox,
    nothing rounds it). Re-verified with this file's usual tray.common(lid)
    probe: 0mm^3 overlap against the lid, clean.
      Height went through two iterations. FIRST built up to the plate
    plane (screen_wall's own convention for a wall needing full height) --
    reverted per an immediate "same height as the button box, so the
    caps can be easily pressed" follow-up: that first version stood
    ~6.6mm above the shelf rim, right in the open finger/keycap space
    point 22's merged hole created, an obstacle to actually pressing a
    button. Now exactly SWITCH_PCB_BELOW_CLEARANCE tall from FLOOR_T --
    flush with the shelf/button-box top, same z0 and height as the shelf
    itself -- so it separates the switches through their below-PCB /
    hot-swap-socket zone without reaching into the space above the PCB.
      Flagged, not hidden: this wall runs the full height of the shelf's
    below-PCB clearance zone, meant for socket/pin protrusion, so the
    real switch PCB needs a matching keepout slot cut into it at this
    X/Y position to seat flush around the wall -- the same kind of
    "custom PCB, dimensions not fully specified" caveat this file already
    carries for the PCB's outline (point 10 / LLM.md), just for one more
    feature on it.
      The same request also asked to remove the switch SHELF's own outer
    corner rounding (switch_shelf_floor_r, build_tray()). Tried and
    reverted: that radius isn't cosmetic, it's matched to the lid skirt's
    own swept radius specifically to avoid an overlap at this shelf's far
    corner -- a bug this file's history already found and fixed once
    (see the long comment above build_tray()'s switch-shelf section).
    Sharp corners reintroduced it for real, not hypothetically: the same
    tray.common(lid) probe measured ~30mm^3 of overlap along that whole
    edge. Flagged to the user and kept rounded (matched to the skirt) by
    their choice, once shown the conflict, so the two halves still
    physically fit together.
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
# compared to ABS/PETG/nylon -- see point 4 in the module docstring.
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
# MCU moved to the BOTTOM of the stack (docstring point 20) -- a plain
# floor-level shelf again, not the ~19.5mm cantilever brackets point 14
# needed to hold it above the battery. This is just ordinary solder-joint
# clearance under the board, same magnitude every other floor-level
# component in this design uses.
MCU_SHELF_CLEARANCE = 1.0
# Battery now sits ABOVE the MCU (point 20) on 4 corner posts -- like the
# display's own posts above the battery, not a bracket -- so this is
# ordinary post-height clearance, not bracket material thickness.
BATTERY_SHELF_CLEARANCE = 1.0
USB_C_CUTOUT_W = 9.0       # LLM.md: ~10x6mm opening
USB_C_CUTOUT_H = 3.0
# ASSUMPTION: connector height above the board's bottom face -- typical
# USB-C receptacle (~3.2mm) sitting on a ~1.2mm PCB. VERIFY against the
# physical board before printing; the cutout has +/-1mm of vertical
# margin built in (see USB_C_CUTOUT_H) to absorb a modest error here.
USB_C_CENTER_Z_ABOVE_SHELF = 3.0

# ---- Battery: EEMB 603449 -------------------------------------------
BATTERY_W = 51.0            # HARDWARE.md
BATTERY_D = 34.5            # HARDWARE.md
BATTERY_T = 6.3             # HARDWARE.md

# ---- Switches: 2x Cherry MX2A Silent Blue on a hot-swap PCB ----------
SWITCH_HOLE = 14.0           # STANDARD Cherry MX plate-hole spec (14x14mm), also used as the footprint
SWITCH_PITCH = 19.05         # STANDARD keyboard key pitch (0.75in), not in HARDWARE.md
N_SWITCHES = 2
# LID opening per button, per an explicit "make the holes bigger, 1.9x1.9cm
# each" request -- docstring point 22. Deliberately separate from
# SWITCH_HOLE (14mm): SWITCH_HOLE still drives the PCB footprint / plate
# spec everywhere else in this file, this only enlarges the LID's cutout.
# At SWITCH_PITCH (19.05mm) two adjacent 19mm squares leave only 0.05mm
# between their edges -- see build_lid()'s comment for why that's cut as
# ONE merged rectangle instead of two separate (near-)overlapping boxes.
LID_BUTTON_HOLE = 19.0
# Custom hot-swap PCB: LLM.md says its outline "isn't specified -- size
# its footprint generously and say so." Generous margin beyond the
# switch bodies for solder pads / socket clearance / routing. Tightened
# twice now chasing a smaller footprint (4.0/5.0mm -> 3.0mm -> 2.0mm each)
# -- see module docstring point 10. 2.0mm is still real, usable margin for
# a hot-swap socket's pads, just no longer "generous" -- this is close to
# the floor before the PCB itself becomes the risk, not the case.
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
# pin protrusion is ~3-3.5mm). Used to be a fixed constant here; as of
# the battery-MCU-display stack (docstring point 11) the actual value
# (SWITCH_PCB_BELOW_CLEARANCE) is DERIVED in section 5 from the stack's
# own height requirement instead, since the stack now needs more height
# than the switches ever did -- see section 5 for the real number.

# ====================================================================
# 3. PRINT / SHELL PARAMETERS
# ====================================================================

WALL_T = 2.0            # general shell wall thickness (floor, ceiling, sides)
CORNER_FILLET_OUTER = 8.0   # external vertical-corner radius -- "fits in the hand"
# Outer TOP/BOTTOM edge treatment ("comfortable in the hand" also means the
# edges you actually rest your palm/fingers on, not just the vertical
# corners). This is a sequence of CHAMFERS (rounded_edge_chamfer(),
# section 7), not a true fillet/round, deliberately: a fillet on the
# horizontal rim where the flat floor/ceiling face meets the outer wall
# runs along the SAME tangent-continuous straight+arc loop as
# CORNER_FILLET_OUTER's own rounded corners, and filleting a curved edge
# like that reliably bulges the shape outward at the corners in this OCCT
# version -- the exact bug already found and fixed for the snap bead
# (build_tray()'s bead comment has the full story; empirically it grows
# the footprint by close to the fillet radius itself). A chamfer is
# bounded by construction and can't do that -- confirmed safe by the same
# category of testing used throughout this file, not assumed safe by
# analogy. Applied early (right after each part's basic outer solid is
# built, before other features), matching the general pattern in this
# script of doing fillet/chamfer operations on the simplest possible
# shape rather than a fully-featured one.
#
# A SINGLE chamfer (1.2mm) reads as a flat bevel, not "rounded" -- a
# follow-up asked for more rounding. Since a true fillet stays off the
# table for the reason above, this uses progressively smaller chamfers
# stacked to approximate a curve as a multi-facet profile instead,
# verified safe the same way the single chamfer was (bounding box
# unchanged, correct facet transition points checked with isInside()
# probes, not assumed from the single-chamfer result). The total must
# stay under WALL_T/FLOOR_T/CEIL_T (2.0mm).
#
# Bumped from 3 stages (0.9+0.6+0.3=1.8mm) to 4 (0.7+0.5+0.4+0.3=1.9mm)
# per a further "more rounded" follow-up -- more, smaller steps read as
# a smoother curve at this size, and the extra stage buys a bit more
# total reach too. This isn't a free knob, though: a direct sweep against
# the actual tray/lid shapes (not a hypothetical box) shows 5- and
# 6-stage sequences at the same ~1.95mm total FAIL outright ("no suitable
# edges for chamfer or fillet") even though a 4-stage sequence at that
# same total succeeds -- OCCT's tolerance for this trick has a stage-count
# ceiling here, not just a total-size one. 1.9mm (not the 1.95mm that
# also worked) leaves 0.1mm of margin below WALL_T, matching this file's
# usual practice of not shipping exactly at an observed pass/fail
# boundary. Re-sweep (stage count AND total) before pushing this further.
OUTER_EDGE_CHAMFER_STAGES = [0.7, 0.5, 0.4, 0.3]

# ---- Display window corner/edge treatment (build_lid()) --------------
# Same "sharp cut vs. finished curve" idea as CORNER_FILLET_OUTER /
# OUTER_EDGE_CHAMFER_STAGES just above, applied to the 50x25mm screen
# opening instead of the whole case -- deliberately smaller than both of
# those (2.5mm corner vs. CORNER_FILLET_OUTER's 8.0mm; 0.5mm total rim
# bevel vs. OUTER_EDGE_CHAMFER_STAGES's 1.9mm), since a window this size
# would look wrong with exterior-scale rounding. Verified safe the same
# way the exterior treatment was: built in isolation on a stand-in box,
# confirmed a valid single solid before wiring it into build_lid().
WINDOW_CORNER_R = 2.5
WINDOW_EDGE_CHAMFER_STAGES = [0.3, 0.2]

FIT_CLEARANCE_XY = 0.30     # per-side clearance around dropped-in components
FIT_CLEARANCE_Z = 0.50      # vertical clearance above components

ROW_GAP = 2.0            # gap between component zones (rib/wire-routing space)
BORDER = 2.0             # gap between innermost wall face and component zones

# ---- MCU retention (docstring point 21) -------------------------------
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

# ---- Screen retention -------------------------------------------------
# A lid-side snap tab was tried and rejected: the only Z room available
# for a tab to hang from the ceiling and flex is STACK_TOP_MARGIN itself
# (0.5mm), and a beam that short is thousands of times stiffer than the
# case's own 5.5mm snap skirt (deflection ~ 1/L^3) -- it would just jam
# or not touch, never spring.
#
# A floor-anchored guide wall along the screen's far (+X) edge (the one
# facing the switch column, mirroring MCU's own retention wall) was built
# here for a while, closing off the one long edge that wasn't already
# flush against the case's exterior wall (SCREEN_X0==0). It was REMOVED
# per an explicit request ("remove the horizontal wall you had for the
# screen between the 2 towers closer to the buttons") -- see build_tray()
# for where it used to be fused in. The screen's +X edge now has only its
# 2 corner posts for lateral support on that side, nothing between them.
DISPLAY_POST_SIZE = 4.0

# ---- Snap-fit geometry (see snap_fit_strain() for the math) ----------
# Shrunk from an earlier pass (L=6.0, band=1.6) per a "make the snap
# connection smaller" follow-up -- see docstring point 19 for the full
# story, including a first attempt that shrank d (SNAP_INTERFERENCE) too
# and broke the mechanism entirely (not just a strain-margin problem):
# d must clear 2*SKIRT_CLEARANCE with real margin, since the skirt's own
# nominal surface already sits SKIRT_CLEARANCE inside the wall on each
# relevant boundary -- d==0.4mm (in that failed attempt) landed EXACTLY
# on 2*SKIRT_CLEARANCE (0.2*2), so the bead's tip and the skirt's own
# clearance-inset surface coincided at the same radius: touching, zero
# actual overlap, confirmed by a fit-check showing 0 mm^3 of common
# volume between the two parts. d is left at its known-good 0.5mm here;
# only L (the flex length, which the strain formula tolerates a
# reduction in without threatening the mechanism itself) and the band
# height (purely cosmetic) were shrunk.
SNAP_FLEX_LENGTH = 5.5      # L: cantilever flex length = lid skirt depth (mm)
SNAP_SKIRT_T = 1.2          # t: thickness of the flexing lid skirt (mm) -- left alone, see point 19
SNAP_INTERFERENCE = 0.5     # d: radial bead/groove interference (mm) -- NOT reduced, see above
SNAP_BEAD_BAND_H = 1.2      # height of the bead/groove band along the wall (mm)
# Chamfer size for the bead/groove ramp (see build_tray()'s comment for
# why it's a chamfer, not a fillet). Deliberately conservative: a larger
# value close to SNAP_BEAD_BAND_H/2 (a near-diamond cross-section) was
# tried first and is numerically fragile on these thin rings -- OCCT
# produced an invalid, split (2-solid) result on the groove ring at 0.6mm
# and a hard exception on a similar ring at 0.75mm, both confirmed by
# direct testing, while 0.4mm was reliably clean at THAT SNAP_INTERFERENCE.
# The safe threshold isn't a fixed number -- it scales with the bead
# ring's own radial wall thickness (~SNAP_INTERFERENCE), so this needs
# re-testing (not just carrying the old value over) any time
# SNAP_INTERFERENCE changes -- confirmed the hard way during point 19: a
# first attempt shrank SNAP_INTERFERENCE to 0.4mm and kept this at 0.3mm,
# which was fine at the OLD interference but landed exactly on the wrong
# side of a NEW failure boundary at the smaller wall thickness (0.25mm+
# threw a hard OCCT exception, 0.2mm and below stayed clean). That
# attempt was reverted for an unrelated, more serious reason (see point
# 19), which happens to restore the wall thickness this 0.3mm value was
# originally tested against -- so it's supposed to be correct again, not
# just reverted for looks.
#
# THAT CLAIM WAS RE-TESTED AND IS WRONG AT THE CURRENT GEOMETRY: a direct
# size sweep against the actual bead ring built by build_tray() (not a
# hypothetical one) shows 0.30mm throws a hard OCCT exception
# (StdFail_NotDone) right now, caught silently by the try/except in
# build_tray() -- so the tray's bead has been shipping as a plain SQUARE
# ridge, not the chamfered ramp this whole section is about, while the
# lid's groove (built with the same constant, but a thicker wall so it
# clears the same failure boundary) WAS getting its chamfer. That
# mismatch isn't just "less smooth" -- it's a real hard collision:
# tray.common(lid) at final rest measures ~0mm^3 (as intended -- see
# GROOVE_EXTRA_DEPTH's comment in build_lid(), the bead is meant to sit
# with a small designed clearance in the groove pocket at rest, not press
# against it) when BOTH rings are chamfered OR BOTH are left square, but
# ~9.5mm^3 of genuine overlap when only the groove is chamfered and the
# bead stays square -- the groove's chamfer tapers its pocket back to
# nothing near the band's top/bottom edges, while the square bead's own
# top/bottom stay at full SNAP_INTERFERENCE protrusion right up to that
# same edge with no matching taper, so the two collide exactly there
# (confirmed by the same tray.common(lid) probe, not assumed). That's a
# real physical bind at assembly, not a cosmetic rough edge -- likely
# the direct cause of "does not fit correctly", not just "not smooth".
# 0.28mm
# was the first size in the sweep that still succeeded; 0.20mm is used
# here instead for real margin below that boundary (matching the
# 0.2mm-stays-clean data point already noted above), not because 0.28
# itself is unsafe -- OCCT's failure boundary here has already drifted
# once (0.6/0.75 -> 0.30, per this same comment's history) and a sliver
# of margin below the observed edge is cheap insurance against it moving
# again. Re-test (see the sweep in this file's development notes) any
# time SNAP_INTERFERENCE, SNAP_BEAD_BAND_H, or BEAD_Z0 change.
BEAD_CHAMFER_SIZE = 0.2

# ====================================================================
# 4. DERIVED LAYOUT (plan view) -- SINGLE ROW: FULL 3-LAYER Z-STACK
#    BESIDE THE SWITCHES.
#
#    +---+------------------------+
#    |sw1|                        |   The "STACK" is MCU + battery +
#    +---+       SCREEN            |   display, all in the SAME XY
#    |sw2|  (MCU at the bottom,    |   footprint at different Z heights
#    |   |   battery + display on  |   (see section 5) -- footprint is
#    |   |   plain corner posts)   |   fixed, so this trades case height
#    +---+------------------------+   for a smaller/unchanged footprint.
#
#    Reverted from point 13's "MCU gets its own row" per explicit
#    instruction: keep the footprint exactly this size, use height
#    instead. See docstring point 20 for why MCU sits at the BOTTOM of
#    the stack (not point 14's cantilever-bracketed middle position) --
#    it lets both stacked pairs use plain floor-reaching corner posts,
#    with no unsupported cantilever span anywhere.
# ====================================================================

SCREEN_W, SCREEN_L = DISPLAY_MODULE_W, DISPLAY_MODULE_D  # 65 x 30, landscape
# The stack's footprint is the bounding box of its widest/deepest member:
# display is wider (65 vs battery's 51), battery is deeper (34.5 vs
# display's 30) -- so the stack "sees" a 65 x 34.5 footprint overall, with
# each component centered within it at its own Z layer.
STACK_W = max(SCREEN_W, BATTERY_W)
STACK_D = max(SCREEN_L, BATTERY_D)

# Switch column: reuse the switch-PCB footprint from section 2, pitch
# direction along Y (stacked vertically, narrow width) so it adds as
# little width as possible next to the stack.
SWITCH_COL_W, SWITCH_COL_L = SWITCH_PCB_D, SWITCH_PCB_W

CONTENT_W = STACK_W + ROW_GAP + SWITCH_COL_W
CONTENT_D = max(STACK_D, SWITCH_COL_L)

INTERNAL_W = CONTENT_W + 2 * BORDER
INTERNAL_D = CONTENT_D + 2 * BORDER

EXTERNAL_W = INTERNAL_W + 2 * WALL_T
EXTERNAL_D = INTERNAL_D + 2 * WALL_T

# Stack column (local internal coordinates):
STACK_X0 = BORDER
STACK_Y0 = BORDER + (CONTENT_D - STACK_D) / 2.0  # centered if switches are taller
# Flush against the far interior wall (the one opposite the switch
# column, away from ROW_GAP) instead of centered with STACK_X0's own
# BORDER gap -- SCREEN_W == STACK_W (the screen is the widest stack
# member) so this doesn't disturb the battery/MCU, which are centered
# off STACK_X0, not SCREEN_X0. Deliberately overlaps FIT_CLEARANCE_XY
# into the wall itself (see the display corner posts below) rather than
# landing exactly at X=0 -- an exact coincident face there risks the
# same disconnected-solid fuse() failures documented elsewhere in this
# file (build_lid()'s skirt/cap-wall comments).
SCREEN_X0 = 0.0
SCREEN_Y0 = STACK_Y0 + (STACK_D - SCREEN_L) / 2.0
BATTERY_X0 = STACK_X0 + (STACK_W - BATTERY_W) / 2.0
BATTERY_Y0 = STACK_Y0 + (STACK_D - BATTERY_D) / 2.0

# Switch column, beside the stack:
SWITCH_COL_X0 = STACK_X0 + STACK_W + ROW_GAP
SWITCH_COL_Y0 = BORDER + (CONTENT_D - SWITCH_COL_L) / 2.0

# MCU: now at the BOTTOM of the stack, under the battery (point 20).
# Centered in X within the BATTERY's own footprint (not the screen's) --
# that's what lets the battery's 4 corner posts clear it (verified in
# section 5's docstring comment: >=8.5mm margin on every side by
# construction). Offset toward the battery's own -Y edge (matching the
# stack's -Y edge) rather than centered in Y too, so its USB-C short edge
# stays close to the case's -Y (top) wall -- the offset is fine because
# it's still centered in X, well clear of the corner posts which sit at
# the X-extremes; only a Y-centered MCU would risk them. Rotated 90deg
# from the portrait revision: long axis (21mm, MCU_W) runs along Y.
MCU_X0 = BATTERY_X0 + (BATTERY_W - MCU_D) / 2.0  # centered in X (uses MCU's short side, 17.5mm)
MCU_Y0 = BATTERY_Y0 - 2.0  # pulled 4mm closer to the -Y wall (was +2.0) -- printed gap to the wall was too big

# ====================================================================
# 5. DERIVED Z STACK
# ====================================================================
#
# Internal cavity height USED TO be set by the switch's plate-mount
# geometry alone (points 1/2). As of the battery-MCU-display stack
# (module docstring points 11/14/20), it's the OTHER way around: the
# stack now needs more height than the switches ever did, so the cavity
# height is set by the stack, and the switch PCB's own shelf is derived
# (raised) to keep its plate gap correct at whatever height that turns
# out to be.
#
# Stack order is MCU (bottom) -> battery -> display (top), per point 20 --
# swapped from point 14's battery/MCU/display order specifically because
# it lets EVERY component use the same simple, proven 4-corner-post
# support (like the display's posts above the battery already did)
# instead of point 14's ~19.5mm cantilever brackets: MCU is much smaller
# than the battery (17.5x21mm vs 51x34.5mm), so when MCU sits centered
# under the battery, the battery's OWN corners land comfortably outside
# MCU's footprint (>=8.5mm clear on every side, verified by construction)
# -- the same geometric relationship the display's posts already rely on
# to clear the battery underneath THEM.
#
#   0                                   tray floor top
#   + MCU_SHELF_CLEARANCE               ordinary solder-joint clearance
#   = MCU bottom
#   + MCU_THICKNESS
#   = MCU top = battery's support-post height
#   + BATTERY_SHELF_CLEARANCE           ordinary post-height clearance
#                                        (NOT bracket material -- these
#                                        are simple corner posts now)
#   + BATTERY_T
#   = battery top = display's support-post height (same convention as
#                                        every other stacked pair here:
#                                        the component above rests
#                                        directly on posts at the
#                                        component below's own top)
#   + DISPLAY_THICKNESS
#   = display top
#   + STACK_TOP_MARGIN                  clearance to the plate
#   = INTERNAL_CAVITY_H                 lid's inner (plate) face
#
MCU_TOP_Z = MCU_SHELF_CLEARANCE + MCU_THICKNESS       # = MCU's own physical top

# Battery and display support-post heights, each grown 5mm taller than the
# component they stand on requires, per an explicit "make the towers for
# the battery and screen 5mm taller" request -- pure extra standoff air gap
# on top of the plain resting height each pair already used, not tied to
# any component's real thickness. The two are stacked (display posts start
# from BATTERY_TOP_Z, which already includes the battery tower's own extra
# 5mm), so the case grows by their SUM, 10mm, not 5mm -- flows straight
# through BATTERY_TOP_Z/DISPLAY_TOP_Z/INTERNAL_CAVITY_H/EXTERNAL_H below,
# same as every other height-driving change in this file.
BATTERY_TOWER_EXTRA_H = 5.0
DISPLAY_TOWER_EXTRA_H = 5.0

BATTERY_POST_H = MCU_TOP_Z + BATTERY_TOWER_EXTRA_H    # = battery's support-post height
BATTERY_TOP_Z = BATTERY_POST_H + BATTERY_SHELF_CLEARANCE + BATTERY_T  # = battery's own physical top
DISPLAY_POST_H = BATTERY_TOP_Z + DISPLAY_TOWER_EXTRA_H  # = display's support-post height
DISPLAY_TOP_Z = DISPLAY_POST_H + DISPLAY_THICKNESS
STACK_TOP_MARGIN = 0.5  # deliberately tight -- see docstring point 11
INTERNAL_CAVITY_H = DISPLAY_TOP_Z + STACK_TOP_MARGIN

# Switch PCB shelf, DERIVED so the plate still sits exactly PCB_TO_PLATE
# above the switch PCB at whatever height the stack now requires (much
# taller than the switches themselves need -- that's fine, it just means
# a lot of unused clearance under the switch PCB; see docstring point 11).
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
# An earlier version of this script split the internal cavity height in
# two and butted the tray wall against the lid skirt at a single flat
# parting plane. That is WRONG for a snap fit: with a butt joint the
# tray's wall and the lid's skirt occupy disjoint Z-ranges and never
# touch, so a bead on one and a groove on the other can never engage --
# verified by boolean-intersecting the two solids and getting exactly
# zero overlap volume. Caught here, not on the printer.
#
# The NEXT version fixed that by having the tray wall run the FULL
# internal cavity height (rim touching the ceiling) with the lid as just
# a flat ceiling + a thin, fully-nested skirt reaching down into the
# tray's cavity. That worked mechanically, but it has a visual
# consequence nobody asked for: the tray's own (thick, EXTERNAL_W/D-wide)
# wall is what's visible from OUTSIDE the case for its entire height,
# and the lid's skirt -- however deep it reaches -- is hidden BEHIND it,
# nested at a smaller radius. So the VISIBLE seam is always exactly at
# TRAY_EXTERNAL_H, regardless of ENGAGE_DEPTH -- which in that version
# sat at ~91% of the case height, near the very top. A later request
# asked for the visible seam at the MIDDLE instead.
#
# Fix: give the LID its own full-width (EXTERNAL_W/D, WALL_T-thick) "cap
# wall" -- the same profile as the tray's own wall -- running from the
# seam up to the ceiling, so the two walls are visually continuous and
# meet flush at the seam. Below the seam, the lid's wall continues down
# as the SAME thin, nested skirt as before (SNAP_SKIRT_T thick, inside
# the tray's cavity, hidden), for ENGAGE_DEPTH more, purely for the snap
# engagement -- invisible from outside either way. The tray's own wall
# now stops AT the seam (TRAY_EXTERNAL_H), not at the plate line.
#
# SEAM_FRACTION controls where the seam sits (0.5 = middle, matching the
# request; 1.0 would reproduce the old "seam near the top" behavior).
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
# Bead Z-position -- and a second, independent bug fixed at the same
# time as the seam move (found while re-deriving this geometry, not
# reported separately, but real): the bead was positioned near the
# TRAY's rim, i.e. near the skirt's FIXED end (where it meets the
# ceiling/cap-wall). For a cantilever fixed at the top and free at the
# bottom, only the length of skirt BETWEEN the fixed end and wherever
# the bead pushes actually bends -- the material below the push point
# just gets carried along, unbent. With the bead 2mm from the fixed end
# (its old position), the snap_fit_strain() check below was computing
# strain using L=ENGAGE_DEPTH (6mm) while the REAL worst-case L at final
# seating was ~2mm -- strain scales as 1/L^2, so the true strain was
# roughly 9x higher than reported: ~22%, above PLA's own 11.2%
# elongation-at-break, not just above the 30%-of-that design allowance.
# The check would have reported PASS while the part was likely to crack
# on the final push of assembly.
#
# Fix: position the bead near the skirt's FREE end instead (near
# LID_PLACEMENT_Z), so the engagement point is close to s=ENGAGE_DEPTH
# (measuring from the fixed end) at final seating -- matching what the
# strain formula has assumed all along. Verified numerically (not just
# re-derived) -- see the module's development notes / point 15.
#
# "Close to" is not "at", though, and that residual gap matters: the
# bead sits BEAD_TIP_OFFSET above the tip, so the TRUE distance from the
# fixed end (the seam) to the push point is ENGAGE_DEPTH -
# BEAD_TIP_OFFSET, not ENGAGE_DEPTH itself. snap_fit_strain() now uses
# that true distance (SNAP_TRUE_FLEX_LENGTH, defined right below) instead of
# ENGAGE_DEPTH directly -- at the values this file shipped with before
# this fix (ENGAGE_DEPTH=5.5, offset=0.4mm), the true flex length was
# 5.1mm, not 5.5mm, and strain scales as 1/L^2: real strain was ~3.46%
# against a 3.36% allowable, i.e. the strain check was silently reporting
# PASS (13% margin) on a design that, correctly measured, was already
# slightly OVER its own safety threshold. Caught by re-deriving this
# exactly the way point 15's original version of this same bug was
# caught -- not a hypothetical.
#
# Fixed by shrinking BEAD_TIP_OFFSET itself (0.4mm -> 0.15mm) rather than
# growing ENGAGE_DEPTH: the 0.4mm gap between the bead and the tip was
# never load-bearing, just headroom so the bead ring doesn't sit exactly
# at the skirt's own bottom edge -- 0.15mm is still comfortably clear of
# that edge (the skirt's tip is a plain flat face, no chamfer/fillet
# there to collide with) while reclaiming 0.25mm of true flex length.
# Explicit choice, not the only option: this keeps the snap's overall
# engagement depth (ENGAGE_DEPTH) unchanged rather than making the
# connection physically shorter, which was the other option considered
# -- shortening ENGAGE_DEPTH further only makes strain worse (1/L^2), so
# a meaningfully shorter engagement in PLA would need a thinner flex
# skirt (print-reliability trade) or a PETG lid (~20-30% elongation vs
# PLA's 11.2%, real headroom for a shorter snap with no other trade-off).
BEAD_TIP_OFFSET = 0.15  # how far the bead sits above the skirt's free tip
BEAD_Z0 = LID_PLACEMENT_Z + BEAD_TIP_OFFSET  # near the skirt's free tip, not the rim
GROOVE_Z0_LOCAL = BEAD_Z0 - LID_PLACEMENT_Z  # == BEAD_TIP_OFFSET, near the lid's own local Z=0

# The TRUE cantilever flex length used by snap_fit_strain() (section 6):
# distance from the skirt's fixed end (the seam) down to where the bead
# actually pushes (BEAD_Z0), not the full ENGAGE_DEPTH. See the long
# comment above for why the two differ by exactly BEAD_TIP_OFFSET.
SNAP_TRUE_FLEX_LENGTH = ENGAGE_DEPTH - BEAD_TIP_OFFSET

# How tall the switch stack rises above the finished case's outer top
# surface (informational -- this is expected, see docstring point 1):
SWITCH_PROTRUSION_ABOVE_CASE = (FLOOR_T + SWITCH_PCB_TOP_Z + SWITCH_HOUSING_ABOVE_PCB) - EXTERNAL_H

# USB-C cutout Z (global, from tray bottom): MCU is floor-level again
# (point 20), so this measures from its simple shelf clearance, not a
# bracket support height.
USB_C_CENTER_Z = FLOOR_T + MCU_SHELF_CLEARANCE + USB_C_CENTER_Z_ABOVE_SHELF

# USB-C notch Z-range (global), shared by build_tray() and build_lid() so
# the two openings line up exactly. Two earlier versions cut this notch
# tall enough to also interrupt the snap bead -- first full wall height
# (floor to rim, ~16mm on an 18mm wall, visibly oversized), then trimmed
# to just clip the bead band near the rim (~9mm). Neither reason applies
# anymore: this notch's Z-range is sized purely from the connector's own
# position (USB_C_CENTER_Z, USB_C_CUTOUT_H) plus a placement-tolerance
# margin -- it has no bead term in it at all, unlike those two earlier
# versions. That's what "the USB-C notch doesn't need to be part of the
# snap-fit" means in practice: its size is no longer driven by the bead.
#
# It still happens to OVERLAP the bead band in Z at the current case
# height (BEAD_Z0 sits near the middle of the case because the skirt's
# free tip does, via SEAM_FRACTION=0.5; the connector is also roughly
# mid-height on the MCU's floor-level shelf) -- an older version of this
# comment claimed the two were "confirmed apart by several mm", which is
# NOT true of the current geometry (re-checked directly: USB_C_NOTCH
# spans it entirely). That overlap is not a bug to fix by moving the
# bead, though -- the bead's Z-position is constrained by the strain
# calculation (section 6) to stay near the skirt's free tip, and the
# connector's Z-position is fixed by the hardware. Where they overlap,
# the notch cut simply removes the bead/groove locally, over the notch's
# own ~9-11mm width -- exactly the "interrupted at the USB-C port"
# behavior this file's own module docstring describes as the design from
# the start (see the top of this file). It costs a short, harmless gap
# in an otherwise continuous ~270mm perimeter bead, not a structural
# problem. Both build_tray() and
# build_lid() still apply the cut unconditionally (it's a no-op wherever
# there's no material) since which of the two parts the port actually
# falls in depends on SEAM_FRACTION and the component stack -- currently
# entirely within the lid's cap wall, but this stays correct if that
# ever shifts.
USB_C_NOTCH_Z0 = USB_C_CENTER_Z - USB_C_CUTOUT_H / 2.0 - 0.5
USB_C_NOTCH_Z1 = USB_C_CENTER_Z + USB_C_CUTOUT_H / 2.0 + 0.5
USB_C_NOTCH_HEIGHT = USB_C_NOTCH_Z1 - USB_C_NOTCH_Z0
assert USB_C_NOTCH_Z0 > FLOOR_T, "USB-C notch would dip into the floor slab"


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
    since the bead sits near the skirt's free tip but not exactly AT it
    -- see BEAD_Z0's comment in section 5 and docstring point 15 for why
    an earlier version got this wrong in the other direction (bead near
    the FIXED end instead, true flex_length ~2mm against an assumed 6mm,
    an ~9x strain understatement). Using plain ENGAGE_DEPTH here (as an
    earlier version of this function did, after point 15's fix but before
    BEAD_TIP_OFFSET was accounted for) re-introduces a smaller version of
    the same error: at this file's own shipped constants that was a
    0.4mm/5.5mm ~7% overstatement of flex_length, enough by itself to
    flip the reported result from PASS to what should have been FAIL.
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


def fence_wall(w, d, wall_w, height, z0, origin_xy, floor_r=1.0):
    """A simple low locating fence (solid floor underneath, walls on the
    sides only) for components that don't need under-board clearance
    (display module, battery)."""
    ox, oy = origin_xy
    outer = rounded_box(w, d, height, floor_r, Vector(ox, oy, z0))
    inner_w, inner_d = w - 2 * wall_w, d - 2 * wall_w
    inner = Part.makeBox(inner_w, inner_d, height, Vector(ox + wall_w, oy + wall_w, z0))
    return outer.cut(inner)


def corner_posts(w, d, post_size, height, z0, origin_xy):
    """4 small square posts at the corners of a w x d footprint, from z0
    up to z0+height -- a board dropped on top rests on the 4 post tops.
    Used (instead of shelf_frame's continuous ring) wherever a component
    needs to be elevated ABOVE another component already occupying most
    of the same footprint (the battery-MCU-display stack, docstring point
    11): a continuous ring's walls would run the FULL height from the
    floor and physically collide with whatever's underneath, where 4
    small posts (standard board-mounting practice) intrude only a little,
    and only at the corners."""
    ox, oy = origin_xy
    positions = [
        (ox, oy),
        (ox + w - post_size, oy),
        (ox, oy + d - post_size),
        (ox + w - post_size, oy + d - post_size),
    ]
    posts = [Part.makeBox(post_size, post_size, height, Vector(px, py, z0)) for px, py in positions]
    result = posts[0]
    for p in posts[1:]:
        result = result.fuse(p)
    return result


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
    # square step -- eases both insertion and removal (brief: "curve
    # structure... easy to mount and disassemble"). NOTE: a *fillet*
    # (constant-radius round) was tried here first and rejected -- OCCT
    # fillets a horizontal rim edge on a plan-rounded rectangle by
    # extending the same continuous chain through the corner arcs (they're
    # tangent-connected), and the resulting corner blend geometrically
    # bulges outward by close to the full fillet radius (a torus-around-a-
    # convex-corner effect), silently growing/shrinking the cavity footprint
    # by ~2x the radius and invalidating the interference/strain numbers
    # below. A chamfer cuts a bounded flat facet instead and cannot bulge
    # past the original surface, so it's used here even though it's a
    # facet, not a true curve.
    bead_edges = [e for e in bead_ring.Edges if _is_horizontal_ring_edge(e)]
    try:
        bead_ring = bead_ring.makeChamfer(BEAD_CHAMFER_SIZE, bead_edges)
    except Part.OCCError:
        # NOT cosmetic, despite the old comment here: a square bead riding
        # into a chamfered groove has no lead-in ramp at all, which is
        # exactly what a rough/binding snap feels like. This used to fail
        # silently at BEAD_CHAMFER_SIZE=0.3 -- see that constant's comment
        # for the direct-sweep numbers -- so if it's happening again, it
        # needs to be seen, not swallowed.
        print("WARNING: bead chamfer failed (OCCT) -- tray bead is an "
              "UNCHAMFERED SQUARE ridge, not the smooth ramp this design "
              "relies on. Reduce BEAD_CHAMFER_SIZE and re-test.")
    tray = tray.fuse(bead_ring)

    # Component shelves, all on the tray floor. Stack order is MCU
    # (bottom) -> battery -> display (top), per docstring point 20 --
    # every component in the stack now uses the SAME simple 4-corner-post
    # pattern (or a plain floor shelf for the bottom one), no cantilever
    # brackets anywhere. Point 14's ~19.5mm unsupported bracket span --
    # this design's single biggest print-reliability risk -- is gone, not
    # mitigated.
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
    # shelf's flat ledge above. See docstring point 21. Uses
    # MCU_RETENTION_CLEARANCE (0.15mm), tighter than the general
    # FIT_CLEARANCE_XY (0.30mm) used everywhere else, and rises to
    # MCU_TOP_Z (5.0mm here) -- the same height convention the stack's
    # corner posts already use, and comfortably clear of the battery's
    # own corner posts, which sit outside MCU's X-span entirely (verified
    # in section 4/5's docstring comment).
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

    # Battery: 4 corner posts rising to BATTERY_POST_H (MCU_TOP_Z plus the
    # 5mm BATTERY_TOWER_EXTRA_H standoff, section 5), ABOVE the MCU.
    # Positioned at the battery's OWN footprint corners -- since MCU
    # (17.5x21mm) is much smaller than the battery (51x34.5mm) and
    # centered within it in X, the battery's corners land >=8.5mm clear
    # of MCU on every side (verified by construction, section 4/5). Same
    # pattern the display already used above the battery in every
    # revision since point 11 -- just applied one level down the stack
    # this time.
    BATTERY_POST_SIZE = 4.0
    tray = tray.fuse(corner_posts(
        BATTERY_W + 2 * FIT_CLEARANCE_XY, BATTERY_D + 2 * FIT_CLEARANCE_XY,
        BATTERY_POST_SIZE, BATTERY_POST_H, FLOOR_T,
        (WALL_T + BATTERY_X0 - FIT_CLEARANCE_XY, WALL_T + BATTERY_Y0 - FIT_CLEARANCE_XY)))

    # Display: 4 corner posts rising to DISPLAY_POST_H (BATTERY_TOP_Z plus
    # the 5mm DISPLAY_TOWER_EXTRA_H standoff, section 5), ABOVE the battery.
    # Positioned at the display's OWN footprint corners, which -- because
    # the display (65mm) is wider than the battery (51mm) -- land in the
    # margin strips beside the battery, clearing it entirely (verified:
    # display corners at roughly x=[0,4] and [61,65] within the stack,
    # battery spans x=[7,58]).
    #
    # DISPLAY_POST_H is TALLER than TRAY_EXTERNAL_H (the seam) -- these
    # posts necessarily rise past the seam into territory that belongs to
    # the LID above it. That's fine in principle, but the lid occupies
    # that near-wall band in TWO different ways depending on Z, and a
    # post has to clear BOTH:
    #   - Below the seam: this is where the lid's
    #     own SNAP_SKIRT_T-thick skirt nests into the tray's cavity for the
    #     snap engagement (build_lid()) -- a solid ring occupying
    #     [WALL_T+SKIRT_CLEARANCE, WALL_T+SKIRT_CLEARANCE+SNAP_SKIRT_T]
    #     near every wall, always, not just above the seam.
    #   - Above the seam: the lid's cap wall is hollow past
    #     WALL_T+SKIRT_CLEARANCE (its cavity is inset that far from each
    #     wall face, to receive tall internal supports like this one).
    #   The skirt band is the tighter constraint of the two (it extends
    #   SNAP_SKIRT_T further in than the cap wall's own cavity edge), so
    #   clearing it is sufficient for both. The screen's near edge sits
    #   FLUSH against the wall (SCREEN_X0 == 0, see section 4), and the
    #   generic -FIT_CLEARANCE_XY pad applied uniformly on every side
    #   pushes THAT one edge well past the wall face -- a real, verified
    #   hard collision with the lid (first with the cap wall, ~71mm^3 via
    #   tray.common(lid); still ~54mm^3 against the skirt alone after only
    #   clearing the cap wall's own inset -- both confirmed the same way
    #   every other fit bug in this file has been, not a hypothetical).
    #   Clamped so the near edge never sits closer to the wall than the
    #   skirt's own outer face, while the far (non-flush) edge keeps its
    #   normal padding.
    display_post_x0 = max(WALL_T + SCREEN_X0 - FIT_CLEARANCE_XY,
                           WALL_T + SKIRT_CLEARANCE + SNAP_SKIRT_T + 0.05)
    display_post_x1 = WALL_T + SCREEN_X0 + SCREEN_W + FIT_CLEARANCE_XY
    tray = tray.fuse(corner_posts(
        display_post_x1 - display_post_x0, SCREEN_L + 2 * FIT_CLEARANCE_XY,
        DISPLAY_POST_SIZE, DISPLAY_POST_H, FLOOR_T,
        (display_post_x0, WALL_T + SCREEN_Y0 - FIT_CLEARANCE_XY)))

    # Screen retention wall along the screen's far (+X) edge -- the one
    # facing the switch column across ROW_GAP, bridging the two display
    # corner posts closest to the switches -- REMOVED per an explicit
    # "remove the horizontal wall you had for the screen between the 2
    # towers closer to the buttons" request. The near (X=0) edge still
    # needs nothing extra (it already touches the case's own exterior
    # wall). Trade-off, flagged rather than silently dropped: the screen's
    # +X edge now relies on the 2 corner posts on that side alone for
    # lateral retention, with nothing between them -- more slop against
    # sideways sliding on that edge than before, not eliminated.
    #
    # Switch column: shelf_frame as in every previous revision, on the
    # SWITCH_COL_W x SWITCH_COL_L footprint beside the stack. Its shelf
    # height (SWITCH_PCB_BELOW_CLEARANCE) is now DERIVED (section 5) and
    # much taller than the switches themselves need -- just a lot of
    # unused clearance under the switch PCB, harmless.
    # floor_r matches the lid skirt's own corner radius (skirt_r,
    # build_lid()) rather than the small default (1.0mm): the switch
    # column sits flush against the cavity's own far wall/corner, and the
    # skirt -- now positioned low enough (point 16's seam move) to
    # actually reach down into this shelf's own Z range -- sweeps a much
    # LARGER radius through that same corner. With the shelf's default
    # small corner radius, its own corner boundary sat closer to the
    # sharp cavity corner than the skirt's rounded sweep allowed
    # clearance for, so the two overlapped there (caught in the
    # fit-check: overlap volume/Z-range far exceeded the bead band alone,
    # constant-rate across most of the skirt's height, not just the 1.6mm
    # bead band -- traced to specific X/Y/Z coordinates matching this
    # shelf's far corner, not a vague "something's off"). Matching the
    # radii removes the conflict at its source instead of just adding
    # clearance margin and hoping.
    # Point 22 asked to also remove this shelf's outer corner rounding
    # (the "internal button box", alongside the new divider below). Tried
    # (floor_r=0.0) and reverted: that radius isn't cosmetic -- it exists
    # specifically to clear the lid skirt at this shelf's far corner (see
    # the long comment above this function for that bug's original story),
    # and sharp corners reintroduce it for real: the same tray.common(lid)
    # probe used throughout this file measured ~30mm^3 of actual overlap
    # along that whole edge, not a rounding error. Kept matched to the
    # skirt's own radius per the user's explicit choice, once shown the
    # conflict, to keep the two halves fitting together.
    SWITCH_SHELF_RIM_W = 2.0
    switch_shelf_floor_r = max(CORNER_FILLET_OUTER - WALL_T - SKIRT_CLEARANCE, 0.1)
    tray = tray.fuse(shelf_frame(
        SWITCH_COL_W + 2 * FIT_CLEARANCE_XY, SWITCH_COL_L + 2 * FIT_CLEARANCE_XY,
        SWITCH_SHELF_RIM_W, SWITCH_PCB_BELOW_CLEARANCE, FLOOR_T,
        (WALL_T + SWITCH_COL_X0 - FIT_CLEARANCE_XY, WALL_T + SWITCH_COL_Y0 - FIT_CLEARANCE_XY),
        floor_r=switch_shelf_floor_r))

    # Wire pass-through: the switch column's shelf_frame is a continuous
    # ring (unlike the stack's posts/brackets), so its wall facing the
    # stack would otherwise block routing the switch wires to the MCU.
    # Cut a small notch through JUST that wall (the one facing the stack,
    # -X side) so wires have a clear, deliberate path from the switch PCB
    # over to the MCU (which sits mid-stack, reachable through the same
    # open gap the wires cross). Centered along the switch column's
    # length, mid-height in its shelf.
    wire_notch_w, wire_notch_h = 6.0, 4.0
    wire_notch_x0 = WALL_T + SWITCH_COL_X0 - FIT_CLEARANCE_XY - 1.0  # 1mm overshoot into the open gap
    wire_notch_depth = SWITCH_SHELF_RIM_W + 2.0  # punches cleanly through the 2mm rim wall
    wire_notch_y0 = WALL_T + SWITCH_COL_Y0 + SWITCH_COL_L / 2.0 - wire_notch_w / 2.0
    wire_notch_z0 = SWITCH_PCB_BELOW_CLEARANCE / 2.0 - wire_notch_h / 2.0
    wire_cutter = Part.makeBox(
        wire_notch_depth, wire_notch_w, wire_notch_h,
        Vector(wire_notch_x0, wire_notch_y0, wire_notch_z0))
    tray = tray.cut(wire_cutter)

    # Button divider: the lid's plate hole over these two switches used to
    # be two separate 14x14mm holes, which kept the buttons visually and
    # physically apart on their own. Point 22 merges that into one big
    # opening (build_lid()'s comment), so nothing up top separates the two
    # switches anymore -- this wall, standing inside the switch shelf,
    # replaces that job. Per an explicit request:
    #   - 5mm thick (Y direction, the axis the switches are stacked on).
    #     Not a chosen number: SWITCH_PITCH - SWITCH_HOLE = 19.05 - 14 =
    #     5.05mm is the actual free gap between the two switch bodies at
    #     this pitch/footprint, and 5mm fits it almost exactly.
    #   - Centered on the shelf's own Y-midpoint -- the same midpoint
    #     wire_notch_y0 above is centered on, i.e. the gap between the two
    #     switches.
    #   - Half the shelf's INNER cavity width (X direction) long, per an
    #     explicit "1/2 of the length of the box" request, anchored to the
    #     shelf's far (+X) inner wall and stopping at the cavity's own
    #     midpoint -- deliberately short of the near (-X) inner wall, where
    #     wire_cutter (just above) punches through, so this wall can't
    #     block that cable path. Confirmed clear of it in X: wire_cutter's
    #     far edge sits only ~1mm past the near inner wall, this wall's
    #     near edge starts at the cavity's own midpoint, several mm beyond
    #     that.
    #   - Sharp corners (no fillet), matching the shelf's own corners just
    #     above.
    # Z-range: floor to SWITCH_PCB_BELOW_CLEARANCE -- i.e. exactly as tall
    # as the shelf/button box itself (their outer boxes share the same z0
    # AND height), not up to the plate plane. FIRST built taller (up to
    # the plate plane, matching screen_wall's convention for a wall that
    # needs to reach all the way up) but that put its top ~6.6mm above the
    # shelf rim -- right where the switch caps themselves are, an obstacle
    # between a fingertip and the button per an explicit "make the buttons
    # easily pressable" follow-up. Flush with the shelf top instead: still
    # separates the two switches through their entire below-PCB /
    # hot-swap-socket zone (the only zone this wall can occupy without
    # colliding with the PCB itself -- see the keepout-slot note below),
    # just without poking up into the open finger/keycap space above the
    # PCB that point 22's merged hole created.
    # ASSUMPTION carried over from before: the actual switch PCB needs a
    # matching keepout slot cut into it at this X/Y position so it can
    # still seat flush on the shelf rim around this wall. Flagged, not
    # silently assumed away -- verify against the real PCB layout before
    # printing, same as every other "custom hot-swap PCB" dimension in
    # this file (see docstring point 10 / LLM.md).
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
    # margin -- no longer tied to the snap bead's position (point 15
    # moved the bead well away from here). STADIUM-shaped (rounded ends),
    # not a sharp rectangle -- a sharp rectangle reads as a generic slot;
    # the rounded-end "capsule" is what actually looks like USB-C.
    usbc_cx = WALL_T + MCU_X0 + MCU_D / 2.0
    notch_w = USB_C_CUTOUT_W + 0.5  # +1mm clearance per side for the plug/cable
    cutter = stadium_slot_y(usbc_cx, USB_C_NOTCH_Z0, notch_w, USB_C_NOTCH_HEIGHT, -2.0, 12.0)
    tray = tray.cut(cutter)

    return tray


def build_lid():
    """Top shell: a flat ceiling (with display window + switch plate
    holes), a full-width "cap wall" below it (the lid's OWN visible outer
    wall, matching the tray's profile so the two meet flush at the seam
    -- see section 5 for why this exists, point 16 in the module
    docstring), and below THAT, a separate, narrower skirt that NESTS
    INSIDE the tray's cavity for ENGAGE_DEPTH, hidden, purely for the
    snap engagement. Local Z=0 is the skirt's free tip; the ceiling sits
    at the top, local Z=LID_EXTERNAL_H. main() translates the whole thing
    up by LID_PLACEMENT_Z to seat it for the preview."""
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
    # An earlier version cut this cavity at INTERNAL_W (matching the
    # tray), leaving a SKIRT_CLEARANCE-wide gap between the skirt's outer
    # face and the cap wall's inner face: they never touched, so
    # fuse()'ing them gave 2 disconnected solids instead of 1 (confirmed
    # by checking len(lid.Solids)). A bridging ring was tried next, sized
    # to overlap both sides of the gap -- but its outer edge, straddling
    # the seam, ended up occupying the SAME space as the tray's own wall
    # just below the seam, an unintended tray/lid collision (caught the
    # same way: an unexpectedly large overlap volume in the fit-check
    # spanning well past the bead band). Matching the cavity to the
    # skirt's footprint directly avoids both problems -- no gap, and
    # nothing reaches outside the tray's own hollow cavity radius, ever.
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
    # set to EXACTLY the same footprint (above), fuse()'ing two solids
    # that only share an exactly-coincident face -- no actual 3D overlap
    # -- still produced 2 disconnected solids instead of 1 (confirmed:
    # len(lid.Solids)==2), the same failure mode as the coincident-face
    # bead issue, just triggered by a lateral/radial coincidence rather
    # than the horizontal one that hit there. Fixed with a small ring
    # reaching OVERLAP_EPS beyond the skirt's own outer footprint,
    # straddling the Z boundary -- giving genuine volumetric overlap with
    # BOTH the skirt and the cap wall. Sized to stay well inside the
    # tray's actual cavity radius (max reach is INTERNAL_W - 0.1mm, a
    # deliberate margin) so it can NEVER collide with the tray's own wall
    # material -- unlike the first attempt at this fix, which reached all
    # the way to the tray's old (INTERNAL_W-cavity) boundary and ended up
    # overlapping the tray's wall just below the seam (caught by an
    # unexpectedly large fit-check overlap volume spanning well past the
    # bead band, not just a solid-count check).
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
    # near the skirt's free tip now, not the rim; see point 15 for why).
    # The pocket's inset is deliberately kept LESS than SNAP_SKIRT_T: an
    # earlier version used inset = SNAP_SKIRT_T + SNAP_INTERFERENCE, which
    # cuts deeper than the skirt wall itself is thick and cleanly SEVERS
    # the skirt ring at the groove band -- confirmed by loading the
    # exported lid and finding it was 6 disconnected solids instead of 1.
    # Keeping a real wall thickness behind the pocket keeps the skirt one
    # continuous tube.
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

    # Display window: sized independently of SCREEN_W/SCREEN_L (which is
    # the full module footprint, 65x30, used for the case/post sizing
    # above). The printed hole was too big at the module-derived size, so
    # it's fixed at a smaller, explicit HOLE_W x HOLE_D instead -- still
    # centered over the module footprint via SCREEN_X0/SCREEN_Y0. NOTE:
    # active area is DISPLAY_ACTIVE_W x DISPLAY_ACTIVE_D (48.55 x 23.71),
    # so this leaves only ~0.7mm/0.65mm bezel per side -- tight, verify
    # against the real module's black border before committing to a full
    # print (a 0.5mm placement error would just start showing glass edge).
    HOLE_W, HOLE_D = 50.0, 25.0
    win_w = HOLE_W
    win_d = HOLE_D
    # Shifted 2mm off-center along X per an explicit request: closer to the
    # case's exterior wall (SCREEN_X0==0, the screen module's own flush
    # edge, section 4) and correspondingly farther from the switch column,
    # which sits on the opposite (+X) side of the same axis -- both of
    # those are satisfied by the same single move, since edge and buttons
    # are the two ends of this one axis, not independent directions.
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
    # from the ceiling's underside around the window, tracing the SAME
    # footprint the tray's own display corner posts use below (SCREEN_W/L
    # +/- FIT_CLEARANCE_XY, section 6) -- so the tray's 4 posts (vertical
    # support) and this lid-side ring (lateral confinement along the
    # WHOLE perimeter, not just 4 points) box the module in from both
    # sides. It reaches down only SCREEN_LIP_H from the ceiling, stopping
    # SCREEN_LIP_CLEARANCE short of where the module's top surface sits
    # (DISPLAY_TOP_Z) -- deliberately NOT an interference fit against the
    # already-tight STACK_TOP_MARGIN (docstring point 11); this is meant
    # to stop the module sliding sideways in its pocket, not to clamp it
    # vertically.
    SCREEN_LIP_CLEARANCE = 0.2
    SCREEN_LIP_H = STACK_TOP_MARGIN - SCREEN_LIP_CLEARANCE
    assert SCREEN_LIP_H > 0, (
        "no room for a screen retention lip -- tighten SCREEN_LIP_CLEARANCE "
        "or STACK_TOP_MARGIN")
    lip_x0 = WALL_T + SCREEN_X0 - FIT_CLEARANCE_XY
    lip_y0 = WALL_T + SCREEN_Y0 - FIT_CLEARANCE_XY
    lip_w = SCREEN_W + 2 * FIT_CLEARANCE_XY
    lip_d = SCREEN_L + 2 * FIT_CLEARANCE_XY
    lip_z0 = LID_EXTERNAL_H - CEIL_T - SCREEN_LIP_H
    lip_outer = Part.makeBox(lip_w, lip_d, SCREEN_LIP_H, Vector(lip_x0, lip_y0, lip_z0))
    lip_inner = Part.makeBox(win_w, win_d, SCREEN_LIP_H + 2, Vector(win_x, win_y, lip_z0 - 1))
    screen_lip = lip_outer.cut(lip_inner)
    lid = lid.fuse(screen_lip)

    # Screen retention WALL: a proper vertical ring around the display
    # module's own footprint, added on the LID's interior (hanging from
    # the ceiling down into the hollow cap-wall cavity) per an explicit
    # "add a retention wall around the screen module" request -- this is
    # a taller, structural version of what the shallow lip above can't be:
    # the lip's depth is capped at STACK_TOP_MARGIN (a fraction of a mm)
    # because going any deeper there would cut into the module's own
    # physical body (the lip's inner hole is window-sized, much smaller
    # than the module footprint). This wall instead uses lip_w/lip_d --
    # the SAME footprint the tray's 4 corner posts already use below -- as
    # its INNER opening, so the module still drops through with the exact
    # clearance it always had; the wall material sits OUTSIDE that
    # boundary, in room that's genuinely free on 3 sides (Y top/bottom
    # have several mm of margin; the +X side facing the switch column has
    # ROW_GAP to spare). The near/-X edge needs nothing extra -- lip_x0
    # already overlaps into the case's own WALL_T exterior wall there
    # (see build_tray()'s display-post-clamp comment), so this ring's -X
    # segment just fuses harmlessly into that existing solid wall.
    #
    # Z-range: from just above where the tray's own display corner posts
    # end (DISPLAY_POST_H, plus SCREEN_WALL_POST_CLEARANCE of assembly-
    # tolerance headroom) up to the ceiling. The posts never reach into
    # that band, so unlike a wall built on the TRAY side (which would
    # have to dodge the posts' own footprint at the corners), there's no
    # cross-part collision to design around here at all -- unused Z
    # territory that opened up once the tower-height change (this
    # session) pushed the display well clear of the seam.
    SCREEN_WALL_T = 1.5
    SCREEN_WALL_POST_CLEARANCE = 0.3
    SCREEN_RETENTION_WALL_H = (EXTERNAL_H - CEIL_T) - (FLOOR_T + DISPLAY_POST_H + SCREEN_WALL_POST_CLEARANCE)
    assert SCREEN_RETENTION_WALL_H > 0, (
        "no room for a screen retention wall above the display's corner posts -- "
        "raise DISPLAY_TOWER_EXTRA_H/STACK_TOP_MARGIN or tighten SCREEN_WALL_POST_CLEARANCE")
    screen_wall_z0 = LID_EXTERNAL_H - CEIL_T - SCREEN_RETENTION_WALL_H
    screen_wall_outer = rounded_box(
        lip_w + 2 * SCREEN_WALL_T, lip_d + 2 * SCREEN_WALL_T, SCREEN_RETENTION_WALL_H, 1.0,
        Vector(lip_x0 - SCREEN_WALL_T, lip_y0 - SCREEN_WALL_T, screen_wall_z0))
    screen_wall_inner = Part.makeBox(
        lip_w, lip_d, SCREEN_RETENTION_WALL_H + 2, Vector(lip_x0, lip_y0, screen_wall_z0 - 1))
    screen_wall = screen_wall_outer.cut(screen_wall_inner)

    # Gap in the +X segment (the one facing the switch column, closer to
    # the buttons), per an explicit "remove 1.5cm in the middle" request.
    # Centered on that segment's own Y-midpoint, full wall thickness and
    # full height, so it opens a clean through-gap rather than a pocket.
    # NOTE: this segment's real length is lip_d (SCREEN_L+2*FIT_CLEARANCE_XY
    # = 30.6mm at this file's current constants), not the ~25mm (5+15+5)
    # implied by the request's own "around 5mm each side" estimate -- a
    # centered 15mm cut actually leaves ~7.8mm on each side, not 5mm.
    # Sized to the explicit 15mm figure (the more specific of the two
    # numbers given) rather than silently resizing the cut to force
    # exactly 5mm remainders; adjust SCREEN_WALL_BUTTON_NOTCH_W below if
    # 5mm on each side was actually the firmer requirement.
    SCREEN_WALL_BUTTON_NOTCH_W = 15.0
    notch_y0 = lip_y0 + lip_d / 2.0 - SCREEN_WALL_BUTTON_NOTCH_W / 2.0
    notch_x0 = lip_x0 + lip_w - 0.5  # 0.5mm overshoot on each side for a clean through-cut
    notch_cutter = Part.makeBox(
        SCREEN_WALL_T + 1.0, SCREEN_WALL_BUTTON_NOTCH_W, SCREEN_RETENTION_WALL_H + 2,
        Vector(notch_x0, notch_y0, screen_wall_z0 - 1))
    screen_wall = screen_wall.cut(notch_cutter)
    lid = lid.fuse(screen_wall)

    # Switch plate holes: previously N_SWITCHES independent 14x14mm holes
    # (standard Cherry MX plate spec), one per switch. Per an explicit
    # "make the holes bigger, 1.9x1.9cm each" request (docstring point 22)
    # each button's opening grows to LID_BUTTON_HOLE (19mm) square -- at
    # the fixed SWITCH_PITCH (19.05mm) that leaves only 0.05mm between two
    # adjacent squares' edges, which the request itself calls out as
    # "provably ... just 1 hole for both buttons". Rather than cut
    # N_SWITCHES separate boxes and rely on OCCT to fuse a 0.05mm sliver
    # cleanly out of the mesh, this cuts ONE rectangle sized to span every
    # button position -- a single hole by construction, not an accident of
    # near-overlap. The switches are stacked along Y (portrait layout), so
    # the merge is along Y; X width is just LID_BUTTON_HOLE.
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
    print("=" * 72)
    print("ESP32-S3 PORTABLE CASE -- computed dimensions")
    print("=" * 72)
    print()
    print("Filament: %s" % ELONGATION_SOURCE)
    print()
    print("-- Footprint / layout --")
    print("External footprint : %.2f x %.2f mm" % (EXTERNAL_W, EXTERNAL_D))
    print("Internal cavity     : %.2f x %.2f mm" % (INTERNAL_W, INTERNAL_D))
    print("Stack footprint (MCU+battery+screen): %.2f x %.2f mm at (%.2f, %.2f)" % (STACK_W, STACK_D, STACK_X0, STACK_Y0))
    print("  MCU (bottom, floor shelf -- see docstring point 20): %.2f x %.2f mm at (%.2f, %.2f)" % (
        MCU_D, MCU_W, MCU_X0, MCU_Y0))
    print("  Battery (middle, on corner posts): %.2f x %.2f mm at (%.2f, %.2f)" % (BATTERY_W, BATTERY_D, BATTERY_X0, BATTERY_Y0))
    print("  Screen (top, on corner posts) : %.2f x %.2f mm at (%.2f, %.2f)" % (SCREEN_W, SCREEN_L, SCREEN_X0, SCREEN_Y0))
    print("Switch column (beside the stack): %.2f x %.2f mm at (%.2f, %.2f)" % (
        SWITCH_COL_W, SWITCH_COL_L, SWITCH_COL_X0, SWITCH_COL_Y0))
    print()
    print("-- Height (Z) budget, from tray floor top -- set by the stack, not the switches --")
    print("Internal cavity height (= PCB-to-plate stack): %.2f mm" % INTERNAL_CAVITY_H)
    print("  MCU shelf clearance     : %.2f mm" % MCU_SHELF_CLEARANCE)
    print("  MCU thickness           : %.2f mm  -> MCU top at Z=%.2f" % (MCU_THICKNESS, MCU_TOP_Z))
    print("  battery tower extra     : %.2f mm  -> battery post height at Z=%.2f" % (BATTERY_TOWER_EXTRA_H, BATTERY_POST_H))
    print("  battery post clearance  : %.2f mm" % BATTERY_SHELF_CLEARANCE)
    print("  battery thickness       : %.2f mm  -> battery top at Z=%.2f" % (BATTERY_T, BATTERY_TOP_Z))
    print("  display tower extra     : %.2f mm  -> display post height at Z=%.2f" % (DISPLAY_TOWER_EXTRA_H, DISPLAY_POST_H))
    print("  display thickness       : %.2f mm  -> display top at Z=%.2f" % (DISPLAY_THICKNESS, DISPLAY_TOP_Z))
    print("  -> margin below plate: %.2f mm (deliberately tight -- see docstring point 11)" % STACK_TOP_MARGIN)
    print("Switch PCB shelf (derived to keep the %.1fmm plate gap correct at this height): %.2f mm" % (
        PCB_TO_PLATE, SWITCH_PCB_BELOW_CLEARANCE))
    print("External case height (tray+lid, assembled)  : %.2f mm" % EXTERNAL_H)
    print("  VISIBLE SEAM at Z=%.2f mm (%.0f%% up the case -- see docstring point 16)" % (
        TRAY_EXTERNAL_H, 100.0 * SEAM_FRACTION))
    print("  tray external height (floor to seam)        : %.2f mm" % TRAY_EXTERNAL_H)
    print("  lid external height (cap wall + ceiling, above the seam): %.2f mm" % (LID_CAP_WALL_H + CEIL_T))
    print("  lid external height total (incl. hidden skirt below the seam): %.2f mm" % LID_EXTERNAL_H)
    print("  lid's skirt is HIDDEN, nested inside the tray's cavity, reaching %.2fmm" % ENGAGE_DEPTH)
    print("  below the seam for the snap engagement only -- not visible from outside")
    print("  bead/groove sit near Z=%.2f (close to the skirt's free tip, not the seam --" % BEAD_Z0)
    print("  see docstring point 15 for why that matters for the strain check below)")
    print("Switch stack protrudes above outer case top : %.2f mm (expected -- see docstring point 1)" % SWITCH_PROTRUSION_ABOVE_CASE)
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
    print("-- Assumed / generic figures (not in HARDWARE.md/LLM.md) --")
    for name, val, note in [
        ("Display module thickness", DISPLAY_THICKNESS, "e-paper HAT glass+PCB, no pin header assumed"),
        ("MCU assembled thickness", MCU_THICKNESS, "XIAO board + antenna/shield + solder"),
        ("MCU USB-C connector center height", USB_C_CENTER_Z_ABOVE_SHELF, "above MCU shelf -- verify against real board"),
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
    print("  [ ] If this case will be opened/closed often, consider printing the LID")
    print("      in PETG (elongation-at-break ~20-30%%) instead of PLA (%.1f%%) for a" % (ELONGATION_AT_BREAK * 100))
    print("      more durable snap; re-run with ELONGATION_AT_BREAK adjusted to check margin.")
    print("  [ ] Slice with >=3 perimeters on the lid skirt / tray bead region so the")
    print("      %.1fmm flex wall is solid, not sparse-infill." % SNAP_SKIRT_T)
    print("  [ ] The stack (MCU -> battery -> display, docstring point 20) relies on")
    print("      each component's corner posts clearing the smaller component beneath")
    print("      it -- verified geometrically and by boolean insertion probes, but a")
    print("      first test-fit of the tray alone (before committing the full print)")
    print("      is still worthwhile given how tight BATTERY_SHELF_CLEARANCE/")
    print("      MCU_SHELF_CLEARANCE (%.1fmm each) are." % MCU_SHELF_CLEARANCE)
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
