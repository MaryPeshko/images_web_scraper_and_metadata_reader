# Scorpion

Displays basic image attributes, creation date, and EXIF metadata.

CLI program invoked as 

```bash
./scorpion FILE1 [FILE2 ...].
```

Support `.jpg/.jpeg`, `.png`, `.gif`, and `.bmp`.


Install dependency

```bash
python3 -m pip install -r requirements.txt
```

Help

```bash
python3 spider.py --help
```

---

stat - display file or file system status

SYNOPSIS
       stat [OPTION]... FILE...

## Structure of JPEG

![Structure_of_JPEG.jpg](./img_learn/Structure_of_JPEG.jpg)

EXIF is commonly stored in an APP1 segment in JPEG files.
