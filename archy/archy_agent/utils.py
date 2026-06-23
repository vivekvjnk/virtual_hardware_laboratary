import os
import sys
import logging
from typing import Union, Optional
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps, ImageDraw
from vhl_common.workspace_manager.manager import WorkspaceManager

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("archy_orchestrator")

def _convert_to_grayscale_n_increase_contrast(image_path: Path, output_path: Path, contrast_factor: float = 1.3):
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

def prepare_archy_workspace(workspace_manager: WorkspaceManager) -> bool:
    """
    Handles all deterministic workspace and artifact preparation steps.
    Consolidates path resolution, image preprocessing, and segmentation.
    Steps:
    1. Identify all modules in the project using the workspace manager's manifest.
    2. Start iterating through modules. For each module:
        a. Check if {module_name}/resources/schematic_images/ directory contains any images.
        b. If yes, convert each image to grayscale and increase contrast, then save in place of original image.
        c. For each preprocessed image, check if segments already exist in {module_name}/resources/schematic_images/{image_name}_segments/. If not, segment the image into 4 overlapping crops(using crop_image_into_segments) and save them in that directory.
    3. Return if all steps completed successfully, or raise error if any step fails.
    """
    
    logger.info(f"[prepare_archy_workspace] Preparing workspace")
    
    # Step 1: Identify all modules from the authoritative manifest
    modules = workspace_manager.module_paths
    
    if not modules:
        logger.warning(f"No modules found in project '{workspace_manager.project_name}'.")
        return False

    # Step 2: Iterate through modules
    for module_name,module_path in modules.items():
        logger.info(f"Processing module: {module_name}")
        
        images_dir = workspace_manager.get_module_workspace(module_name) / "resources" / "schematic_images"
        if not images_dir.exists() or not images_dir.is_dir():
            logger.info(f"No schematic_images directory found for module {module_name}, skipping.")
            continue
            
        # Supported image extensions
        extensions = (".png", ".jpg", ".jpeg")
        
        for image_file in images_dir.iterdir():
            if image_file.suffix.lower() in extensions:
                # Skip if it's a directory (unlikely but possible with weird naming)
                if image_file.is_dir():
                    continue
                
                # a & b. Convert to grayscale and increase contrast, save in place
                # Note: This follows docstring instructions.
                logger.info(f"Preprocessing image: {image_file}")
                _convert_to_grayscale_n_increase_contrast(image_file, image_file)
                
                # c. Segment the image if segments don't already exist
                segments_dir = images_dir / f"{image_file.stem}_segments"
                if not segments_dir.exists() or not any(segments_dir.iterdir()):
                    logger.info(f"Generating segments for {image_file.name} in {segments_dir}")
                    crop_image_into_segments(
                        image_path=image_file,
                        output_dir=segments_dir,
                        num_segments=4,
                        overlap_pct=0.1
                    )
                else:
                    logger.info(f"Segments already exist for {image_file.name} in {segments_dir}")
                    
    return True



