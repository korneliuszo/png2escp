#!/usr/bin/env python3

from PIL import Image
import sys

def render(textlines,fontdir):
    space=Image.open(fontdir+"/ .png")
    width_pixels, height_pixels = space.size
    xline=0
    for line in textlines:
        xline=max(xline,len(line))
    im=Image.new("1",(xline*width_pixels,len(textlines)*height_pixels),1)
    for y in range(0,len(textlines)):
        for x in range(0,len(textlines[y])):
            glyph=Image.open(fontdir+'/'+textlines[y][x]+'.png')
            im.paste(glyph,(x*width_pixels,y*height_pixels))
    return im

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Render text as image.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('output',
                    help='output image')
    parser.add_argument('-f', '--font', default="out24", type=str,
                    help='mode to use for printing')
    args = parser.parse_args()

    data = sys.stdin.read().splitlines()

    im = render(data,args.font)
    im.save(args.output)
