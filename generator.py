import io
import textwrap
import qrcode
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont

RENDER_SIZE = 900  # внутренний размер рендера для качества


def _get_font(size: int):
    for name in ["cour.ttf", "courbd.ttf", "DejaVuSansMono.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _add_serial(img: Image.Image, text: str) -> Image.Image:
    """Добавить серийный номер текстом под изображением."""
    w = img.width
    font_size = max(28, w // 13)
    font = _get_font(font_size)

    avg_char_w = font_size * 0.62
    max_chars = max(1, int(w / avg_char_w))
    lines = textwrap.wrap(text, width=max_chars) or [text]

    line_h = int(font_size * 1.35)
    pad = font_size
    text_h = line_h * len(lines) + pad

    result = Image.new("RGB", (w, img.height + text_h), "white")
    result.paste(img, (0, 0))

    draw = ImageDraw.Draw(result)
    y = img.height + pad // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        draw.text(((w - lw) // 2, y), line, fill="black", font=font)
        y += line_h

    return result


def generate_qr(data: str) -> io.BytesIO:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((RENDER_SIZE, RENDER_SIZE), Image.LANCZOS)
    result = _add_serial(img, data)

    buf = io.BytesIO()
    result.save(buf, format="PNG", dpi=(300, 300))
    buf.seek(0)
    return buf


def generate_barcode(data: str) -> io.BytesIO:
    writer = ImageWriter()
    code128 = barcode.get("code128", data, writer=writer)
    raw = io.BytesIO()
    code128.write(raw, options={"write_text": False, "dpi": 300})
    raw.seek(0)

    img = Image.open(raw).convert("RGB")
    aspect = img.height / img.width
    render_h = int(RENDER_SIZE * aspect)
    img = img.resize((RENDER_SIZE, render_h), Image.LANCZOS)
    result = _add_serial(img, data)

    buf = io.BytesIO()
    result.save(buf, format="PNG", dpi=(300, 300))
    buf.seek(0)
    return buf
