import os
import sys
import logging
from pathlib import Path
from typing import Union
from PIL import Image, ImageEnhance, ImageOps, ImageDraw

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("archy_orchestrator")

def _preprocess_image(image_path: Path, output_path: Path, contrast_factor: float = 1.3):
    """Preprocess image by converting to grayscale and increasing contrast."""
    logger.info(f"Preprocessing image: {image_path} -> {output_path}")
    try:
        with Image.open(image_path) as img:
            # Convert to Grayscale
            grayscale_img = ImageOps.grayscale(img)
            # Increase Contrast
            enhancer = ImageEnhance.Contrast(grayscale_img)
            processed_img = enhancer.enhance(contrast_factor)
            # Save results
            processed_img.save(output_path)
            logger.info("Image preprocessing completed successfully.")
    except Exception as e:
        logger.error(f"Error during image preprocessing: {e}")
        raise

def crop_image_into_segments(image_path: Path, output_dir: Path, num_segments: int = 4, overlap_pct: float = 0.1):
    """
    Segments the image into a grid of specified segments with overlap.
    
    Args:
        image_path: Path to the source image.
        output_dir: Directory where the segments will be saved.
        num_segments: Number of segments to create (should be an even number).
        overlap_pct: The percentage of overlap between adjacent segments (0.0 to 1.0).
    """
    if num_segments % 2 != 0:
        logger.warning(f"num_segments={num_segments} is not even. Proceeding anyway.")

    logger.info(f"Segmenting image {image_path} into {num_segments} segments with {overlap_pct*100}% overlap.")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with Image.open(image_path) as img:
        width, height = img.size
        
        # Create a copy of the image to draw bounding boxes on for overview
        # We convert to RGB to ensure we can draw colored bounding boxes
        overview_img = img.copy().convert("RGB")
        draw = ImageDraw.Draw(overview_img)

        # Determine grid dimensions
        if num_segments <= 2:
            rows, cols = 1, num_segments
        elif num_segments == 4:
            rows, cols = 2, 2
        else:
            # For other even numbers, try to keep a reasonable aspect ratio
            rows = 2
            cols = (num_segments + 1) // 2
            
        seg_w = width / cols
        seg_h = height / rows
        
        overlap_w = seg_w * overlap_pct
        overlap_h = seg_h * overlap_pct
        
        segment_idx = 0
        for r in range(rows):
            for c in range(cols):
                if segment_idx >= num_segments:
                    break
                    
                # Calculate coordinates with overlap
                left = max(0, c * seg_w - overlap_w / 2)
                top = max(0, r * seg_h - overlap_h / 2)
                right = min(width, (c + 1) * seg_w + overlap_w / 2)
                bottom = min(height, (r + 1) * seg_h + overlap_h / 2)
                
                # Ensure we cover the full range at extremes to avoid gaps due to rounding
                if c == 0: left = 0
                if c == cols - 1: right = width
                if r == 0: top = 0
                if r == rows - 1: bottom = height
                
                crop_box = (int(left), int(top), int(right), int(bottom))
                segment = img.crop(crop_box)
                
                segment_name = f"segment_{segment_idx}.png"
                segment_path = output_dir / segment_name
                segment.save(segment_path)
                logger.info(f"Saved segment {segment_idx} to {segment_path}")

                # Draw bounding box and label on overview image
                draw.rectangle(crop_box, outline="red", width=1)
                # Label the segment on the overview image
                draw.text((left + 10, top + 10), f"Segment {segment_idx}", fill="red")
                
                segment_idx += 1
        
        # Save the overview image
        overview_filename = f"segments_overview_with_bboxes.png"
        overview_path = output_dir / overview_filename
        overview_img.save(overview_path)
        logger.info(f"Saved segments overview image to {overview_path}")
                
    logger.info(f"Successfully created {num_segments} segments and overview in {output_dir}")

def prepare_archy_workspace(workspace_path: Union[str, Path], image_id: str) -> Path:
    """
    Handles all deterministic workspace and artifact preparation steps.
    Consolidates path resolution, image preprocessing, and segmentation.
    Returns the path to the preprocessed image.
    """
    workspace = Path(workspace_path).resolve()
    source_image_path = workspace / "UserArtefacts" / f"{image_id}.png"
    processed_image_path = workspace / "UserArtefacts" / f"{image_id}_preprocessed.png"
    output_dir = workspace / "schematic_images" / image_id

    logger.info(f"[prepare_archy_workspace] Preparing workspace for image_id: {image_id}")
    
    if not source_image_path.exists():
        raise FileNotFoundError(f"Source image not found at {source_image_path}")

    # Step 1: Image Preprocessing (Idempotent)
    if not processed_image_path.exists():
        logger.info(f"[prepare_archy_workspace] Preprocessed image not found. Generating...")
        _preprocess_image(source_image_path, processed_image_path)
    else:
        logger.info(f"[prepare_archy_workspace] Preprocessed image already exists at {processed_image_path}")

    # Step 2: Image Segmentation (Idempotent)
    # Check if segments already exist by checking if output_dir has files
    if not output_dir.exists() or not any(output_dir.iterdir()):
        logger.info(f"[prepare_archy_workspace] Segments not found. Segmenting image...")
        crop_image_into_segments(
            image_path=processed_image_path,
            output_dir=output_dir,
            num_segments=4,
            overlap_pct=0.1
        )
    else:
        logger.info(f"[prepare_archy_workspace] Segments already exist in {output_dir}")

    return processed_image_path

def _archy_build_scud_stub(image_id: str, workspace_path: Path):
    """Stub implementation of archy_build_scud for faster validation."""
    workspace = Path(workspace_path).resolve()
    scud_file = workspace / f"{image_id}.scud"
    
    # Check if scud file already exists
    if scud_file.exists():
        logger.info(f"[_archy_build_scud_stub] SCUD file already exists at {scud_file}. Skipping stub generation.")
        return scud_file

    logger.info(f"[_archy_build_scud_stub] [STUB] Generating dummy SCUD document for image_id: {image_id}")
    
    # Define mock SCUD path relative to the script's root (VHL_agent_backend)
    # The script is in VHL_agent_backend/archy/archy_agent/main.py
    # Mock is in VHL_agent_backend/tests/Mocks/Archy/...
    base_dir = Path(__file__).resolve().parents[3] # VHL_agent_backend
    mock_scud_path = base_dir / "tests" / "Mocks" / "Archy" / "bms_bq_sys_c195dff2_eval_board_0b36a.scud"
    
    if not mock_scud_path.exists():
        # Fallback to local tests path if running from backend root
        mock_scud_path = Path("tests/Mocks/Archy/bms_bq_sys_c195dff2_eval_board_0b36a.scud")

    try:
        with open(mock_scud_path, "r") as f:
            scud_content = f.read()
    except Exception as e:
        logger.warning(f"[_archy_build_scud_stub] Could not find mock SCUD at {mock_scud_path}: {e}. Using fallback content.")
        scud_content = f"DUMMY SCUD FOR {image_id}"
    
    with open(scud_file, "w") as f:
        f.write(scud_content)

    logger.info(f"[_archy_build_scud_stub] [STUB] Dummy SCUD document generated: {scud_file}")
    return scud_file

def orchestrate_archy(workspace_path: Union[str, Path], image_id: str, image_path: Path):
    """
    Main orchestration function for the Archy module.
    
    Purpose: Generate a Shared Circuit Understanding Document (SCUD) from a schematic image.
    
    Sole Responsibility: Triggering LLM agent in fail-safe mode with proper error handling.
    Deterministic workspace preparation should be handled by the caller.
    """
    workspace = Path(workspace_path).resolve()
    
    # Step 1: Trigger Archy Agent (Scud Generation)
    logger.info("[orchestrate_archy] Triggering Archy agent for SCUD generation...")
    if os.environ.get("ARCHY_STUB") == "true":
        _archy_build_scud_stub(image_id=image_id, workspace_path=workspace)
    else:
        from archy_agent.scud_gen_agent import archy_build_scud 
        archy_build_scud(
            image_id=image_id,
            workspace=workspace,
            image_path=image_path
        )
    
    # Final Verification: Check if scud document is created in workspace
    scud_file = workspace / f"{image_id}.scud"
    if not scud_file.exists():
        raise RuntimeError(f"Final verification failed: SCUD document not found at {scud_file}")
    
    logger.info(f"[orchestrate_archy] Workflow completed successfully. SCUD document generated: {scud_file}")
    return scud_file

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <workspace_path> <image_id>")
        sys.exit(1)
        
    ws_v_path = Path(sys.argv[1]).resolve()
    img_v_id = sys.argv[2]
    
    try:
        # Local preparation for standalone run
        source_image_path = ws_v_path / "UserArtefacts" / f"{img_v_id}.png"
        processed_image_path = ws_v_path / "UserArtefacts" / f"{img_v_id}_preprocessed.png"
        output_dir = ws_v_path / "schematic_images" / img_v_id

        if not source_image_path.exists():
            logger.error(f"Source image not found at {source_image_path}")
            sys.exit(1)

        if not processed_image_path.exists():
            _preprocess_image(source_image_path, processed_image_path)
        
        if not output_dir.exists() or not any(output_dir.iterdir()):
            crop_image_into_segments(processed_image_path, output_dir)

        orchestrate_archy(ws_v_path, img_v_id, processed_image_path)
    except Exception as e:
        logger.error(f"[main] Orchestration failed: {e}")
        sys.exit(1)
