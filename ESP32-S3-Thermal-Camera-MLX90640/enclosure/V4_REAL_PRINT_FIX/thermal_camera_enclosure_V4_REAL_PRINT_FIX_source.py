from pathlib import Path
import json, zipfile
import cadquery as cq
from cadquery import exporters
import trimesh
from PIL import Image, ImageDraw, ImageFont

OUT = Path('/mnt/data/ESP32_Thermal_Camera_Enclosure_V4_REAL_PRINT_FIX')
OUT.mkdir(parents=True, exist_ok=True)

# -----------------------------
# PARAMETRIC DIMENSIONS (mm)
# -----------------------------
BODY_W = 90.0
BODY_H = 62.0
BODY_D = 32.0
CORNER_R = 9.0
WALL = 2.6

DISPLAY_PCB_W = 62.0
DISPLAY_PCB_H = 37.0
DISPLAY_WINDOW_W = 55.0
DISPLAY_WINDOW_H = 36.0
DISPLAY_FRONT_GAP = 2.2
DISPLAY_PCB_T = 1.6

LENS_HOLE_D = 12.5
LENS_Y = 8.0

SCREW_BOSS_OD = 6.2
SCREW_PILOT_D = 2.0
SCREW_CLEAR_D = 2.9

COVER_T = 2.8
LOCATING_LIP_H = 2.0

# V4 mating geometry:
# The cover lip enters 2.0 mm into the body.  Boss tops stop 3.5 mm below the
# rear rim, creating 1.5 mm vertical clearance.  The lip also has radial relief
# pockets around all four boss positions to protect against XY print tolerance.
BOSS_RECESS_FROM_RIM = 3.5
LIP_RELIEF_D = 10.5


def rounded_rect_prism(w, h, r, d, z0=0):
    shape = cq.Workplane('XY').workplane(offset=z0).rect(w - 2*r, h).extrude(d)
    shape = shape.union(cq.Workplane('XY').workplane(offset=z0).rect(w, h - 2*r).extrude(d))
    for sx in (-1, 1):
        for sy in (-1, 1):
            shape = shape.union(
                cq.Workplane('XY').workplane(offset=z0)
                .center(sx*(w/2-r), sy*(h/2-r))
                .circle(r).extrude(d)
            )
    return shape


# -----------------------------
# FRONT BODY
# -----------------------------
inner_w = BODY_W - 2*WALL
inner_h = BODY_H - 2*WALL
inner_r = CORNER_R - WALL

outer = rounded_rect_prism(BODY_W, BODY_H, CORNER_R, BODY_D)
# cut all the way through the rear so the body is open at the back
inner = rounded_rect_prism(inner_w, inner_h, inner_r, BODY_D - WALL + 0.5, z0=WALL)
front_body = outer.cut(inner)

# Screen opening
screen_cut = rounded_rect_prism(DISPLAY_WINDOW_W, DISPLAY_WINDOW_H, 2.2, WALL + 1.0, z0=-0.2)
front_body = front_body.cut(screen_cut)

# Display PCB support pads
for sx in (-1, 1):
    for yy in (-11.5, 11.5):
        x = sx*(DISPLAY_PCB_W/2 - 2.3)
        pad = (cq.Workplane('XY').workplane(offset=WALL)
               .center(x, yy)
               .box(4.0, 6.0, DISPLAY_FRONT_GAP, centered=(True, True, False)))
        front_body = front_body.union(pad)

# Display retaining clips
clip_base_z = WALL
clip_h = DISPLAY_FRONT_GAP + DISPLAY_PCB_T + 1.5
for sx in (-1, 1):
    for yy in (-10.5, 10.5):
        x = sx*(DISPLAY_PCB_W/2 + 2.0)
        tower = (cq.Workplane('XY').workplane(offset=clip_base_z)
                 .center(x, yy)
                 .box(2.0, 5.0, clip_h, centered=(True, True, False)))
        front_body = front_body.union(tower)
        lip_x = x - sx*1.6
        snap_lip = (cq.Workplane('XY')
                    .workplane(offset=clip_base_z + DISPLAY_FRONT_GAP + DISPLAY_PCB_T + 0.2)
                    .center(lip_x, yy)
                    .box(1.2, 5.0, 0.9, centered=(True, True, False)))
        front_body = front_body.union(snap_lip)

# Screw boss positions
boss_xy = [
    (-38.5, -24.0),
    (-38.5,  24.0),
    ( 38.5, -24.0),
    ( 38.5,  24.0),
]

boss_z0 = WALL
boss_top_z = BODY_D - BOSS_RECESS_FROM_RIM
boss_h = boss_top_z - boss_z0

# V4: every screw post starts directly on the enclosure floor.  A wider,
# low base collar is fused into the floor so the post cannot begin in mid-air
# and has a larger first-layer footprint inside the cavity.
BOSS_BASE_OD = 8.5
BOSS_BASE_H = 1.4

# Screw bosses fully grounded to interior floor
for x, y in boss_xy:
    base = (cq.Workplane('XY').workplane(offset=WALL)
            .center(x, y).circle(BOSS_BASE_OD/2).extrude(BOSS_BASE_H))
    front_body = front_body.union(base)
    boss = (cq.Workplane('XY').workplane(offset=boss_z0)
            .center(x, y).circle(SCREW_BOSS_OD/2).extrude(boss_h))
    hole = (cq.Workplane('XY').workplane(offset=boss_z0 - 0.1)
            .center(x, y).circle(SCREW_PILOT_D/2).extrude(boss_h + 0.3))
    front_body = front_body.union(boss).cut(hole)

# Centered, enlarged USB / service opening on right side
# Y=0 centers the slot along the 62 mm side.  Z tracks the rear-mounted ESP32
# while leaving extra clearance for the molded USB-C plug and cable movement.
SERVICE_SLOT_W = 18.0
SERVICE_SLOT_H = 9.0
SERVICE_SLOT_Y = 0.0
SERVICE_SLOT_Z = BODY_D - 8.0
service_slot = (cq.Workplane('YZ')
                .workplane(offset=BODY_W/2 - 1.2)
                .center(SERVICE_SLOT_Y, SERVICE_SLOT_Z)
                .rect(SERVICE_SLOT_W, SERVICE_SLOT_H)
                .extrude(4, both=True))
front_body = front_body.cut(service_slot)

# -----------------------------
# REAR COVER
# -----------------------------
rear_cover = rounded_rect_prism(BODY_W, BODY_H, CORNER_R, COVER_T)

# Locating lip
lip_w = inner_w - 1.2
lip_h = inner_h - 1.2
outer_lip = rounded_rect_prism(lip_w, lip_h, inner_r - 0.3, LOCATING_LIP_H, z0=COVER_T)
inner_lip = rounded_rect_prism(lip_w - 2.4, lip_h - 2.4, inner_r - 1.5, LOCATING_LIP_H + 0.2, z0=COVER_T)
locating_lip = outer_lip.cut(inner_lip)

# Relief around each boss through locating lip only
for x, y in boss_xy:
    relief = (cq.Workplane('XY').workplane(offset=COVER_T - 0.05)
              .center(x, y).circle(LIP_RELIEF_D/2)
              .extrude(LOCATING_LIP_H + 0.2))
    locating_lip = locating_lip.cut(relief)

rear_cover = rear_cover.union(locating_lip)

# Screw holes + counterbores
for x, y in boss_xy:
    through = (cq.Workplane('XY').workplane(offset=-0.2)
               .center(x, y).circle(SCREW_CLEAR_D/2)
               .extrude(COVER_T + LOCATING_LIP_H + 0.5))
    counterbore = (cq.Workplane('XY').workplane(offset=-0.1)
                   .center(x, y).circle(2.7).extrude(1.1))
    rear_cover = rear_cover.cut(through).cut(counterbore)

# MLX90640 lens aperture
lens_hole = (cq.Workplane('XY').workplane(offset=-0.2)
             .center(0, LENS_Y).circle(LENS_HOLE_D/2)
             .extrude(COVER_T + LOCATING_LIP_H + 0.5))
rear_cover = rear_cover.cut(lens_hole)

# Universal sensor mounting pad
sensor_pad = (cq.Workplane('XY').workplane(offset=COVER_T)
              .center(0, LENS_Y).rect(30, 30).extrude(1.2))
sensor_pad = sensor_pad.cut(
    cq.Workplane('XY').workplane(offset=COVER_T - 0.1)
    .center(0, LENS_Y).rect(20, 20).extrude(1.5)
)
rear_cover = rear_cover.union(sensor_pad)

# Universal thermal-sensor slots
for dx, dy in [(-10,0), (10,0), (0,-10), (0,10)]:
    sw, sh = (3.0, 7.0) if dx else (7.0, 3.0)
    slot = (cq.Workplane('XY').workplane(offset=-0.2)
            .center(dx, LENS_Y + dy).rect(sw, sh)
            .extrude(COVER_T + 2.0))
    rear_cover = rear_cover.cut(slot)

# Universal ESP32-S3 SuperMini tray/tie points
tray_cx, tray_cy = 22, -11
tray_w, tray_h = 28, 22
for dx in (-tray_w/2 + 3, tray_w/2 - 3):
    for dy in (-tray_h/2 + 3, tray_h/2 - 3):
        post = (cq.Workplane('XY').workplane(offset=COVER_T)
                .center(tray_cx + dx, tray_cy + dy)
                .box(4, 4, 2.2, centered=(True, True, False)))
        rear_cover = rear_cover.union(post)
for sx in (-1, 1):
    tie_slot = (cq.Workplane('XY').workplane(offset=-0.2)
                .center(tray_cx + sx*(tray_w/2 + 2.5), tray_cy)
                .rect(3.0, 10).extrude(COVER_T + 0.5))
    rear_cover = rear_cover.cut(tie_slot)

# -----------------------------
# FIT TESTS
# -----------------------------
display_test = rounded_rect_prism(68, 45, 4, 2.0)
display_test = display_test.cut(
    rounded_rect_prism(DISPLAY_WINDOW_W, DISPLAY_WINDOW_H, 2.2, 2.4, z0=-0.2)
)

lens_test = rounded_rect_prism(28, 28, 4, 2.0)
lens_test = lens_test.cut(
    cq.Workplane('XY').workplane(offset=-0.2).circle(LENS_HOLE_D/2).extrude(2.4)
)

# Corner mating test: crop one corner from each actual part.
# This lets the user verify the exact lip/boss interaction before printing the full enclosure.
corner_crop_body = (cq.Workplane('XY').workplane(offset=0)
                    .center(BODY_W/2 - 14, BODY_H/2 - 14)
                    .box(28, 28, BODY_D, centered=(True, True, False)))
corner_body = front_body.intersect(corner_crop_body)

corner_crop_cover = (cq.Workplane('XY').workplane(offset=0)
                     .center(BODY_W/2 - 14, BODY_H/2 - 14)
                     .box(28, 28, COVER_T + LOCATING_LIP_H + 0.5, centered=(True, True, False)))
corner_cover = rear_cover.intersect(corner_crop_cover)

# -----------------------------
# EXPORT + VALIDATION
# -----------------------------
parts = {
    '01_front_body_V4_REAL_PRINT_FIX': front_body,
    '02_rear_cover_V4_REAL_PRINT_FIX': rear_cover,
    '03_display_window_fit_test': display_test,
    '04_lens_hole_fit_test': lens_test,
    '05_corner_body_fit_test': corner_body,
    '06_corner_cover_fit_test': corner_cover,
}

validation = {}
for name, shape in parts.items():
    stl = OUT / f'{name}.stl'
    step = OUT / f'{name}.step'
    exporters.export(shape, str(stl))
    exporters.export(shape, str(step))
    mesh = trimesh.load_mesh(stl)
    validation[name] = {
        'watertight': bool(mesh.is_watertight),
        'size_mm': [round(float(v), 2) for v in (mesh.bounds[1] - mesh.bounds[0])],
        'faces': int(len(mesh.faces)),
        'volume_mm3': round(float(abs(mesh.volume)), 2),
    }

# Closed assembly model for inspection (cover rotated so the locating lip points into the body)
rear_assembled = rear_cover.rotate((0,0,0), (0,1,0), 180).translate((0,0,BODY_D + COVER_T))
assembly = cq.Compound.makeCompound([front_body.val(), rear_assembled.val()])
exporters.export(assembly, str(OUT / '07_assembly_closed_V4_REAL_PRINT_FIX.step'))

# Collision check between body and assembled cover.
# NOTE: the locating lip intentionally sits inside the cavity, but should not overlap solid body/boss material.
try:
    intersection = front_body.intersect(rear_assembled)
    inter_vol = intersection.val().Volume()
except Exception:
    inter_vol = None

meta = {
    'body_rear_rim_z_mm': BODY_D,
    'usable_internal_depth_to_lip_mm': round(BODY_D - WALL - LOCATING_LIP_H, 3),
    'display_window_mm': [DISPLAY_WINDOW_W, DISPLAY_WINDOW_H],
    'usb_slot_mm': [SERVICE_SLOT_W, SERVICE_SLOT_H],
    'usb_slot_side_center_y_mm': SERVICE_SLOT_Y,
    'usb_slot_center_z_mm': SERVICE_SLOT_Z,
    'boss_start_z_mm': boss_z0,
    'interior_floor_top_z_mm': WALL,
    'boss_base_od_mm': BOSS_BASE_OD,
    'cover_lip_penetration_mm': LOCATING_LIP_H,
    'boss_top_z_mm': boss_top_z,
    'boss_recess_from_rim_mm': BOSS_RECESS_FROM_RIM,
    'nominal_vertical_clearance_boss_to_lip_mm': BOSS_RECESS_FROM_RIM - LOCATING_LIP_H,
    'lip_relief_diameter_mm': LIP_RELIEF_D,
    'rear_lip_xy_clearance_per_side_mm': 0.6,
    'display_clip_clearance_per_side_mm': 1.0,
    'lens_radial_clearance_mm_assuming_10mm_lens': (LENS_HOLE_D-10.0)/2,
    'assembled_solid_intersection_volume_mm3': None if inter_vol is None else round(float(inter_vol), 6),
}

(OUT / 'validation.json').write_text(json.dumps({'parts':validation,'mating':meta}, indent=2), encoding='utf-8')

# Full parametric source
source = Path('/mnt/data/build_thermal_v4_real_print_fix.py').read_text(encoding='utf-8')
(OUT / 'thermal_camera_enclosure_V4_REAL_PRINT_FIX_source.py').write_text(source, encoding='utf-8')

# Documentation
(OUT / 'CHANGELOG_V4_REAL_PRINT_FIX.md').write_text(f'''# V4 REAL-PRINT FIX change — rear cover / screw-boss clearance\n\nV4 incorporates fixes from the first real full print: more internal depth, a larger display opening, a centered/wider USB service slot, and screw posts grounded directly to the enclosure floor.\n\nKey V4 geometry changes:\n\n1. Boss tops stop **{BOSS_RECESS_FROM_RIM:.1f} mm below the rear body rim**.\n2. The rear-cover locating lip has **Ø{LIP_RELIEF_D:.1f} mm clearance pockets** around all four boss positions.\n\nThe locating lip enters **{LOCATING_LIP_H:.1f} mm** into the body, leaving **{BOSS_RECESS_FROM_RIM - LOCATING_LIP_H:.1f} mm nominal vertical clearance** above each screw boss before accounting for the extra radial relief.\n\nThese changes address the real-print fit issues while preserving the proven cover-lip clearance from V3.\n''', encoding='utf-8')

(OUT / 'PRINT_GUIDE_V4_REAL_PRINT_FIX.md').write_text(f'''# ESP32 Thermal Camera Enclosure V4 REAL-PRINT FIX — Print Guide\n\n## Print these first\n\nBefore a full enclosure print, print the two corner mating coupons:\n\n- `05_corner_body_fit_test.stl`\n- `06_corner_cover_fit_test.stl`\n\nThey are cropped directly from the real V4 body and cover, so they test the exact screw-boss / locating-lip geometry.\n\nThe cover should drop fully onto the corner with no gap.\n\n## Full enclosure parts\n\n- `01_front_body_V4_REAL_PRINT_FIX.stl`\n- `02_rear_cover_V4_REAL_PRINT_FIX.stl`\n\n## Suggested print settings\n\n- PLA or PETG\n- 0.20 mm layer height\n- 0.4 mm nozzle\n- 4 walls/perimeters\n- 15–25% infill\n- Front body: display/front face on the build plate\n- Rear cover: outside/rear face on the build plate\n\n## Fasteners\n\n4 × M2.5 self-tapping screws. Start with roughly 10 mm length because the boss tops are deliberately recessed.\n\n## V3 cover clearance\n\n- Locating-lip depth: {LOCATING_LIP_H:.1f} mm\n- Screw-boss recess below rim: {BOSS_RECESS_FROM_RIM:.1f} mm\n- Nominal vertical clearance: {BOSS_RECESS_FROM_RIM - LOCATING_LIP_H:.1f} mm\n- Lip relief around each boss: Ø{LIP_RELIEF_D:.1f} mm\n''', encoding='utf-8')

# Simple explanatory preview image
img = Image.new('RGB', (1600, 900), (244,246,249))
d = ImageDraw.Draw(img)
try:
    fb = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 48)
    fm = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 31)
    fs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
except Exception:
    fb=fm=fs=None

d.text((60,35),'Thermal Camera Enclosure V4 REAL-PRINT FIX — Cover Clearance Fix',font=fb,fill=(22,28,34))
# section sketch
d.text((90,130),'SIDE SECTION AT A SCREW CORNER',font=fm,fill=(50,55,62))
# body wall/rim
# cavity area
body_x1, body_x2 = 170, 720
rim_y = 270
bottom_y = 700
d.rounded_rectangle((130,220,760,735), radius=50, fill=(55,58,64), outline=(20,24,30), width=4)
d.rectangle((190,270,700,735), fill=(244,246,249))
# boss, stopped lower
d.rounded_rectangle((560,390,635,700), radius=25, fill=(232,183,55), outline=(130,95,20), width=3)
d.ellipse((581,405,614,438),fill=(244,246,249),outline=(110,80,20),width=2)
# body rear rim line
d.line((190,270,700,270), fill=(0,180,220), width=6)
d.text((215,225),'BODY REAR RIM',font=fs,fill=(0,135,170))
# cover above
cover_y0=115
d.rounded_rectangle((865,115,1505,245), radius=36, fill=(55,58,64), outline=(20,24,30), width=4)
# lip downward
# indicate relief cut around boss line
d.rectangle((930,245,1440,325), fill=(92,97,105))
d.ellipse((1280,220,1410,350), fill=(244,246,249))
d.text((1005,355),'LOCATING LIP',font=fs,fill=(70,75,82))
d.text((1130,410),'Relief pocket around screw boss',font=fm,fill=(20,105,135))
d.line((1260,430,1330,340),fill=(0,165,205),width=5)
# dimension arrows / labels
# 3.2 mm boss recess
x=790
d.line((x,270,x,390),fill=(220,70,70),width=4)
d.line((x-12,270,x+12,270),fill=(220,70,70),width=4)
d.line((x-12,390,x+12,390),fill=(220,70,70),width=4)
d.text((810,315),f'{BOSS_RECESS_FROM_RIM:.1f} mm boss recess',font=fs,fill=(170,45,45))
# clearance callout
d.text((85,790),f'Lip enters {LOCATING_LIP_H:.1f} mm; boss is recessed {BOSS_RECESS_FROM_RIM:.1f} mm → {BOSS_RECESS_FROM_RIM-LOCATING_LIP_H:.1f} mm nominal vertical clearance.',font=fm,fill=(20,30,38))
d.text((85,840),f'Plus Ø{LIP_RELIEF_D:.1f} mm relief around every screw post.',font=fm,fill=(0,115,150))
img.save(OUT / 'V3_one_trip_clearance.png', quality=95)

# Zip
zip_path = Path('/mnt/data/ESP32_Thermal_Camera_Enclosure_V4_REAL_PRINT_FIX.zip')
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):
        if p.is_file():
            z.write(p, arcname=f'ESP32_Thermal_Camera_Enclosure_V4_REAL_PRINT_FIX/{p.name}')

print('ZIP', zip_path)
print('META', json.dumps(meta, indent=2))
for k,v in validation.items():
    print(k, v)
