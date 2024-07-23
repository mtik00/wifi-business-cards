#!/usr/bin/env python3

import json
from itertools import product
from typing import Dict, Iterable, List

import qrcode
import typer
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

app = typer.Typer()

WIFI_QR_CODE_FORMAT = "WIFI:T:{encryption_type};S:{ssid};P:{password};;"


LABEL_CONFIG = {
    "label-height": 2 * inch,
    "label-width": 3.5 * inch,
    # From the left side of the page to the left side of the label
    "x-start": 0.75 * inch,
    # From the bottom of the page to the bottom of the label
    "y-start": 0.52 * inch,
    # How far from the left side of the label to start drawing
    "x-offset": 0.1 * inch,
    # How far from the top of the label to start drawing
    "y-offset": 0.1 * inch,
    "pagesize": letter,
    "columns": 2,
    "rows": 5,
}


def register_fonts():
    pdfmetrics.registerFont(
        TTFont("normal", "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf")
    )
    pdfmetrics.registerFont(
        TTFont("mono", "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf")
    )
    pdfmetrics.registerFont(
        TTFont("bold", "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf")
    )


def validate_data(data: List) -> None:
    card_count = 0
    columns = LABEL_CONFIG["columns"]
    rows = LABEL_CONFIG["rows"]
    max_cards = columns * rows
    errors = []

    for config in data:
        if "coords" in config:
            card_count += len(config["coords"])
            for row, column in config["coords"]:
                if (row > rows - 1) or (column > columns - 1):
                    errors.append(f"ERROR: Invalid coord: {row},{column}")

    if card_count > max_cards:
        errors.append(
            f"ERROR: Too many cards defined: {card_count}. Maximum is {max_cards}"
        )

    if errors:
        print("\n".join(errors))
        raise Exception("Invalid data")


def load_data(filename: str):
    with open(filename) as fileobject:
        data = json.load(fileobject)

    validate_data(data)
    return data


def get_qrcode_pil(ssid: str, password: str, encryption_type: str = "WPA"):
    """
    Formats the Wi-Fi string and returns QR code in PIL format.
    """
    qr_text = WIFI_QR_CODE_FORMAT.format(
        ssid=ssid, password=password, encryption_type=encryption_type
    )

    print(qr_text)
    return qrcode.make(qr_text).get_image()


def fit_text_to_width(text: str, width: float, font: str, font_size: int = 12) -> int:
    """Calculate an appropriate size for the given dimensions.

    :param string text: The text to use for the calculation
    :param float width: The size, in inches, to fit the text to
    :param string font: The font to use
    :param int font_size: The initial font size to use

    :rtype: int
    :returns: font_size
    """
    calculated_width = stringWidth(text, font, font_size)

    while calculated_width > width:
        font_size -= 1
        calculated_width = stringWidth(text, font, font_size)

    return font_size


def draw_card(
    row: int,
    column: int,
    data: Dict[str, str],
    qrcode_pil,
    canvas: canvas.Canvas,
    box: bool = False,
):
    """
    Draws a single card
    """
    x_start = LABEL_CONFIG["x-start"] + (LABEL_CONFIG["label-width"] * column)
    y_start = (
        LABEL_CONFIG["y-start"]
        + LABEL_CONFIG["label-height"]
        + (LABEL_CONFIG["label-height"] * row)
    )

    if box:
        y = y_start - LABEL_CONFIG["label-height"]
        x = x_start
        canvas.rect(
            height=LABEL_CONFIG["label-height"],
            width=LABEL_CONFIG["label-width"],
            x=x_start,
            y=y,
        )

    x_offset = LABEL_CONFIG["x-offset"]
    y_offset = LABEL_CONFIG["y-offset"]
    header_offset = 0.3 * inch
    newline_offset = 0.2 * inch
    section_offset = 0.5 * inch
    qrcode_size = 0.9 * inch

    x = x_start + x_offset

    pil = ImageReader(qrcode_pil)
    canvas.drawImage(
        pil, x, y_start - qrcode_size - y_offset, width=qrcode_size, height=qrcode_size
    )

    y = y_start - y_offset * 4  # Fudge factor for title string
    x = x_start + 1.0 * inch

    canvas.setFont("bold", 14)
    canvas.drawString(x, y, data["name"])

    y -= header_offset
    canvas.setFont("normal", 14)
    canvas.drawString(x, y, "SSID:")

    y -= newline_offset
    canvas.setFont("mono", 14)
    canvas.drawString(x, y, data["ssid"])

    # Left-align the password section
    x = x_start + x_offset
    y -= section_offset
    canvas.setFont("normal", 14)
    canvas.drawString(x, y, "Password:")

    y -= newline_offset
    width = LABEL_CONFIG["label-width"] - (2 * x_offset)
    size = fit_text_to_width(data["password"], width, "mono", 14)
    canvas.setFont("mono", size)
    canvas.drawString(x, y, data["password"])


def generate_map(coords: Iterable, wifi_data: List[Dict]) -> Dict[tuple, Dict]:
    """
    Create a list of coordinates and the wifi data to use.

    Returns a generator with only valid coordinates.
    """
    wifi_data_mapping: Dict[tuple, Dict] = {x: {} for x in coords}

    default_network = None
    default_networks = [x for x in wifi_data if "coords" not in x]
    if len(default_networks) > 1:
        raise ValueError(
            "Only one wifi network is allowed to use default coords.  You must specify `coords` on more or more networks"
        )
    elif len(default_networks) == 1:
        default_network = default_networks[0]

    # Go through each item that has explicit coordinates
    specific_networks = (x for x in wifi_data if "coords" in x)
    for network in specific_networks:
        for coord in network["coords"]:
            wifi_data_mapping[tuple(coord)] = network

    # Fill in the blanks with the default network, if any.
    if default_network:
        for x in [x for x in wifi_data_mapping if not wifi_data_mapping[x]]:
            wifi_data_mapping[x] = default_network

    # Filter out everything that wasn't defined above.
    return filter_network_map(wifi_data_mapping)


def filter_network_map(wifi_data_mapping):
    """A generator function that only yields valid network info."""
    for coords, network in wifi_data_mapping.items():
        if network:
            yield (coords, network)


def generate_pdf(wifi_data: List[Dict], outfile: str, draw_boxes: bool = False):
    """
    Generates the PDF by iterating over the columns and rows based on the data.
    """
    pdf_canvas = canvas.Canvas(outfile, pagesize=LABEL_CONFIG["pagesize"])
    pdf_canvas.setTitle("WiFi Business Cards")
    all_rows = range(LABEL_CONFIG["rows"])
    all_columns = range(LABEL_CONFIG["columns"])

    all_coords = product(all_rows, all_columns)
    coord_map = generate_map(all_coords, wifi_data)

    for coord, network in coord_map:
        qrcode = get_qrcode_pil(
            ssid=network["ssid"],
            password=network["password"],
            encryption_type=network["encryption_type"],
        )
        row, column = coord
        draw_card(row, column, network, qrcode, pdf_canvas, box=draw_boxes)

    pdf_canvas.save()


@app.command()
def main(datafile: str, outfile: str, draw_boxes: bool = False):
    register_fonts()
    data = load_data(datafile)
    generate_pdf(data, outfile, draw_boxes=draw_boxes)


if __name__ == "__main__":
    app()
