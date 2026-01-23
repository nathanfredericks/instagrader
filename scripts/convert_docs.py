# /// script
# dependencies = [
#     "markitdown",
# ]
# ///

from pathlib import Path
from markitdown import MarkItDown


def convert_docs(start_dir: str):
    md_converter = MarkItDown()

    start_path = Path(start_dir)
    if not start_path.exists():
        print(f"Directory not found: {start_dir}")
        return

    files_to_convert = []
    for file_path in start_path.rglob("*"):
        if file_path.suffix.lower() in [".pdf", ".docx"]:
            files_to_convert.append(file_path)

    for file_path in files_to_convert:
        output_path = file_path.with_suffix(".md")

        if output_path.exists():
            print(f"Skipping {file_path.name}")
            continue

        print(f"Converting {file_path.name}...")
        try:
            result = md_converter.convert(str(file_path))

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.text_content)

            print(f"Saved to {output_path}")
        except Exception as e:
            print(f"Failed to convert {file_path.name}: {e}")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    dataset_dir = script_dir.parent / "dataset"
    convert_docs(str(dataset_dir))
