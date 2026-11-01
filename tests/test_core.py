"""核心算法与业务逻辑自测（不依赖 pytest）。

运行：``python tests/run_selftest.py``，或 ``python -m pytest tests``。
每个 ``test_*`` 函数都是一条独立断言，失败时抛出 AssertionError。
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wmh.core import config as config_mod                                    # noqa: E402
from wmh.core import (fft2d, formats, images, pipeline, schemes,  # noqa: E402
                      textmask, watermark)
from wmh.core.constants import SCHEMES, SPIN_DEFAULT            # noqa: E402
from wmh.core.textmask import FontSpec                           # noqa: E402

TEXT = "隐形水印 WaterMark"


# ----------------------------------------------------------------- 测试素材
def make_photo(width: int = 620, height: int = 420) -> Image.Image:
    """合成一张“像照片”的图：渐变背景 + 彩色形状 + 细噪点。"""
    rng = np.random.default_rng(20261030)
    yy, xx = np.mgrid[0:height, 0:width]
    base = np.stack([
        xx / width * 200 + 40,
        yy / height * 160 + 60,
        (xx + yy) / (width + height) * 180 + 50,
    ], axis=-1).astype(np.float32)
    base = base + rng.normal(0, 6, base.shape)
    image = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    draw = ImageDraw.Draw(image)
    draw.ellipse([width // 4, height // 4, width // 2, height // 2], fill=(220, 40, 90))
    draw.rectangle([width // 2, height // 2, width * 3 // 4, height * 4 // 5], fill=(30, 180, 210))
    return image


def mask_pair(size: tuple[int, int], text: str = TEXT,
              spec: FontSpec | None = None) -> tuple[Image.Image, Image.Image]:
    """返回 (build_mask 的结果, 摆正后的文字层)。

    build_mask 会整体旋转 180°（原程序如此），提取结果可能呈正或反，
    因此两种方向都要能判定。
    """
    stored = textmask.build_mask(text, size, spec)
    upright = stored.rotate(180)
    return stored, upright


def _regions(mask: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    gray = np.asarray(mask.convert("L"), dtype=np.uint8)
    foreground = gray > 120
    if foreground.sum() < 20:
        raise AssertionError("水印文字掩膜近乎为空，请确认可用中文字体已安装")
    return foreground, ~foreground


def psnr(reference: np.ndarray, test: np.ndarray) -> float:
    mse = float(np.mean((reference.astype(np.float64) - test.astype(np.float64)) ** 2))
    if mse == 0:
        return float("inf")
    return float(10.0 * np.log10(255.0 ** 2 / mse))


def gray_of(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L"))


# ------------------------------------------------------------------- 数学层
def test_power_of_two_modes() -> None:
    assert schemes.power_of_two(1000, schemes.ROUND) == 1024
    assert schemes.power_of_two(700, schemes.ROUND) == 512
    assert schemes.power_of_two(700, schemes.CEIL) == 1024
    assert schemes.power_of_two(700, schemes.FLOOR) == 512
    assert schemes.power_of_two(512, schemes.ROUND) == 512
    for value in (320, 640, 1024):
        assert fft2d.is_power_of_two(schemes.power_of_two(value))


def test_fft_is_unitary_round_trip() -> None:
    plane = (np.random.default_rng(1).random((64, 32)) * 255).astype(np.float32) / 256.0
    restored = fft2d.backward(fft2d.forward(plane))
    assert np.allclose(restored.real, plane, atol=1e-4)
    assert np.max(np.abs(restored.imag)) < 1e-4
    manual = np.fft.fft2(plane) / np.sqrt(plane.size)
    assert np.allclose(fft2d.forward(plane), manual, atol=1e-5)
    assert fft2d.to_uint8(np.array([[-0.6], [300.0], [255.9]])).tolist() == [[0], [255], [255]]


# ------------------------------------------------------------------- 算法层
def test_embed_is_invisible_at_default_strength() -> None:
    size = (512, 256)
    data = images.to_array(make_photo(*size))
    mask = images.to_array(textmask.build_mask(TEXT, size))
    out = watermark.embed(data, mask, pipeline.strength_of(SPIN_DEFAULT))
    value = psnr(data, out)
    assert value > 30.0, f"默认强度下 PSNR 过低：{value:.1f} dB"
    assert int(np.abs(out.astype(int) - data.astype(int)).max()) < 90


def test_embed_requires_power_of_two_canvas() -> None:
    data = np.zeros((100, 120, 3), dtype=np.uint8)
    try:
        watermark.embed(data, data, 0.1)
    except ValueError as exc:
        assert "2 的整数次幂" in str(exc)
    else:
        raise AssertionError("非 2 的幂画布应报错")


def test_embed_rejects_size_mismatch() -> None:
    data = np.zeros((64, 64, 3), dtype=np.uint8)
    try:
        watermark.embed(data, np.zeros((32, 32, 3), dtype=np.uint8), 0.1)
    except ValueError as exc:
        assert "水印图尺寸" in str(exc)
    else:
        raise AssertionError("尺寸不一致应报错")


def _central_crop(array: np.ndarray, fraction: float = 0.6) -> np.ndarray:
    """裁剪中央区域：频谱四角是图像自身的低频大能量，必须排除后再判定可读性。"""
    height, width = array.shape[:2]
    margin_y = int(height * (1 - fraction) / 2)
    margin_x = int(width * (1 - fraction) / 2)
    return array[margin_y:height - margin_y, margin_x:width - margin_x]


def _auc(foreground: np.ndarray, background: np.ndarray, samples: int = 3000) -> float:
    """判别力指标：随机取一个文字像素，其提取亮度高于随机背景像素的概率。

    水印文字只占画面的百分之一，直接用整体相关系数会被面积比例稀释，
    AUC 才是“人眼能不能读出文字”的合理度量。
    """
    left = foreground.astype(np.float64).ravel()
    right = background.astype(np.float64).ravel()
    if left.size == 0 or right.size == 0:
        raise AssertionError("前景或背景区域为空")
    rng = np.random.default_rng(7)
    if right.size > samples:
        right = right[rng.choice(right.size, samples, replace=False)]
    return float(np.mean(left[:, None] > right[None, :])) + 0.5 * float(
        np.mean(left[:, None] == right[None, :]))


def test_round_trip_recovers_text() -> None:
    """嵌入 -> 提取：文字区域应明显亮于背景，且能被判别出来（水印可读）。"""
    size = (512, 256)
    data = images.to_array(make_photo(*size))
    stored, upright = mask_pair(size)
    out = watermark.embed(data, images.to_array(stored), pipeline.strength_of(400))
    ext = watermark.extract(out, pipeline.gain_of(SPIN_DEFAULT))

    crop_ext = _central_crop(ext[..., 0]).astype(np.float64)
    best_mask = None
    best_auc = -1.0
    for candidate in (upright, stored):
        crop_mask = _central_crop(gray_of(candidate))
        foreground = crop_mask > 120
        auc = _auc(crop_ext[foreground], crop_ext[~foreground])
        if auc > best_auc:
            best_auc, best_mask, best_foreground = auc, crop_ext, foreground
    text_mean = float(best_mask[best_foreground].mean())
    back_mean = float(best_mask[~best_foreground].mean())
    assert text_mean > back_mean + 20, f"文字与背景对比不足：{text_mean:.1f} vs {back_mean:.1f}"
    assert best_auc > 0.9, f"提取结果判别力不足：AUC={best_auc:.3f}"


def test_extract_of_plain_image_has_no_text_signal() -> None:
    """对照组：未加水印的图，提取结果里文字位置不应比周围更亮。"""
    size = (512, 256)
    _stored, upright = mask_pair(size)
    ext = watermark.extract(images.to_array(make_photo(*size)), pipeline.gain_of(SPIN_DEFAULT))
    crop_ext = _central_crop(ext[..., 0]).astype(np.float64)
    crop_mask = _central_crop(gray_of(upright))
    foreground = crop_mask > 120
    auc = _auc(crop_ext[foreground], crop_ext[~foreground])
    assert auc < 0.62, f"未加水印却已能判别出文字：AUC={auc:.3f}"


def test_strength_and_gain_mapping() -> None:
    assert pipeline.strength_of(50) == 0.1
    assert pipeline.strength_of(1000) == 2.0
    assert pipeline.gain_of(50) == 10.0
    assert pipeline.gain_of(1000) == 200.0


def test_progress_callback_matches_original_schedule() -> None:
    seen: list[int] = []
    size = (256, 256)
    data = images.to_array(make_photo(*size))
    mask = images.to_array(textmask.build_mask("测试", size))
    watermark.embed(data, mask, 0.1, progress=seen.append)
    assert seen == [0, 10, 20, 30, 40, 50, 60, 70, 80, 90], seen

    events: list[tuple[int, str]] = []
    pipeline.extract_watermark(make_photo(600, 300), scheme=0,
                               progress=lambda percent, message: events.append((percent, message)))
    assert [percent for percent, _ in events] == [0, 10, 30, 50, 70, 90], events
    assert all(message.startswith("正在提取") for _, message in events)


# ------------------------------------------------------------------- 方案层
def test_scheme_sizes() -> None:
    im = make_photo(620, 420)
    rounded = (schemes.power_of_two(620), schemes.power_of_two(420))
    for index, info in enumerate(SCHEMES):
        canvas = schemes.prepare_embed(im, index)
        assert fft2d.is_power_of_two(canvas.image.width), info.name
        assert fft2d.is_power_of_two(canvas.image.height), info.name
        result = canvas.restore(canvas.image)
        if index == 0:
            assert result.size == rounded, f"{info.name} 输出应为 2 的幂尺寸"
        else:
            assert result.size == im.size, f"{info.name} 应保持原尺寸"
        extract = schemes.prepare_extract(im, index)
        assert extract.restore(extract.image).size == im.size, f"{info.name} 提取应回原尺寸"
    assert schemes.prepare_embed(im, 3).image.size == (1024, 512), "方案四用 ceil 补白"
    assert schemes.prepare_embed(im, 4).image.size == (512, 256), "方案五用 floor 取块"


def test_scheme_five_only_touches_region() -> None:
    im = make_photo(620, 420)
    canvas = schemes.prepare_embed(im, 4)
    processed = canvas.image.point(lambda value: 0 if value > 128 else 255)
    out = canvas.restore(processed)
    floor_width, floor_height = canvas.image.size
    original = np.asarray(im)
    result = np.asarray(out)
    assert result.shape == original.shape
    assert (result[floor_height:, floor_width:] == original[floor_height:, floor_width:]).all()
    assert not (result[:floor_height, :floor_width] == original[:floor_height, :floor_width]).all()


def test_scheme_four_pads_white() -> None:
    im = make_photo(300, 300)
    canvas = schemes.prepare_embed(im, 3)
    data = np.asarray(canvas.image)
    assert canvas.image.size == (512, 512)
    assert (data[400, 400] == (255, 255, 255)).all(), "补白区域应为白色"
    assert (data[10, 10] == np.asarray(im)[10, 10]).all(), "左上应为原图内容"
    assert canvas.restore(canvas.image).size == im.size


# ------------------------------------------------------------------- 业务层
def test_textmask_is_black_background_white_text() -> None:
    stored, upright = mask_pair((256, 128), text="水印")
    assert np.asarray(stored).shape == (128, 256, 3)
    foreground, background = _regions(upright)
    assert float(np.asarray(upright)[foreground].mean()) > 150
    assert float(np.asarray(stored)[_regions(stored)[1]].mean()) < 30


def test_config_round_trip_and_legacy_format() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "WaterMarkH.xml"
        cfg = config_mod.Config(path)
        assert cfg.out_format == formats.JPEG, "无配置文件时默认 JPEG"
        cfg.out_format = formats.BMP
        cfg.save()
        text = path.read_text(encoding="utf-8")
        assert "<Setting>" in text and "<OutFormat>2</OutFormat>" in text
        assert config_mod.Config(path).out_format == formats.BMP

        path.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<Setting><General>'
            "<OutFormat>1</OutFormat></General></Setting>", encoding="utf-8")
        assert config_mod.Config(path).format.name == "PNG"


def test_formats_paths_and_saving() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "out"
        source = Path(tmp) / "photo.png"
        make_photo(80, 60).save(source)
        for index, expected in ((formats.JPEG, "photo_WaterMark.jpg"),
                                (formats.PNG, "photo_WaterMark.png"),
                                (formats.BMP, "photo_WaterMark.bmp")):
            target = formats.output_path(source, out_dir, index)
            assert target.name == expected
            formats.save(make_photo(80, 60), target, index)
            assert target.is_file()
            with Image.open(target) as opened:
                assert opened.size == (80, 60)


def test_pipeline_add_then_extract() -> None:
    """端到端：添加水印 -> 落盘 -> 用同方案提取，验证文件与预览都可用。"""
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        source = folder / "photo.png"
        make_photo(640, 300).save(source)
        events: list[tuple[int, str]] = []
        result = pipeline.add_watermark(source, folder, TEXT, scheme=1, strength_value=500,
                                        preview=True, brightness_value=60,
                                        out_format=formats.JPEG,
                                        progress=lambda percent, message: events.append((percent, message)))
        assert result.saved_path.is_file()
        assert result.saved_path.name == "photo_WaterMark.jpg"
        assert result.result_image.size == (640, 300)
        assert result.preview_image is not None and result.preview_image.size == (640, 300)
        assert events[-1] == (0, "添加成功")
        assert any(message.startswith("正在添加") for _, message in events)
        assert any(message.startswith("生成预览") for _, message in events)

        again = pipeline.extract_watermark(result.saved_path, scheme=1, brightness_value=60)
        assert again.size == (640, 300)
        # 提取出的幅度谱应当有明显结构（不是纯黑或纯噪声平面）
        ext = images.to_array(again)[..., 0].astype(np.float32)
        assert float(ext.std()) > 5.0, f"提取结果过于平坦：std={ext.std():.2f}"
