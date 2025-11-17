import fitz  # PyMuPDF
import os

def compress_pdf(input_path, output_path, dpi=120, quality=60):
    """
    Compress PDF by downscaling and recompressing images.
    :param input_path: Original PDF file
    :param output_path: Compressed PDF file
    :param dpi: Image resolution (lower = smaller file, 72/96/120 recommended)
    :param quality: JPEG quality (30–95, lower = smaller file, 60 is good balance)
    """
    doc = fitz.open(input_path)
    mat = fitz.Matrix(dpi / 72, dpi / 72)  # scale factor (72 is default)

    new_doc = fitz.open()
    for page in doc:
        # Render each page as a pixmap (raster image)
        pix = page.get_pixmap(matrix=mat)
        img_page = new_doc.new_page(width=pix.width, height=pix.height)
        img_page.insert_image(img_page.rect, pixmap=pix, keep_proportion=True, quality=quality)

    # Save new compressed PDF
    new_doc.save(output_path, garbage=4, deflate=True)
    new_doc.close()

    size_kb = os.path.getsize(output_path) // 1024
    print(f"Compressed PDF saved: {output_path} ({size_kb} KB)")


# Example usage
compress_pdf(
    "/Users/chiragkhanduja/PycharmProjects/PythonProject11/degree.pdf",
    "/Users/chiragkhanduja/PycharmProjects/PythonProject11/degree_compressed.pdf",
    dpi=120,
    quality=60
)
