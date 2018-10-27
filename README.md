# beep-downloader

Download all your courses' files-and-documents from BeeP!

BeeP = Be-e-Poli, the Politecnico of Milan's platforms for managing the courses files.

## Usage

You'll need Python>=3.5 in order to run this, and you'll also need to install some dependencies:

- `requests`
- `colorama`

The easiest way is to use a virtualenv and run `pip intall -r requirements.txt`

Then you can simply run `./beep-downloader.py` and enjoy! By default a folder named `results` is created in the current working directory.

## Tips

Run `./beep-downloader.py --help` to see the various options!

If you have installed `aria2` the download will be a lot faster :P
