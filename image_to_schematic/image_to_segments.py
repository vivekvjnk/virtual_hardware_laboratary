# Objective of this module is to segment given schematic image into different components
# Uses SAMv3 segmentation model to identify modular sub circuits within the schematic image

from typing import List, Dict, Any, Union
from pathlib import Path

from PIL import Image
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor


def load_sam3_processor(confidence_threshold: float = 0.3) -> Sam3Processor:
    """
    Load SAMv3 image model and wrap it in a Sam3Processor.
    Keep this separate so you can reuse the same processor across calls.
    """
    print("Loading SAMv3 Image Model...")
    model = build_sam3_image_model()
    print("Model loaded.")
    processor = Sam3Processor(model, confidence_threshold=confidence_threshold)
    return processor


def segment_schematic_image(
    image: Union[str, Path, Image.Image],
    prompt_keywords: List[str],
    processor: Sam3Processor,
) -> Dict[str, Any]:
    """
    Segment a schematic image into sub-images using SAMv3.

    Parameters
    ----------
    image : str | Path | PIL.Image.Image
        Source image (file path or already-loaded PIL image).
    prompt_keywords : List[str]
        List of text prompts/keywords, e.g. ["circuit", "schematic"].
        These will be joined into a single comma-separated prompt.
    processor : Sam3Processor
        An initialized Sam3Processor instance (from load_sam3_processor).

    Returns
    -------
    Dict[str, Any]
        {
          "original_image": PIL.Image.Image,   # original RGB image
          "prompt": str,                       # combined text prompt
          "detections": [
              {
                  "crop": PIL.Image.Image,    # cropped sub-image (no rescaling)
                  "mask": torch.Tensor,       # mask tensor for this region
                  "box": (int, int, int, int),# (x0, y0, x1, y1)
                  "score": float              # confidence score
              },
              ...
          ]
        }
    """
    # ----- Load / normalize image -----
    if isinstance(image, (str, Path)):
        image = Image.open(image).convert("RGB")
    elif isinstance(image, Image.Image):
        image = image.convert("RGB")
    else:
        raise TypeError("image must be a file path or a PIL.Image.Image instance")

    width, height = image.size

    # ----- Build text prompt from keywords -----
    if not prompt_keywords:
        raise ValueError("prompt_keywords must be a non-empty list of strings")
    prompt_text = ", ".join(prompt_keywords)

    # ----- Run SAMv3 inference -----
    print("Setting image...")
    inference_state = processor.set_image(image)
    print("Image set.")

    print(f"Prompting model with text: {prompt_text!r} ...")
    output = processor.set_text_prompt(state=inference_state, prompt=prompt_text)
    print("Finished processing.")

    masks = output["masks"]   # Tensor or list-like
    boxes = output["boxes"]   # Tensor of shape [N, 4]
    scores = output["scores"] # Tensor of shape [N]

    print(f"Detected {len(masks)} masks")

    detections = []

    for i, (mask, box, score) in enumerate(zip(masks, boxes, scores)):
        # box is typically [x0, y0, x1, y1] as floats
        x0, y0, x1, y1 = box.tolist()

        # Clip box coords to image bounds to be safe
        x0 = max(0, min(int(x0), width - 1))
        y0 = max(0, min(int(y0), height - 1))
        x1 = max(0, min(int(x1), width))
        y1 = max(0, min(int(y1), height))

        # Skip degenerate boxes
        if x1 <= x0 or y1 <= y0:
            print(f"Skipping degenerate box for mask {i}: {(x0, y0, x1, y1)}")
            continue

        print(f"Mask {i}: Score {float(score):.4f}, Box {(x0, y0, x1, y1)}")

        # ----- Crop directly from original image (no resizing) -----
        crop = image.crop((x0, y0, x1, y1))

        detections.append(
            {
                "crop": crop,
                "mask": mask,  # keep original tensor; .cpu() as needed by caller
                "box": (x0, y0, x1, y1),
                "score": float(score),
            }
        )

    return {
        "original_image": image,
        "prompt": prompt_text,
        "detections": detections,
    }


# ---------------- Visualization Utility ----------------
import matplotlib.pyplot as plt

def visualize_masks_on_image(image: Image.Image, masks) -> None:
    """
    Quick visualization of masks overlaid on the image.
    `masks` is expected to be an iterable of torch.Tensors or numpy arrays.
    """
    import numpy as np

    def _show_mask(mask, ax, random_color=False):
        if random_color:
            color = np.concatenate([np.random.random(3), np.array([0.6])], axis=0)
        else:
            color = np.array([30/255, 144/255, 255/255, 0.6])
        h, w = mask.shape[-2:]
        mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
        ax.imshow(mask_image)

    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.imshow(image)

    for mask in masks:
        if hasattr(mask, "cpu"):
            mask_np = mask.cpu().numpy()
        else:
            mask_np = np.asarray(mask)
        _show_mask(mask_np, ax, random_color=True)

    plt.axis("off")
    plt.show()


from pathlib import Path
from typing import Union, List, Dict, Any

from PIL import Image, ImageDraw

# Assuming these are defined as in the previous reply
# from sam3.model_builder import build_sam3_image_model
# from sam3.model.sam3_image_processor import Sam3Processor
# from your_module import load_sam3_processor, segment_schematic_image


def run_schematic_segmentation_pipeline(
    image_path: Union[str, Path],
    output_subdir_name: str = "schematic_subcircuits",
    prompt_keywords: List[str] = None,
    confidence_threshold: float = 0.25,
) -> Dict[str, Any]:
    """
    Orchestrate the full SAMv3 segmentation pipeline on a high-resolution schematic.

    Parameters
    ----------
    image_path : str | Path
        Path to the high-resolution schematic image.
    output_subdir_name : str, optional
        Name of the output directory (created under the directory where this Python file resides).
    prompt_keywords : List[str], optional
        List of prompt keywords to guide segmentation.
        Defaults to ["circuit", "schematic"] if not provided.
    confidence_threshold : float, optional
        Confidence threshold for SAMv3 detections.

    Returns
    -------
    Dict[str, Any]
        {
          "output_dir": Path,
          "annotated_image_path": Path,
          "subcircuit_paths": List[Path],
          "num_detections": int,
        }
    """
    image_path = Path(image_path)
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if prompt_keywords is None:
        prompt_keywords = ["circuit", "schematic"]

    # Base directory: where this Python script resides
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / output_subdir_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load processor
    processor = load_sam3_processor(confidence_threshold=confidence_threshold)

    # Run core segmentation utility
    result = segment_schematic_image(
        image=image_path,
        prompt_keywords=prompt_keywords,
        processor=processor,
    )

    original_image: Image.Image = result["original_image"]
    detections = result["detections"]

    # 1) Save cropped sub-circuit images (no resizing ⇒ no resolution loss)
    subcircuit_paths: List[Path] = []
    stem = image_path.stem

    for idx, det in enumerate(detections):
        crop: Image.Image = det["crop"]
        score: float = det["score"]

        # Encode score into filename for debugging/inspection
        score_int = int(score * 100)
        crop_filename = f"{stem}_subckt_{idx:03d}_s{score_int:02d}.png"
        crop_path = output_dir / crop_filename
        crop.save(crop_path)
        subcircuit_paths.append(crop_path)

    # 2) Create original image with bounding boxes drawn (no rescaling)
    annotated_image = original_image.copy()
    draw = ImageDraw.Draw(annotated_image)

    for idx, det in enumerate(detections):
        x0, y0, x1, y1 = det["box"]
        score = det["score"]

        # Draw rectangle (you can tweak width/color as you like)
        draw.rectangle((x0, y0, x1, y1), outline="red", width=3)

        # Optional: label each box with index and score
        label = f"{idx}:{score:.2f}"
        # A simple text offset to avoid drawing exactly on the border
        text_pos = (x0 + 3, y0 + 3)
        draw.text(text_pos, label, fill="red")

    annotated_filename = f"{stem}_with_boxes.png"
    annotated_image_path = output_dir / annotated_filename
    annotated_image.save(annotated_image_path)

    return {
        "output_dir": output_dir,
        "annotated_image_path": annotated_image_path,
        "subcircuit_paths": subcircuit_paths,
        "num_detections": len(detections),
    }


if __name__ == "__main__":
    result = run_schematic_segmentation_pipeline("bq79616.png",confidence_threshold=0.25)

    print("Output directory:", result["output_dir"])
    print("Annotated image:", result["annotated_image_path"])
    print("Num subcircuits:", result["num_detections"])
    for p in result["subcircuit_paths"]:
        print("  -", p)
