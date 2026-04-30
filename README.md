# מפענח T9 עברי — Hebrew T9 Decoder

A Windows desktop application that decodes T9 digit sequences into Hebrew text,
using the Israeli phone keypad layout and the Hspell-based Hebrew dictionary.

---

## Example

```
Input:  6725076270255037623
Output: חתול שחור הלך ברחוב
```

---

## Key mapping

| Key | Letters         | Key | Letters         |
|-----|-----------------|-----|-----------------|
| 2   | ד ה ו           | 6   | ז ח ט           |
| 3   | א ב ג           | 7   | ר ש ת           |
| 4   | מ ם נ ן         | 8   | צ ץ ק           |
| 5   | י כ ך ל         | 9   | ס ע פ ף         |
| 0   | *(word space)*  |     |                 |

---

## How it works

1. **Digit-to-letter mapping** — each digit represents a set of Hebrew letters
   (one keypress per letter, predictive T9 style).
2. **Word segmentation** — the digit `0` separates words.
3. **Dictionary lookup** — for each segment all possible letter combinations are
   generated and matched against the bundled Hebrew dictionary
   ([LibreOffice/he_IL](https://github.com/LibreOffice/dictionaries/tree/master/he_IL),
   based on [Hspell](http://hspell.ivrix.org.il/) by Nadav Har'El).
4. **Alternative selection** — the UI shows all dictionary matches per word;
   click any alternative to replace it in the result.

---

## Running from source

No external packages are needed; the app uses only the Python standard library.

```bash
python main.py
```

On first run the dictionary is downloaded once and cached in
`%APPDATA%\T9Hebrew\he_IL.dic`.

---

## Building the EXE locally

```bash
pip install pyinstaller

# Download dictionary first
python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/LibreOffice/dictionaries/master/he_IL/he_IL.dic', 'he_IL.dic')"

# Build
pyinstaller --onefile --windowed --name T9Hebrew --add-data "he_IL.dic;." main.py
```

The EXE will be at `dist/T9Hebrew.exe`.

---

## CI/CD

GitHub Actions builds the EXE automatically on every push to `main`/`master`.
Tag a commit as `v1.0.0` (or any `v*` pattern) to also create a GitHub Release
with the EXE attached.

---

## Dictionary licence

The bundled Hebrew dictionary is based on **Hspell** (LGPL) as distributed by
the [LibreOffice Dictionaries](https://github.com/LibreOffice/dictionaries)
project (also used by Mozilla Firefox).

---

## Project structure

```
t9-hebrew/
├── main.py              # GUI application (tkinter)
├── t9_decoder.py        # T9 decoding logic
├── hebrew_dict.py       # Dictionary download & management
├── requirements-build.txt
├── README.md
└── .github/
    └── workflows/
        └── build.yml    # Windows EXE build + GitHub Release
```
