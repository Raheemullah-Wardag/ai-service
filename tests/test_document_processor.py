import unittest

from services.document_processor import process_pdf_bytes


class DocumentProcessorTests(unittest.TestCase):
    def _build_pdf_bytes(self, page_texts: list[str]) -> bytes:
        objects: list[str] = []
        page_refs: list[int] = []
        font_obj_id = 5

        for index, text in enumerate(page_texts, start=1):
            content_obj_id = 2 * index + 1
            page_obj_id = content_obj_id + 1
            objects.append(f"{content_obj_id} 0 obj\n<< /Length 0 >>\nstream\nBT /F1 12 Tf 72 720 Td ({self._escape_pdf_text(text)}) Tj ET\nendstream\nendobj")
            objects.append(f"{page_obj_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_obj_id} 0 R /Resources << /Font << /F1 {font_obj_id} 0 R >> >> >>\nendobj")
            page_refs.append(page_obj_id)

        catalog_obj = "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj"
        pages_obj = "2 0 obj\n<< /Type /Pages /Kids [" + " ".join(f"{page_id} 0 R" for page_id in page_refs) + f"] /Count {len(page_refs)} >>\nendobj"
        font_obj = f"{font_obj_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj"

        pdf_objects = [catalog_obj, pages_obj, font_obj] + objects
        offsets: list[int] = []
        pdf = b"%PDF-1.4\n"
        for obj in pdf_objects:
            offsets.append(len(pdf))
            pdf += f"{len(obj.splitlines())} 0 obj\n".encode("latin-1")
            pdf += obj.encode("latin-1")
            pdf += b"\n"

        xref_offset = len(pdf)
        pdf += b"xref\n0 10\n0000000000 65535 f \n"
        for offset in offsets:
            pdf += f"{offset:010d} 00000 n \n".encode("ascii")
        pdf += f"trailer\n<< /Size 10 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
        return pdf

    def _escape_pdf_text(self, text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def test_process_pdf_bytes_returns_chunks(self) -> None:
        pdf_bytes = self._build_pdf_bytes(["A" * 1200, "B" * 1300, "C" * 1500])

        chunks = process_pdf_bytes(pdf_bytes, filename="sample.pdf")

        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["page_number"], 1)
        self.assertEqual(chunks[0]["chunk_index"], 0)
        self.assertIn("content", chunks[0])
        self.assertTrue(chunks[0]["content"].startswith("A"))

    def test_process_pdf_bytes_rejects_non_pdf_extension(self) -> None:
        with self.assertRaises(ValueError):
            process_pdf_bytes(b"%PDF-1.4\n", filename="sample.txt")

    def test_process_pdf_bytes_rejects_non_pdf_magic_bytes(self) -> None:
        with self.assertRaises(ValueError):
            process_pdf_bytes(b"not a pdf", filename="sample.pdf")


if __name__ == "__main__":
    unittest.main()
