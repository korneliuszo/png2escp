#!/usr/bin/env python
"""
This is a minimal ESC/POS printing script which uses the 'column format'
of image output.

The snippet is designed to efficiently delegate image processing to
PIL, rather than spend CPU cycles looping over pixels.

Do not attempt to use this snippet in production, get a copy of python-escpos instead!
"""

from PIL import Image, ImageOps
import bitstring
import struct
import sys
import os

ESC = b"\x1b";

def _to_column_format(im,colour='cmyk',overscan=2,mode=39,printer="24pin",skip=1):
    """
    Extract slices of an image as equal-sized blobs of column-format data.

    :param im: Image to extract from
    :param line_height: Printed line height in dots
    """

    #im = im.convert("L")  # Invert: Only works on 'L' images
    #im = ImageOps.invert(im) # Bits are sent with 0 = white, 1 = black in ESC/POS
    #im = im.convert("1") # Pure black and white
    im = im.convert("RGB")
    im = im.transpose(Image.ROTATE_270).transpose(Image.FLIP_LEFT_RIGHT)
    ci = Image.new("1",im.size,0)
    mi = Image.new("1",im.size,0)
    yi = Image.new("1",im.size,0)
    ki = Image.new("1",im.size,0)

    width_pixels, height_pixels = im.size

    if colour == 'cmyk':
        for y in range(0,height_pixels):
            for x in range(0,width_pixels):
                box=(x,y,x+1,y+1)
                r,g,b=im.getpixel((x, y))
                if r==0 and g==0 and b==0:
                    ki.paste(1,box)
                elif r==255 and g==255 and b==255:
                    pass
                elif r==255 and g==0 and b==0:
                    mi.paste(1,box)
                    yi.paste(1,box)
                elif r==0 and g==255 and b==0:
                    ci.paste(1,box)
                    yi.paste(1,box)
                elif r==0 and g==0 and b==255:
                    ci.paste(1,box)
                    mi.paste(1,box)
                elif r==255 and g==255 and b==0:
                    yi.paste(1,box)
                elif r==0 and g==255 and b==255:
                    ci.paste(1,box)
                elif r==255 and g==0 and b==255:
                    mi.paste(1,box)
                else:
                    raise Exception("Not known colour %d,%d,%d"%(r,g,b))
    elif colour == 'k':
        ki = im.convert("L")  # Invert: Only works on 'L' images
        ki = ImageOps.invert(ki) # Bits are sent with 0 = white, 1 = black in ESC/POS
        ki = ki.convert("1") # Pure black and white
    else:
        raise Exception("Not known colour mode")

    line_height = overscan *(3 if mode & 32 else 1)
    top = 0
    left = 0
    while left < width_pixels:
        remaining_pixels = width_pixels - left
        
        for i in range(0,overscan):
            
            if colour == 'cmyk':
                colours =  (4,2,1,0)
            elif colour == 'k':
                colours = (0,)
            for col in colours:
                
                switcher={
                        4: yi,
                        2: ci,
                        1: mi,
                        0: ki,
                        }

                box = (left + i, top, left + line_height*8 + i, top + height_pixels)
                slice = switcher[col].transform((line_height*8, height_pixels), Image.EXTENT, box)
                data = slice.tobytes()
            
                assert len(data) % line_height == 0
                assert len(data) == height_pixels * line_height

                yield ESC + b"r" + struct.pack("<B",col)

                yield ESC + b"*" + struct.pack("<BH",mode,len(data)//(line_height))

                ai = 0
                for j in range(0, len(data), line_height):
                    value = bitstring.Bits(data[j:j+(3 if mode & 32 else 1)*overscan]).uintbe
                    sparse = value
                    byte = 0x00
                    for k in range(0, (24 if mode & 32 else 8)):
                        #100100100100100100100100
                        byte |= ((1 << (overscan * k + overscan - 1)) & sparse) >> (overscan * k - k + overscan - 1 )
                    ai+=(3 if mode & 32 else 1)
                    yield bitstring.Bits(uintbe=byte, length=(3 if mode & 32 else 1)*8).tobytes()
                    
                yield b"\r"

                assert ai == len(data)//overscan

            if printer == "24pin":
                if i < overscan-1:
                    yield ESC + b"+" + struct.pack("<B",skip) + b"\n"
                else:
                    yield ESC + b"+" + struct.pack("<B",48-(overscan-1)*skip) +b"\n"
            elif printer == "9pin":
                if i < overscan-1:
                    yield ESC + b"3" + struct.pack("<B",skip) + b"\n"
                else:
                    yield ESC + b"3" + struct.pack("<B",24-(overscan-1)*skip) +b"\n"
            else:
                raise Exception('not known printer')

        left += line_height*8

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Process image for escp printer.',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('input',
                    help='input image')
    parser.add_argument('output', default='-', nargs='?',
                    help='output file (dafaults to stdout)')
    parser.add_argument('-p', '--printer', default='9pin',
                    help='printer type (9pin or 24pin)')
    parser.add_argument('-c', '--colour',
                    default='k', action='store_const', const='cmyk',
                    help='use colours')
    parser.add_argument('-m', '--mode', default=5, type=int,
                    help='mode to use for printing')
    parser.add_argument('-o', '--overscan', default=1, type=int,
                    help='vertical resolution multiplier')
    parser.add_argument('-s', '--skip', default=1, type=int,
                    help='how much n/(216/360)dpi jump when overscanning')

    args = parser.parse_args()

    # Load Image
    im = Image.open(args.input)
    
    if args.output == '-':
        fp=os.fdopen(sys.stdout.fileno(), 'wb')
    else:
        fp=open(args.output,'wb')

    # Initial rotate. mirror, and extract blobs for each 8 or 24-pixel row
    # Convert to black & white via greyscale (so that bits can be inverted)

    # Generate ESC/POS header and print image
    # Height and width refer to output size here, image is rotated in memory so coordinates are swapped
   
    fp.write(ESC + b'@' + ESC + b'P' + ESC + b'l\x00' + b'\r' + ESC + b'Q\x00')
    for blob in _to_column_format(im,
            printer=args.printer,
            colour=args.colour,
            mode=args.mode,
            overscan=args.overscan,
            skip=args.skip):
        fp.write(blob)
