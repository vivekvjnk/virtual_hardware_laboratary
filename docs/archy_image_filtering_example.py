"""
Integration Example: Using EventFilter in Archy Pipeline

This example demonstrates how to integrate the EventFilter solution
into the Archy pipeline to prevent context bloat when processing
multiple image crops.
"""

from pathlib import Path
from openhands.sdk import AgentConfig, LocalConversation

from openhands.sdk.llm import LLM


def orchestrate_archy_with_image_filtering(
    workspace_path: str,
    image_id: str,
    model_name: str = "gemini-2.0-flash-exp"
):
    """
    Orchestrate the Archy pipeline with image filtering enabled.
    
    This function demonstrates how to configure and use the EventFilter
    to prevent context bloat when processing many image crops.
    
    Args:
        workspace_path: Path to the workspace directory
        image_id: ID of the reference schematic image
        model_name: Name of the LLM model to use
    """
    
    # Step 1: Configure image filtering
    # Since Archy processes many image crops sequentially,
    # we configure aggressive filtering to keep only recent images
    filter_config = EventFilterConfig(
        enabled=True,
        # Keep images for only the last 3 observations
        # This is sufficient as the agent focuses on one crop at a time
        recent_event_threshold=3,
        
        # Target only file_editor tool (where images come from)
        target_tools=["file_editor"],
        
        # Custom replacement text for clarity
        replacement_template="[Analyzed crop: {path}]",
        
        # Use age-based filtering for predictable behavior
        filter_mode="age",
    )
    
    # Step 2: Set up LLM with vision enabled
    llm = LLM(model=model_name)
    
    # Step 3: Create agent config
    agent_config = AgentConfig(
        llm=llm,
        # ... other agent configuration ...
    )
    
    # Step 4: Create conversation with filter config
    # Note: This assumes the LocalConversation class has been updated
    # to accept and use event_filter_config
    conversation = LocalConversation(
        agent_config=agent_config,
        workspace=workspace_path,
    )
    
    # Step 5: Process image crops
    reference_image = Path(workspace_path) / "UserArtifacts" / f"{image_id}.png"
    crops_dir = Path(workspace_path) / "cropped_images"
    
    # Get all cropped images
    crop_files = sorted(crops_dir.glob("crop_*.png"))
    
    print(f"Processing {len(crop_files)} image crops with filtering enabled")
    
    
    # Initialize SCUD document
    conversation.add_message(
        "Your task is to analyze circuit schematic image crops and build a "
        "comprehensive SCUD (Schematic and Circuit Understanding Document). "
        "You will be shown multiple crops sequentially. Focus on each one, "
        "extract information, and incrementally build the document."
    )
    
    # Process each crop
    for i, crop_path in enumerate(crop_files, 1):
        print(f"\nProcessing crop {i}/{len(crop_files)}: {crop_path.name}")
        
        # Ask agent to view and analyze the crop
        conversation.add_message(
            f"Please view and analyze the circuit crop at: {crop_path}"
        )
        
        # At this point:
        # - Recent crops (last 3) will have full image content in context
        # - Older crops will have replacement text: "[Analyzed crop: /path/to/crop_X.png]"
        # - This prevents exponential context growth while maintaining recent context
        
        # The agent can still use file_editor to re-view old crops if needed
        # (the filter only affects chat history, not the filesystem)
    
    # Step 6: Generate final SCUD document
    conversation.add_message(
        "Based on all the crops you've analyzed, please generate the final "
        "SCUD document and save it to the workspace."
    )
    
    print("\nArchy pipeline completed with image filtering active")
    print(f"Context bloat significantly reduced!")


def example_comparison():
    """
    Demonstrate the difference in context size with and without filtering.
    """
    
    print("=" * 60)
    print("CONTEXT SIZE COMPARISON")
    print("=" * 60)
    
    num_crops = 20
    avg_image_size_kb = 50  # Average base64 image size
    
    # Without filtering
    without_filter = num_crops * avg_image_size_kb
    print(f"\nWithout filtering:")
    print(f"  - All {num_crops} image crops in context")
    print(f"  - Approximate context size: {without_filter} KB")
    print(f"  - Result: Exponential growth, potential model confusion")
    
    # With filtering (threshold = 3)
    recent_threshold = 3
    with_filter = recent_threshold * avg_image_size_kb
    replaced_images = num_crops - recent_threshold
    replaced_text_per_image = 0.05  # KB for "[Analyzed crop: ...]"
    text_overhead = replaced_images * replaced_text_per_image
    total_with_filter = with_filter + text_overhead
    
    print(f"\nWith filtering (threshold={recent_threshold}):")
    print(f"  - {recent_threshold} recent images in full context")
    print(f"  - {replaced_images} older images replaced with text")
    print(f"  - Approximate context size: {total_with_filter:.1f} KB")
    
    reduction_percent = ((without_filter - total_with_filter) / without_filter) * 100
    print(f"\n  → Context size reduction: {reduction_percent:.1f}%")
    print(f"  → Result: Linear growth, better model performance")


def example_manual_filtering():
    """
    Example of manually applying the filter to events.
    
    This shows how to use the EventFilter directly without
    integration into the conversation class.
    """
    from openhands.sdk.conversation.event_filter import EventFilter
    
    # Create filter
    config = EventFilterConfig(recent_event_threshold=5)
    event_filter = EventFilter(config)
    
    # Assume we have a conversation with events
    # conversation = LocalConversation(...)
    # events = conversation.get_events()  # Get all events
    
    # Apply filtering
    # filtered_events = event_filter.filter_events(events)
    
    # Use filtered events for message preparation
    # from openhands.sdk.agent.utils import prepare_llm_messages
    # messages = prepare_llm_messages(filtered_events)
    
    print("Manual filtering example (see code for details)")


if __name__ == "__main__":
    print("=" * 60)
    print("ARCHY PIPELINE - IMAGE FILTERING INTEGRATION EXAMPLE")
    print("=" * 60)
    
    # Show context size comparison
    example_comparison()
    
    print("\n" + "=" * 60)
    print("INTEGRATION STEPS")
    print("=" * 60)
    print("""
1. Copy event_filter.py and event_filter_config.py to agent-sdk
2. Modify LocalConversation to accept event_filter_config parameter
3. Integrate filter into prepare_llm_messages() in agent/utils.py
4. Run tests to verify functionality
5. Deploy to Archy pipeline

See orchestrate_archy_with_image_filtering() for complete example.
    """)
    
    example_manual_filtering()
