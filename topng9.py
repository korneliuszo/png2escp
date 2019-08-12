#!/usr/bin/env python3

import fontdict
import os
import glob
from PIL import Image

try:
    os.mkdir("out9")
except FileExistsError:
    pass
files = glob.glob('out9/*')
for f in files:
    os.remove(f)



for char in fontdict.fontdict.keys():
    im=Image.new("1",(11,9),1)
    glyph=fontdict.getfont(char)
    yi = 0 if glyph[0] & 0x80 else 1
    for xi in range(0,11):
        byte=glyph[xi+1]
        for yii in range(0,8):
            black=(byte & (1<<yii))
            if black:
                xc=xi
                yc=yi+yii
                im.paste(0,(xc,yc,xc+1,yc+1))
    im.save("out9/"+char+".png","PNG")
