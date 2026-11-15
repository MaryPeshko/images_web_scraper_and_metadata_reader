Sites

- https://crawler-test.com/

Several tests:
- Image Links — whether spider finds images through links.
- Relative Link — whether relative URLs are handled correctly.
- Repeated internal links — whether spider avoids looping on repeated links.
- Broken Links Internal — whether navigation errors are handled.

- https://www.42berlin.de/

```bash
python3 spider.py -r -l 2 -p data_2 https://www.42berlin.de/
```

**A. Core functionality**

<table>
<tr>
<th> Test </th>
<th> What to check </th>
</tr>
<tr>
<td>

Page with multiple images

Images with different URLs

Recursive links

Repeated links

Unsupported extension

</td>
<td>

Whether all supported formats are downloaded

Absolute, root-relative, and relative URLs

Whether spider finds images on child pages

Whether the same image is not downloaded multiple times

Whether it ignores, for example, `.svg` or `.webp` if they are not required

</td>
</tr>
</table>

**B. Edge cases**

<table>
<tr>
<th> Test </th>
<th> What to check </th>
</tr>
<tr>
<td>

Page without images

Page without links

Two pages linking to each other

Missing page (404)

Unavailable server

Identical file names

</td>
<td>

The program does not crash

Recursion terminates normally

There is no infinite recursion

The error is handled and the program does not crash

The connection error is handled

One file must not silently overwrite another

</td>
</tr>
</table>

**C. Command-line options**

Check all options required by the assignment:
- `-r` — recursive downloading.
- `-l N` — recursion depth limit.
- `-p PATH` — custom directory for saving files.
- Missing argument after `-p` or `-l`.
- Unknown option.
- Running without a URL.
