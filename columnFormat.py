#!/usr/bin/env python
"""
This is a minimal ESC/POS printing script which uses the 'column format'
of image output.

The snippet is designed to efficiently delegate image processing to
PIL, rather than spend CPU cycles looping over pixels.

Do not attempt to use this snippet in production, get a copy of python-escpos instead!
"""

from PIL import Image, ImageOps
import struct
import sys
import os

ESC = b"\x1b";

def _to_column_format(im):
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

    line_height = 8*3*2
    top = 0
    left = 0
    while left < width_pixels:
        remaining_pixels = width_pixels - left
        
        for i in range(0,2):

            for colour in (4,2,1,0):
                
                switcher={
                        4: yi,
                        2: ci,
                        1: mi,
                        0: ki,
                        }

                box = (left + i, top, left + line_height + i, top + height_pixels)
                slice = switcher[colour].transform((line_height, height_pixels), Image.EXTENT, box)
                data = slice.tobytes()
            
                assert len(data) % 6 == 0
                assert len(data) == height_pixels * 6

                yield ESC + b"r" + struct.pack("<B",colour)

                yield ESC + b"*" + struct.pack("<BH",39,len(data)//6)

                ai = 0
                for j in range(0, len(data), 2*3):
                    value = struct.unpack(">Q",b'\x00\x00'+data[j:j+3*2])[0]
                    sparse = value
                    byte = 0x00
                    for k in range(0, 24):
                        #100100100100100100100100
                        byte |= ((1 << (2 * k + 1)) & sparse) >> (2 * k - k +1)
                    ai+=3
                    yield struct.pack(">I",byte)[1:4]
                    
                yield b"\r"

            assert ai == len(data)//2

            if i < 1:
                yield b"\r" + ESC + b"+" + struct.pack("<B",1) + b"\n"
            else:
                yield b"\r" + ESC + b"+" + struct.pack("<B",48-1) +b"\n"
        left += line_height

if __name__ == "__main__":
    # Configure
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = u"tulips.png"
    
    # Load Image
    im = Image.open(filename)
    
    # Initial rotate. mirror, and extract blobs for each 8 or 24-pixel row
    # Convert to black & white via greyscale (so that bits can be inverted)

    # Generate ESC/POS header and print image
    # Height and width refer to output size here, image is rotated in memory so coordinates are swapped
   
    with os.fdopen(sys.stdout.fileno(), 'wb') as fp:
        fp.write(ESC + b'@' + ESC + b'P' + ESC + b'l\x00' + b'\r' + ESC + b'Q\x00')
        for blob in _to_column_format (im):
            fp.write(blob)
