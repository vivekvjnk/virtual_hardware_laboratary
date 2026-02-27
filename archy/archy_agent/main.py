import os
import sys
import logging
from pathlib import Path
from typing import Union
from PIL import Image, ImageEnhance, ImageOps
from archy_agent.image_to_schematic.image_to_segments import run_schematic_segmentation_pipeline

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

def _archy_build_scud_stub(image_id: str, workspace_path: Path, image_path: Path = None):
    """Stub implementation of archy_build_scud for faster validation."""

    workspace = Path(workspace_path).resolve()    
    source_image_path = workspace / "UserArtefacts" / f"{image_id}.png"
    processed_image_path = workspace / "UserArtefacts" / f"{image_id}_preprocessed.png"

    if not image_path:
        if not source_image_path.exists():
            raise FileNotFoundError(f"Source image not found at {source_image_path}")
        _preprocess_image(source_image_path, processed_image_path)
        image_path = processed_image_path
    
    # Step 1: Segmentation (uses processed image)
    # Source image is assumed to be at <workspace>/UserArtefacts/<image_id>.png
    # But we now use the preprocessed image
    image_path = processed_image_path
    
    # Predefined output directory for segments
    # Consistent with standard naming and scud_gen_agent's expected structure
    output_dir = workspace / "schematic_images" / image_id
    
    logger.info(f"[_archy_build_scud_stub] Starting orchestration for image_id: {image_id}")
    logger.info(f"[_archy_build_scud_stub] Workspace: {workspace}")
    logger.info(f"[_archy_build_scud_stub] Source Image Path: {image_path}")
    
    if not image_path.exists():
        raise FileNotFoundError(f"Source image not found at {image_path}")

    # Step 1: Run Segmentation Pipeline
    logger.info("[_archy_build_scud_stub] Running image segmentation pipeline...")
    try:
        segmentation_result = run_schematic_segmentation_pipeline(
            output_dir=output_dir,
            image_path=image_path
        )
        logger.info(f"[_archy_build_scud_stub] Segmentation pipeline finished. Detections: {segmentation_result.get('num_detections', 0)}")
    except Exception as e:
        logger.error(f"[_archy_build_scud_stub] Error during image segmentation: {e}")
        raise

    # Validation: Verify segments were created
    if not output_dir.exists() or not any(output_dir.glob("*.png")):
        raise RuntimeError(f"Validation failed: No cropped images found in segment directory {output_dir}")
    
    logger.info(f"[_archy_build_scud_stub] Validation success: Segments found in {output_dir}")

    
    
    # Step 2
    logger.info(f"[_archy_build_scud_stub] [STUB] Generating dummy SCUD document for image_id: {image_id}")
    
    # Create dummy SCUD file
    scud_file = workspace / f"{image_id}.scud"
    # Load mock SCUD content from VHL_agent_backend/tests/Mocks/Archy/bms_bq_sys_c195dff2_eval_board_0b36a.scud
    with open("tests/Mocks/Archy/bms_bq_sys_c195dff2_eval_board_0b36a.scud", "r") as f:
        scud_content = f.read()
    
    with open(scud_file, "w") as f:
        f.write(scud_content)

    logger.info(f"[_archy_build_scud_stub] [STUB] Dummy SCUD document generated: {scud_file}")
    return scud_file
    
def orchestrate_archy(workspace_path: Union[str, Path], image_id: str):
    """
    Main orchestration function for the Archy module.
    
    Purpose: Generate a Shared Circuit Understanding Document (SCUD) from a schematic image.
    
    Steps:
    1. Run image segmentation pipeline on the source schematic.
    2. Validate that cropped image segments were generated.
    3. Run Archy agent to generate the SCUD document.
    4. Verify the SCUD document was created in the workspace.
    
    Inputs:
    - workspace_path: Path to the workspace directory.
    - image_id: Unique identifier for the source image.
    """
    workspace = Path(workspace_path).resolve()
    
    
    # 1. Step 0: Image Preprocessing
    # Source image is assumed to be at <workspace>/UserArtefacts/<image_id>.png
    source_image_path = workspace / "UserArtefacts" / f"{image_id}.png"
    processed_image_path = workspace / "UserArtefacts" / f"{image_id}_preprocessed.png"
    
    # Predefined output directory for segments
    # Consistent with standard naming and scud_gen_agent's expected structure
    output_dir = workspace / "schematic_images" / image_id
    
    logger.info(f"[orchestrate_archy] Starting orchestration for image_id: {image_id}")
    logger.info(f"[orchestrate_archy] Workspace: {workspace}")
    logger.info(f"[orchestrate_archy] Source Image Path: {source_image_path}")
    
    if not source_image_path.exists():
        raise FileNotFoundError(f"Source image not found at {source_image_path}")

    # Preprocess image before segmentation
    _preprocess_image(source_image_path, processed_image_path)
    # Use preprocessed image as baseline for all downstream tasks
    image_path = processed_image_path

    # Step 1: Run Segmentation Pipeline
    logger.info("[orchestrate_archy] Running image segmentation pipeline...")
    try:
        segmentation_result = run_schematic_segmentation_pipeline(
            output_dir=output_dir,
            image_path=image_path
        )
        logger.info(f"[orchestrate_archy] Segmentation pipeline finished. Detections: {segmentation_result.get('num_detections', 0)}")
    except Exception as e:
        logger.error(f"[orchestrate_archy] Error during image segmentation: {e}")
        raise

    # Validation: Verify segments were created
    if not output_dir.exists() or not any(output_dir.glob("*.png")):
        raise RuntimeError(f"Validation failed: No cropped images found in segment directory {output_dir}")
    
    logger.info(f"[orchestrate_archy] Validation success: Segments found in {output_dir}")

    # Step 2: Trigger Archy Agent (Scud Generation)
    logger.info("[orchestrate_archy] Step 2/2: Triggering Archy agent for SCUD generation...")
    if os.environ.get("ARCHY_STUB") == "true":
        _archy_build_scud_stub(image_id=image_id, workspace_path=workspace, image_path=image_path)
    else:
        from archy_agent.scud_gen_agent import archy_build_scud
        try:
            archy_build_scud(
                image_id=image_id,
                workspace=workspace,
                image_path=image_path
            )
        except Exception as e:
            logger.error(f"[orchestrate_archy] Error during SCUD generation: {e}")
            raise

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
        
    ws_v_path = sys.argv[1]
    img_v_id = sys.argv[2]
    
    try:
        orchestrate_archy(ws_v_path, img_v_id)
    except Exception as e:
        logger.error(f"[main] Orchestration failed: {e}")
        sys.exit(1)
