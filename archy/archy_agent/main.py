import os
import sys
import logging
from typing import Union, Optional
from pathlib import Path
from PIL import Image, ImageEnhance, ImageOps, ImageDraw
from workspace.manager import WorkspaceManager

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
        
        images_dir = module_path / "resources" / "schematic_images"
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

def _archy_build_scud_stub(image_id: str, workspace_manager: WorkspaceManager):
    """Stub implementation of archy_build_scud for faster validation."""
    scud_file = workspace_manager.project_root / f"{image_id}.scud"
    
    # Check if scud file already exists
    if scud_file.exists():
        logger.info(f"[_archy_build_scud_stub] SCUD file already exists at {scud_file}. Skipping stub generation.")
        return scud_file

    logger.info(f"[_archy_build_scud_stub] [STUB] Generating dummy SCUD document for image_id: {image_id}")
    
    # Define mock SCUD path relative to the script's root (VHL_agent_backend)
    # The script is in VHL_agent_backend/archy/archy_agent/main.py
    base_dir = Path(__file__).resolve().parents[2] # VHL_agent_backend
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

def orchestrate_archy(
    workspace_path: Path, 
    module_name: str, 
    image_path: Path,
    image_segments_path: Path,
    system_boundary_path: Optional[Path] = None,
    module_boundary_path: Optional[Path] = None,
    datasheet_path: Optional[Path] = None,
    eval_design_path: Optional[Path] = None,
):
    """
    Main orchestration function for the Archy module.
    
    Purpose: Generate a Shared Circuit Understanding Document (SCUD) from a schematic image 
    and supporting technical documentation.
    """
    
    # Step 1: Trigger Archy Agent (Scud Generation)
    logger.info("[orchestrate_archy] Triggering Archy agent for SCUD generation...")
    if os.environ.get("ARCHY_STUB") == "true":
        _archy_build_scud_stub(image_id=module_name, workspace_manager=workspace_path)
    else:
        from archy_agent.scud_gen_agent import archy_build_scud 
        archy_build_scud(
            module_name=module_name,
            workspace=workspace_path,
            image_path=image_path,
            image_segment_paths=image_segments_path,
            system_boundary_path=system_boundary_path,
            module_boundary_path=module_boundary_path,
            datasheet_path=datasheet_path,
            eval_design_path=eval_design_path,
        )
    
    # Final Verification: Check if scud document is created in workspace
    scud_file = workspace_path / f"{module_name}.scud"
    if not scud_file.exists():
        raise RuntimeError(f"Final verification failed: SCUD document not found at {scud_file}")
        # TODO If this happens, ask agent to rename the generate SCUD file to match the expected naming convention
    
    logger.info(f"[orchestrate_archy] Workflow completed successfully. SCUD document generated: {scud_file}")
    return scud_file

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python main.py <workspace_path> <module_name>")
        sys.exit(1)
        
    ws_v_path = Path(sys.argv[1]).resolve()
    module_name = sys.argv[2]
    
    try:
        # Local preparation for standalone run
        docs_dir = ws_v_path / "docs"
        # source_image_path = "schematic_images" / f"{module_name}.png"
        image_segments_path = ws_v_path / "schematic_images"
        processed_image_path = image_segments_path / f"{module_name}_preprocessed.png"

        
        # if not processed_image_path.exists():
        #     _preprocess_image(source_image_path, processed_image_path)
        
        # if not image_segments_path.exists() or not any(image_segments_path.iterdir()):
        crop_image_into_segments(processed_image_path, image_segments_path)

        # Auto-locate other required documents
        sys_boundary = next(docs_dir.glob("system-boundary.md"), None)
        mod_boundary = next(docs_dir.glob(f"*{module_name}*boundary*.md"), None)
             
        datasheet = next(docs_dir.glob("*datasheet*.md"), None)
            
        eval_design = next(docs_dir.glob("*eval*board*.md"), None)

        logger.info(f"Located System Boundary: {sys_boundary}")
        logger.info(f"Located Module Boundary: {mod_boundary}")
        logger.info(f"Located Datasheet: {datasheet}")
        logger.info(f"Located Eval Design: {eval_design}")

        orchestrate_archy(
            workspace_path=ws_v_path,
            module_name=module_name,
            image_path=processed_image_path,
            image_segments_path=image_segments_path,
            system_boundary_path=sys_boundary,
            module_boundary_path=mod_boundary,
            datasheet_path=datasheet,
            eval_design_path=eval_design
        )
    except Exception as e:
        logger.error(f"[main] Orchestration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
