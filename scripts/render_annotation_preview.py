import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main(image_path: str, annotation_path: str, output_path: str, font_file: str | None = None) -> None:
    image = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if font_file is None:
        candidates = (
            "C:/Windows/Fonts/msyh.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        )
        font_file = next((p for p in candidates if Path(p).is_file()), None)
    if font_file is None:
        raise RuntimeError("未找到中文字体；请用 --font 指定已确认可用的中文字体文件")
    font = ImageFont.truetype(font_file, 28)
    small_font = ImageFont.truetype(font_file, 18)
    colors = [(38, 103, 255, 225), (255, 105, 92, 225), (41, 167, 102, 225), (181, 100, 255, 225)]

    data = json.loads(Path(annotation_path).read_text(encoding="utf-8"))
    for index, element in enumerate(data["elements"], start=1):
        region = element["region"]
        x, y = region["x"], region["y"]
        right, bottom = x + region["width"], y + region["height"]
        color = colors[(index - 1) % len(colors)]
        fill = (*color[:3], 24)
        draw.rounded_rectangle((x, y, right, bottom), radius=12, outline=color, width=4, fill=fill)
        draw.ellipse((x + 8, y + 8, x + 44, y + 44), fill=color)
        draw.text((x + 19, y + 8), str(index), anchor="ma", font=small_font, fill="white")
        label = f"{index}. {element['label']}  {element['reveal']['direction']}"
        draw.rounded_rectangle((x + 52, y + 8, min(right - 8, x + 52 + len(label) * 19), y + 46), radius=6, fill=(255, 255, 255, 225))
        draw.text((x + 60, y + 12), label, font=small_font, fill=color)
        start = tuple(element["handPath"]["start"])
        end = tuple(element["handPath"]["end"])
        draw.line((start, end), fill=color, width=4)
        draw.polygon((end, (end[0] - 13, end[1] - 7), (end[0] - 13, end[1] + 7)), fill=color)

    result = Image.alpha_composite(image, overlay).convert("RGB")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, quality=95)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成中文区域编号与方向检查图")
    parser.add_argument("image", help="原图路径")
    parser.add_argument("annotation", help="标注 JSON 路径")
    parser.add_argument("output", help="预览图输出路径")
    parser.add_argument("--font", help="已有中文字体文件；默认探测常用系统字体")
    args = parser.parse_args()
    try:
        main(args.image, args.annotation, args.output, args.font)
    except (OSError, RuntimeError) as exc:
        parser.exit(1, f"[err] {exc}\n")
