# RetCom

> A fast comic cleaner/typesetter/translator utility.

## Features

- Open and edit `.jpg`, `.png`, `.tiff`, `.zip`, `.rar`, `.cbz`, `.cbr` images/archives.
- Recognize text using optical character recognition.
- Content-aware cleaning using advance inpainting techniques.
- Mask-based cleaning using text boxes.
- Translate text using Google Translate, straight from the software.
- Add text bubbles and change font size and family.
- Easily export and share text boxes and text bubbles with others.
- Immediately export cleaned and typeset pages.

Sounds too good to be true? Check out this demo: _to be added_.

## Installation

Simply run the installer for your platform, and you can use the core features.

If you want to use OCR (optical character recognition) features, you will also need to install [Tesseract-OCR](https://github.com/tesseract-ocr/tesseract). If you don't have Tesseract installed, the app will warn you that OCR features are unavailable each time you launch it, and provides additional instructions for each platform to install it. The same platform-specific instructions are repeated here:

### macOS

Install Brew or MacPorts and run the following command:
```bash
# brew
brew install tesseract

# ports
sudo port install tesseract
```

### Windows

Use the Tesseract installer from [UB Mannheim](https://digi.bib.uni-mannheim.de/tesseract/). In particular, install [`tesseract-ocr-w64-setup-v4.1.0.20190314.exe`](https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-v4.1.0.20190314.exe) (simply go through the installation without checking any additional options). Locate the folder where Tesseract-OCR is installed (usually `C:\Program Files\Tesseract-OCR` or `C:\Program Files (x86)\Tesseract-OCR`), and add this to your PATH variable as follows:

1. Press the Windows button and search for 'Edit the system environment variables'.
2. Click the 'Environment Variables' button on the bottom left.
3. Select 'Path' in the 'System variables' list, and press 'Edit'.
4. In the window that just opened, press 'New', and paste the path to Tesseract-OCR.

That's it, you should be good to go now.

### Linux

Install Tesseract-OCR following the instructions [here](https://tesseract-ocr.github.io/tessdoc/Installation.html). Be sure to install Tesseract v4, since this is directly compatible with the bundled language files.

If you are on Ubuntu, simply run `sudo apt install tesseract-ocr`.

## Usage

More detailed instructions will be added later. For now, check this set of shortcuts out:

### Scene Editor

| Keystroke | Action |
|-|-|
| <kbd>I</kbd> / <kbd>J</kbd> / <kbd>K</kbd> / <kbd>L</kbd> | Move selected; hold <kbd>shift</kbd> to nudge |
| <kbd>A</kbd> | Add box |
| <kbd>shift</kbd>+<kbd>A</kbd> | Select all items |
| <kbd>D</kbd> / <kbd>bcksp</kbd> / <kbd>del</kbd> | Remove selected items |
| <kbd>shift</kbd>+{<kbd>D</kbd> / <kbd>bcksp</kbd> / <kbd>del</kbd>} | Remove flagged items |
| <kbd>E</kbd> | Edit box |
| <kbd>F</kbd> | Flag selected |
| <kbd>shift</kbd>+<kbd>F</kbd> | Unflag selected |
| <kbd>G</kbd> | Group selected |
| <kbd>shift</kbd>+<kbd>G</kbd> | Ungroup selected |
| <kbd>H</kbd> | Hide selected |
| <kbd>shift</kbd>+<kbd>H</kbd> | Unhide all |
| <kbd>S</kbd> | OCR rubberband selection |
| <kbd>shift</kbd>+<kbd>S</kbd> | OCR rubberband tight selection |
| <kbd>R</kbd> | Restore selected |
| <kbd>W</kbd> | Inpaint black |
| <kbd>shift</kbd>+<kbd>W</kbd> | Inpaint white |
| <kbd>[</kbd> | Scale down |
| <kbd>shift</kbd>+<kbd>[</kbd> | Fine scale down |
| <kbd>]</kbd> | Scale up |
| <kbd>shift</kbd>+<kbd>]</kbd> | Fine scale up |

### General Shortcuts

_Note_: Replace <kbd>ctrl</kbd> by <kbd>command</kbd> on macOS.

| Keystroke | Action |
|-|-|
| <kbd>ctrl</kbd>+<kbd>E</kbd> | Export LSTMBox |
| <kbd>ctrl</kbd>+<kbd>shift</kbd>+<kbd>E</kbd> | Export TXTEll |
| <kbd>ctrl</kbd>+<kbd>I</kbd> | Page information |
| <kbd>ctrl</kbd>+<kbd>L</kbd> | Load LSTMBox |
| <kbd>ctrl</kbd>+<kbd>shift</kbd>+<kbd>L</kbd> | Load TXTEll |
| <kbd>ctrl</kbd>+<kbd>O</kbd> | Open image/archive |
| <kbd>ctrl</kbd>+<kbd>P</kbd> | Prescan page |
| <kbd>ctrl</kbd>+<kbd>S</kbd> | Save cleaned image |
| <kbd>ctrl</kbd>+<kbd>shift</kbd>+<kbd>S</kbd> | Save current scene as image |
| <kbd>ctrl</kbd>+<kbd>T</kbd> | Translate page |

### Settings

You can access the `config.json` file in your installation folder (exact location depends on your operating system). The different settings should be somewhat obvious, but detailed documentation will follow soon.

#### Changing OCR/translation language

One thing to look out for is the `language` tag. The default values are for vertical Japanese text, but you can change this by setting `"isVertical" : false` and changing the `language` tag to match one of the files in the `tessdata` folder. You can download more `.traineddata` files [here](https://github.com/tesseract-ocr/tessdata); simply add the files to the `tessdata` folder in the installation location.

The translation language is easily changed by changing the `translationLanguage` tag to a two-letter language code. These language codes can be found in [`translator_constants.py`](src/main/python/translator_constants.py). The source language is set to be detected automatically at the moment, although we will probably add a feature to change this manually.

## Details / Q&A

_Note:_ This section will be greatly expanded upon in the future.

### How do you save OCR results?

We use a modified version of Tesseract's LSTM `.box` format (see [here](https://tesseract-ocr.github.io/tessdoc/TrainingTesseract-4.00.html) for more info), encoding the box to which each glyph belongs, as well as what group it belongs to, if any. This format has the following form:
```
<symbol> <left> <bottom> <right> <top> <group>
```
and uses the `.box` extension.

We use a special character, known as the unit separator ('␟', U+001F), to prevent a textbox from being resized based on its content. This allows you to create masking boxes that only serve to cover text, but are ignored during collation/translation.

### How do you save text bubbles?

We call text bubbles 'ellipsoids' in RetCom, to not confuse them with textboxes. Ellipsoids are encoded in such a way so as to store the width and length, position, font size and family, and content of the ellipsoid.

We follow the following convention:
```
<content> <size> <family> <x> <y> <w> <h>
```

and we use `.ell`. For details on serialization, check the source code.

### How can I make text bold/italic?

You can simply use HTML formatting in the text bubbles, so bold text would be `<b>bold</b>`, and italics would be `<i>italics</>`. Try out other HTML tags and see what work for yourself!

### Can I contribute?

Sure! Just open an issue and we can talk.

### `X` is not working!

Same as above.

### Can you add feature `Y`?

Maybe, open an issue and say how you would go about doing it and why it's useful.

## Dependencies

Besides Tesseract-OCR, we use the following amazing open source dependencies:

| Package | Use |
|-|-|
| [fontTools](https://github.com/fonttools/fonttools) | Character size determination |
| [NumPy](https://numpy.org/) | Numerical support |
| [OpenCV](https://opencv.org/) | Inpainting |
| [Pillow](https://github.com/python-pillow/Pillow) | Image cropping and I/O |
| [rarfile](https://github.com/markokr/rarfile) | RAR file support |
| [requests](https://requests.readthedocs.io/en/master/) | Communication with Google Translate API |

## License
[MIT](https://choosealicense.com/licenses/mit/)