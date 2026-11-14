Plan:

- CLI: accept FILE1 [FILE2 ...], process multiple files.

- File validation: check whether a file exists, whether it can be opened, and whether the format is supported.

- Basic attributes: retrieve the format, size and colour mode.

- EXIF extraction: retrieve EXIF tags, if present.
    - Creation date should mean EXIF `DateTimeOriginal`, with filesystem timestamps as different value.

- Readable output: convert numeric tag IDs and values into human-readable output.

- Error handling: a single problematic file should not halt the processing of all subsequent files. Unsupported extensions and corrupted files should produce clear per-file errors.

- Optionally add metadata modification/deletion later.

----

Pillow — a Python library for working with images.

Here are the main tools:

```python
from PIL import Image, ExifTags

image = Image.open("photo.jpg")

print(image.format)
print(image.size)
print(image.mode)

exif = image.getexif()

for tag_id, value in exif.items():
    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
    print(tag_name, value)
```