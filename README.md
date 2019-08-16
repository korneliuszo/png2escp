# png2escp
Print pixel perfect graphics on dot matrix printers and rendering draft fonts from romdumps
## Getting started

### Prerequsites
```
Python3
PIL
bitstring (pip3 install bitstring)
```

## Using printer
```
./collumnFormat <input> >> /dev/usb/lp0
```
### Examples
For 9pin 120x72 dpi 
```
./collumnFormat -p 9pin -m 1 <input>
```
For 9pin 120x216 dpi 
```
./collumnFormat -p 9pin -m 1 -o 3 <input>
```
For 24pin 120x120 dpi 
```
./collumnFormat -p 24pin -m 1 -o 2 -s 3 <input>
```
For 24pin 180x360 dpi 
```
./collumnFormat -p 24pin -m 39 -o 2 <input>
```

## Fonts

### Generating fonts
```
./crop.sh
./topng9.py
./topng24.py
```

### Using font
```
echo "Multiline text" | ./fontrenderer.py -f out9 output.png
```

