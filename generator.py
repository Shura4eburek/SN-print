import io
import qrcode
import barcode
from barcode.writer import ImageWriter
from PIL import Image


def _fit_to_canvas(img: Image.Image, width_px: int, height_px: int) -> Image.Image:
    """Вписать изображение в заданный размер без растяжения, фон белый."""
    img.thumbnail((width_px, height_px), Image.LANCZOS)
    canvas = Image.new("RGB", (width_px, height_px), "white")
    x = (width_px - img.width) // 2
    y = (height_px - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def generate_qr(data: str, size_px: tuple) -> io.BytesIO:
    width_px, height_px = size_px

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = _fit_to_canvas(img, width_px, height_px)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generate_barcode(data: str, size_px: tuple) -> io.BytesIO:
    width_px, height_px = size_px

    writer = ImageWriter()
    code128 = barcode.get("code128", data, writer=writer)

    options = {
        "write_text": False,
        "dpi": 300,
    }
    raw = io.BytesIO()
    code128.write(raw, options=options)
    raw.seek(0)

    img = Image.open(raw).convert("RGB")
    img = _fit_to_canvas(img, width_px, height_px)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
