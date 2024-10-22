#!/usr/bin/env python3
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

def _to_column_format(im,colour='cmyk',overscan=2,mode=39,printer="24pin",skip=1,cut=False):

    # Convert image to RGB type so we can process colours
    im = im.convert("RGB")
    # Initial rotate. mirror
    im = im.transpose(Image.ROTATE_270).transpose(Image.FLIP_LEFT_RIGHT)
    ci = Image.new("L",im.size,0)
    mi = Image.new("L",im.size,0)
    yi = Image.new("L",im.size,0)
    ki = Image.new("L",im.size,0)

    # Height and width refer to output size here, image is rotated in memory so coordinates are swapped
    width_pixels, height_pixels = im.size
    if colour == 'cmyk':
        for y in range(0,height_pixels):
            for x in range(0,width_pixels):
                box=(x,y,x+1,y+1)
                r,g,b=im.getpixel((x, y))
                rp=r/255
                gp=g/255
                bp=b/255
                k=1-max(rp,gp,bp)
                c=(1-rp-k)/(1-k) if k!=1 else 0
                m=(1-gp-k)/(1-k) if k!=1 else 0
                yc=(1-bp-k)/(1-k) if k!=1 else 0
                ki.paste((int(k*255)),box)
                ci.paste((int(c*255)),box)
                mi.paste((int(m*255)),box)
                yi.paste((int(yc*255)),box)
        ki=ki.convert("1")
        ci=ci.convert("1")
        mi=mi.convert("1")
        yi=yi.convert("1")
    elif colour == 'k':
        # Convert to black & white via greyscale (so that bits can be inverted)
        ki = im.convert("L")  # Invert: Only works on 'L' images
        ki = ImageOps.invert(ki) # Bits are sent with 0 = white, 1 = black in ESC/POS
        ki = ki.convert("1") # Pure black and white
    elif colour == 'rk':
        for y in range(0,height_pixels):
            for x in range(0,width_pixels):
                box=(x,y,x+1,y+1)
                r,g,b=im.getpixel((x, y))
                rp=r/255
                gp=g/255
                bp=b/255
                k=1-max(rp,gp,bp)
                w=min(rp,gp,bp)
                m=(rp-w)/(1-k) if k!=1 else 0
                ki.paste((int(k*255)),box)
                mi.paste((int(m*255)),box)
        ki=ki.convert("1")
        mi=mi.convert("1")
    else:
        raise Exception("Not known colour mode")

    mode_width = (6 if mode & 64 else (3 if mode & 32 else 1))
    line_height = overscan *mode_width
    top = 0
    left = 0
    image = b""
    lines = 0 #in printer dpi
    while left < width_pixels:
        remaining_pixels = width_pixels - left
        
        if cut:
            if left == (-(width_pixels+7+8)//8*8+10*8)%((width_pixels)//8*8+8):
                image += ESC + b"i"

        for i in range(0,overscan):
            
            if colour == 'cmyk':
                colours =  (4,1,2,0)
            elif colour == 'rk':
                colours = (1,0)
            elif colour == 'k':
                colours = (0,)
            for col in colours:
                
                switcher={
                        4: yi,
                        2: ci,
                        1: mi,
                        0: ki,
                        }
                #, and extract blobs for each 8 or 24-pixel row
                box = (left + i, top, left + line_height*8 + i, top + height_pixels)
                slice = switcher[col].transform((line_height*8, height_pixels), Image.EXTENT, box)
                data = slice.tobytes()
            
                assert len(data) % line_height == 0
                assert len(data) == height_pixels * line_height

                if printer == "oki":
                    image += ESC + struct.pack("<BH",b"KLYZ"[mode],len(data)//(line_height))
                else:
                    image += ESC + b"r" + struct.pack("<B",col)
                    # Generate ESC/POS header
                    image += ESC + b"*" + struct.pack("<BH",mode,len(data)//(line_height))

                ai = 0
                for j in range(0, len(data), line_height):
                    value = bitstring.Bits(data[j:j+mode_width*overscan]).uintbe
                    sparse = value
                    byte = 0x00
                    for k in range(0, mode_width*8):
                        #100100100100100100100100
                        byte |= ((1 << (overscan * k + overscan - 1)) & sparse) >> (overscan * k - k + overscan - 1 )
                    ai+=mode_width
                    image += bitstring.Bits(uintbe=byte, length=mode_width*8).tobytes()
                    
                image += b"\r"

                assert ai == len(data)//overscan

            if i < overscan-1:
                linewidth=skip
            else:
                linedpi={"24pin":6,"lq510":3,"oki":3,"9pin":3,"escpos":2}[printer]
                linewidth = linedpi*8-(overscan-1)*skip

            if printer == "24pin":
                image += ESC + b"+" + struct.pack("<B",linewidth) + b"\n"
            elif printer == "lq510":
                image += b"\r" + ESC + b"J" + struct.pack("<B",24)
            elif printer == "9pin":
                image += ESC + b"J" + struct.pack("<B",linewidth) + b"\r"
            elif printer == "oki":
                image += b"\r" + ESC + b"J" + struct.pack("<B",24)
            elif printer == "escpos":
                image += ESC + b"3" + struct.pack("<B",linewidth) + b"\n"
            else:
                raise Exception('not known printer')
            lines +=linewidth

        left += line_height*8
    if cut:
        image +=b"\r\n"

    return image, lines

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
                    default='k', type=str,
                    help='use colours')
    parser.add_argument('-m', '--mode', default=5, type=int,
                    help='mode to use for printing')
    parser.add_argument('-o', '--overscan', default=1, type=int,
                    help='vertical resolution multiplier')
    parser.add_argument('-s', '--skip', default=1, type=int,
                    help='how much n/(216/360)dpi jump when overscanning')
    parser.add_argument('-w', '--paper-width', default=0, type=int,
                    help='set paper width in escpos ("GS ( E <5> <3>")')
    parser.add_argument('-l', '--left-offset', default=0, type=int,
                    help='append white on left side for alignment')
    parser.add_argument('--cut', action="store_true",
                    help='papercut top image')
    parser.add_argument('-n','--count', default=1, type=int,
                    help='print n times')

    args = parser.parse_args()

    # Load Image
    im = Image.open(args.input)
    
    if args.left_offset:
        im = ImageOps.pad(im,
                          [sum(x) for x in zip(im.size,(args.left_offset,0))],
                          method=Image.Resampling.NEAREST,
                          centering=(1,0.5),
                          color='#fff')

    if args.output == '-':
        fp=os.fdopen(sys.stdout.fileno(), 'wb')
    else:
        fp=open(args.output,'wb')
   
    # Initialize printer

    if args.paper_width:
        fp.write(b'\x1d(E\x03\x00\x01IN')
        fp.write(b'\x1d(E\x04\x00\x05\x03' + struct.pack('<H',args.paper_width))
        fp.write(b'\x1d(E\x04\x00\x02OUT')

    if args.printer == "oki":
        fp.write(b'\x18' + ESC + b'\x55\x00')
    else:
        fp.write(ESC + b'@' + ESC + b'P' + ESC + b'l\x00' + b'\r' + ESC + b'Q\x00')

    blob, lines = _to_column_format(im,
            printer=args.printer,
            colour=args.colour,
            mode=args.mode,
            overscan=args.overscan,
            skip=args.skip,
            cut=args.cut)
    for _ in range(args.count):
        fp.write(blob)
