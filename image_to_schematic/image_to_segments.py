# Objective of this module is to segment given schematic image into different components
# Uses SAMv3 segmentation model to identify modular sub circuits within the schematic image


from PIL import Image
from sam3.model_builder import build_sam3_image_model
from sam3.model.sam3_image_processor import Sam3Processor
# Load the model
print("Loading SAMv3 Image Model...")
model = build_sam3_image_model()
print("Model loaded.")
processor = Sam3Processor(model, confidence_threshold=0.3)
# Load an image
image = Image.open("ckt.png").convert("RGB")
# image = Image.open("bq79616.png").convert("RGB")
print("Setting image...")
inference_state = processor.set_image(image)
print("Image set.")

print("Prompting model with text...")
# Prompt the model with text
output = processor.set_text_prompt(state=inference_state, prompt="Circuit, schematic")
print("finished processing.")
# Get the masks, bounding boxes, and scores
masks, boxes, scores = output["masks"], output["boxes"], output["scores"]

print(f"Detected {len(masks)} masks")
# Print the scores and boxes
for i, (score, box) in enumerate(zip(scores, boxes)):
    print(f"Mask {i}: Score {score:.4f}, Box {box.tolist()}")

# Visualize the results
import matplotlib.pyplot as plt
import numpy as np 
def show_mask(mask, ax, random_color=False):
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
    show_mask(mask.cpu().numpy(), ax, random_color=True)
plt.axis('off')
plt.show()