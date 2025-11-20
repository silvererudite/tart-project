#!/usr/bin/env python3
import glob
import logging
import os
import random
import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from multiprocessing import Pool
from PIL import Image, ImageDraw
import pandas

# -----------------------------
# CONFIG
# -----------------------------
INPUT_GLOB = "img/mu-udm-t*-image.fits"    # picks only the CLEANed images
OUTPUT_DIR = "movie_frames_final"

DO_OVERPLOT_TRACK = False

# -----------------------------
# Helpers
# -----------------------------
def temp_name():
    return "tmp_" + ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=16)) + ".fits"

def make_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR,exist_ok=True)

# -----------------------------
# DRAW ONE PNG FRAME
# -----------------------------
def make_png(ff, idx, clamp_min, clamp_max):
    make_output_dir()

    log = logging.getLogger()
    log.info(f"[{idx}] Converting {ff}")

    tmpf = temp_name()
    os.system(f"mShrink {ff} {tmpf} 1")

    # read metadata
    hdu = fits.open(ff)[0]
    hdr = hdu.header
    date = hdr.get("DATE-OBS", "UNKNOWN")
    freq = hdr.get("CRVAL3", 0) * 1e-6     # Hz → MHz

    # convert time
    try:
        mjd = Time(date, format='isot').mjd
        tt = f"{date}  |  MJD={mjd:.2f}"
    except Exception:
        tt = date

    # output png
    png = f"{OUTPUT_DIR}/frame_{idx:04d}.png"

    # call mViewer
    cmd = f"mViewer -ct 0 -gray {tmpf} {clamp_min} {clamp_max} -out {png}"
    os.system(cmd)

    img = Image.open(png)
    w, h = img.size

    # enforce even dimensions for ffmpeg
    img = img.crop((0, 0, w - (w % 2), h - (h % 2)))
    w, h = img.size

    # *NO TEXT, NO FONTS, NO LABELS*
    # but you can still draw shapes if needed
    draw = ImageDraw.Draw(img)

    # overlay circles for radius guide (optional)
    try:
        wcs = WCS(hdr)
        for r in [15, 30, 45, 60, 75]:
            px = wcs.world_to_pixel_values([
                (hdr["CRVAL1"] + r, hdr["CRVAL2"], hdr.get("CRVAL3", 0), hdr.get("CRVAL4", 0))
            ])
            if not np.isnan(px[0][0]):
                r_px = np.sqrt((px[0][0] - (hdr["CRPIX1"] - 1))**2 +
                               (px[0][1] - (hdr["CRPIX2"] - 1))**2)
                draw.ellipse((w//2-r_px, h//2-r_px, w//2+r_px, h//2+r_px), outline="green")
    except Exception:
        pass

    img.save(png)
    os.remove(tmpf)
    log.info(f"[{idx}] Done → {png}")


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
if __name__ == "__main__":

    logging.basicConfig(filename="make_movie.log",
                        level=logging.INFO,
                        format="%(asctime)s | %(message)s")

    fitslist = sorted(glob.glob(INPUT_GLOB))
    if len(fitslist) == 0:
        raise SystemExit("ERROR: No FITS files found.")

    nframes = len(fitslist)

    # compute clamp range from first image
    with fits.open(fitslist[0]) as f:
        data = f[0].data
        sigma = np.std(data)
        clamp_min = -3 * sigma
        clamp_max =  3 * sigma

    print(f"Clamp range: {clamp_min:.4g} → {clamp_max:.4g}")

    pool = Pool(processes=8)
    pool.starmap(make_png,
                 [(f, i, clamp_min, clamp_max) for i, f in enumerate(fitslist)])

    # make MP4
    out_movie = "tart_movie.mp4"
    fps = 10
    os.system(f"ffmpeg -y -r {fps} -i {OUTPUT_DIR}/frame_%04d.png "
              f"-vcodec libx264 -pix_fmt yuv420p -crf 22 {out_movie}")

    print(f"\n🎉 Movie saved as: {out_movie}\n")
