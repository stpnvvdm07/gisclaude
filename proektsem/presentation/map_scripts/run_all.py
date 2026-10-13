# Все карты презентации подряд: python3 run_all.py
import os, sys, glob, runpy
H = os.path.dirname(os.path.abspath(__file__))
for f in sorted(glob.glob(os.path.join(H, "[0-9][0-9]_*.py"))):
    print("—", os.path.basename(f)); runpy.run_path(f, run_name="__main__")
