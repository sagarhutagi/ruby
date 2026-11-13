import shutil
import asyncio
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ruby.converter")


class LegacyFormatConverter:
    """Safely converts legacy binary formats (.doc, .ppt, .xls) using headless LibreOffice."""

    @staticmethod
    def is_available() -> bool:
        return shutil.which("libreoffice") is not None or shutil.which("soffice") is not None

    @classmethod
    async def convert_to_pdf(cls, file_path: Path, output_dir: Path) -> Optional[Path]:
        """Convert a legacy document to PDF safely via headless LibreOffice."""
        libreoffice_bin = shutil.which("libreoffice") or shutil.which("soffice")
        if not libreoffice_bin:
            raise RuntimeError("LibreOffice binary not found on host. Legacy conversion unavailable.")

        output_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            libreoffice_bin,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir.resolve()),
            str(file_path.resolve()),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)

            if proc.returncode != 0:
                err = stderr.decode("utf-8", errors="ignore")
                logger.error("LibreOffice conversion failed (%d): %s", proc.returncode, err)
                return None

            converted_pdf = output_dir / f"{file_path.stem}.pdf"
            if converted_pdf.exists():
                return converted_pdf
            return None
        except Exception as e:
            logger.error("Legacy conversion exception: %s", e)
            return None


legacy_converter = LegacyFormatConverter()
