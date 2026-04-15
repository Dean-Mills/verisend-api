import fitz
import asyncio
import io


def extract_page_images(file_path: str, dpi: int) -> list[bytes]:
    """
    Render each page of a PDF as a PNG image.
    
    Args:
        file_path: Path to the PDF file
        dpi: Resolution for rendering (150 is good balance of quality/size)
        
    Returns:
        List of PNG image bytes, one per page
    """
    doc = fitz.open(file_path)
    
    image_bytes = []
    for page in doc:
        # Render page to pixmap
        pix = page.get_pixmap(dpi=dpi)
        image_bytes.append(pix.tobytes("png"))
    
    doc.close()
    return image_bytes


async def extract_page_images_async(file_path: str, dpi: int = 300) -> list[bytes]:
    """Async wrapper for extract_page_images."""
    return await asyncio.to_thread(extract_page_images, file_path, dpi)


def render_first_page_thumbnail(
    pdf_bytes: bytes,
    max_width: int = 400,
    jpeg_quality: int = 75,
) -> bytes:
    """Render page 1 of a PDF to a JPEG thumbnail. Returns JPEG bytes."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = doc.load_page(0)
        page_width = page.rect.width or max_width
        scale = max_width / page_width
        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        return pix.tobytes("jpeg", jpg_quality=jpeg_quality)
    finally:
        doc.close()


async def render_first_page_thumbnail_async(
    pdf_bytes: bytes,
    max_width: int = 400,
    jpeg_quality: int = 75,
) -> bytes:
    """Async wrapper for render_first_page_thumbnail."""
    return await asyncio.to_thread(
        render_first_page_thumbnail, pdf_bytes, max_width, jpeg_quality
    )