Test files are in img_test/ directory

```python
python3 scorpion.py img_test/peacock.jpg

python3 scorpion.py img_test/maxresdefault_17.jpg

python3 scorpion.py \
  img_test/maxresdefault_17.jpg \
  img_test/maxresdefault_18.jpg

python3 scorpion.py \
  img_test/missing.jpg

python3 scorpion.py img_test/its_png.png

python3 scorpion.py img_test/Wolf_Berlin_gif.gif
```

More images for tests:

https://commons.wikimedia.org/

Decompression bomb test

`DecompressionBombWarning`

```bash
python -c "from pathlib import Path; from PIL import Image; import scorpion as s; Image.MAX_IMAGE_PIXELS = 5_000_000; s.process_file(Path('img_test/peacock.jpg'), 1)" 
```

This test lowers Pillow's built-in pixel limit only for this Python process.
`peacock.jpg` contains about 9,144,576 pixels, which is more than 5,000,000
but less than twice that limit. Pillow therefore raises
`DecompressionBombWarning` while opening the image. Scorpion converts that
warning into an exception and reports that the image was rejected.

- `s.process_file(...)` runs Scorpion's normal image-processing path.
- `Path('img_test/peacock.jpg')` selects the test image.
- `1` supplies the image number used in Scorpion's output.

`DecompressionBombError`

Pillow raises it when the image exceeds roughly twice Image.MAX_IMAGE_PIXELS.

```bash
python -c "from pathlib import Path; from PIL import Image; import scorpion as s; Image.MAX_IMAGE_PIXELS = 4_000_000; s.process_file(Path('img_test/peacock.jpg'), 1)"
```
