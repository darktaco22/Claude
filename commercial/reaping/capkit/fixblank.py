"""replace near-uniform (blank / context-lost) frames with the previous good frame"""
import sys, glob, shutil
from PIL import Image, ImageStat
fs = sorted(glob.glob(sys.argv[1] + '/f_*.png')); prev = None; bad = 0
for f in fs:
    st = ImageStat.Stat(Image.open(f).convert('L').resize((108, 192)))
    if st.stddev[0] < 6:
        bad += 1
        if prev: shutil.copy(prev, f)
    else: prev = f
print('blank frames replaced:', bad)
