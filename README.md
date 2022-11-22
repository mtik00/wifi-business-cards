# wifi-business-cards
A Python app to create Avery 5371 business cards from Wi-Fi credentials.

I recently went through a home network overhaul with UniFi equipment.  Part of that process was creating multiple Wi-Fi networks: one for my home users, one for my IoT devices, and one for guests.  I also learned that many mobile phones allow you to scan a QR code to join a network instead of selecting the SSID and entering the password.  The idea was born!

I first created the QR code and printed out the credentials on paper... n00b

I then had the thought of making up business cards I could hand out to my guests who needed the Wi-Fi credentials.

## Usage

Setup is pretty rudimentary.  Aside from the Python package, the app requires a JSON file at `instance/data.json` that's a hash with three keys: `name`, `ssid`, and `password`.

Create the PDF file with:

    python -m wifi_business_cards <path to data.json> <path to output pdf>

The single-page output can be printed on Avery 5371 Business Cards.

## Installation

Clone the repo and then:

    poetry install

The only things you need are `qrcode` and `reportlab`, so you could also `pip install qrcode reportlab` and then run the module.  _Technically_ the module also relies on `typer`.

Surely you'll need to modify the fonts used if you aren't running this on an Ubuntu-based Linux distribution.

## Notes

Make sure you print a test page.  You'll need to make sure you have **NO** auto-scaling or auto-centering!

I couldn't figure out a way to print this with default _Docuement Viewer_ application on Linux Mint.  It kept messing with the margins.  I have to print it using something else.  Chrome worked fine.

The PDF is built from the bottom-left to the top-right.  Row `0`, Column `0`, is the bottom left.  You can use the `coords` key in your data JSON to list all of the coordinates to print.  This is helpful if you're printing multiple networks on the same sheet.

## Data File
The data file that gets parsed is JSON format with a `list` being the base element.

One network example:
```json
[
    {
        "name": "Guest Wi-Fi",
        "ssid": "nowhere-guest",
        "password": "changeme"
    }
]
```

All cards will use the same network credentials.

Multiple network example:
```json
[
    {
        "name": "Home Wi-Fi",
        "ssid": "nowhere",
        "password": "battery-horse-staple",
        "coords": [
            [0,0], [0,1], [1,0], [1,1]
        ]
    },
    {
        "name": "Guest Wi-Fi",
        "ssid": "nowhere-guest",
        "password": "changeme"
    }
]
```
In this scenario, we're only using the bottom two rows for the first network.  The rest of the cards will be filled with the second network's credentials.  Any network _without_ the `coords` key:value will always use the rest of the available cards.  **There can be only one "default" network!**

Avery 5371 is a 2-column, 5-row, template.  The bottom-left card is `0,0`.
