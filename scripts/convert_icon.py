"""Convert PNG icon to ICO format for Windows EXE."""

from PIL import Image
from pathlib import Path

script_dir = Path(__file__).parent
project_root = script_dir.parent
assets_dir = project_root / "assets"

png_path = assets_dir / "sql_audit_icon.png"
ico_path = assets_dir / "sql_audit_icon.ico"

print(f"Converting {png_path} -> {ico_path}")

img = Image.open(png_path)
img.save(
    ico_path,
    format="ICO",
    sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
)

print("Done!")
