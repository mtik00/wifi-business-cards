#!/usr/bin/env python3

import json
from typing import Dict

import qrcode
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
import typer

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


def load_data(filename: str):
    with open(filename) as fileobject:
        data = json.load(fileobject)
    return data


def get_qrcode_pil(ssid: str, password: str, encryption_type: str = "WPA"):
    """
    Formats the Wi-Fi string and returns QR code in PIL format.
    """
    qr_text = WIFI_QR_CODE_FORMAT.format(
        ssid=ssid, password=password, encryption_type=encryption_type
    )

    return qrcode.make(qr_text).get_image()


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

    x = x_start + x_offset

    pil = ImageReader(qrcode_pil)
    size = 0.9 * inch
    canvas.drawImage(pil, x, y_start - size - y_offset, width=size, height=size)

    y = y_start - y_offset * 4  # Fudge factor for title string
    x = x_start + 1.0 * inch

    canvas.setFont("bold", 14)
    canvas.drawString(x, y, data["name"])

    y -= 0.3 * inch
    canvas.setFont("normal", 14)
    canvas.drawString(x, y, "SSID:")

    y -= 0.2 * inch
    canvas.setFont("mono", 14)
    canvas.drawString(x, y, data["ssid"])

    x = x_start + x_offset
    y -= 0.5 * inch
    canvas.setFont("normal", 14)
    canvas.drawString(x, y, "Password:")

    y -= 0.3 * inch
    canvas.setFont("mono", 14)
    canvas.drawString(x, y, data["password"])


def generate_pdf(wifi_data: Dict[str, str], outfile: str, draw_boxes: bool = False):
    """
    Generates the PDF by iterating over the columns and rows based on the data.
    """
    qrcode = get_qrcode_pil(ssid=wifi_data["ssid"], password=wifi_data["password"])
    pdf_canvas = canvas.Canvas(outfile, pagesize=LABEL_CONFIG["pagesize"])
    pdf_canvas.setTitle("WiFi Business Cards")

    if "coords" in wifi_data:
        for row, column in wifi_data["coords"]:
            draw_card(row, column, wifi_data, qrcode, pdf_canvas, box=draw_boxes)
    else:
        for row in range(LABEL_CONFIG["rows"]):
            for column in range(LABEL_CONFIG["columns"]):
                draw_card(row, column, wifi_data, qrcode, pdf_canvas, box=draw_boxes)

    pdf_canvas.save()


@app.command()
def main(datafile: str, outfile: str, draw_boxes: bool = False):
    register_fonts()
    data = load_data(datafile)
    generate_pdf(data, outfile, draw_boxes=draw_boxes)


if __name__ == "__main__":
    app()
