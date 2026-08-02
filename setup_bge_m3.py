import os
import torch
from huggingface_hub import snapshot_download
from FlagEmbedding import BGEM3FlagModel

# Define paths
BASE_DIR = "/home/gokul/Downloads/final-year-project/models"
MODEL_DIR = os.path.join(BASE_DIR, "bge-m3")
MODEL_ID = "BAAI/bge-m3"

# Create directory
os.makedirs(MODEL_DIR, exist_ok=True)

# Download the model locally if the folder is empty
if not os.listdir(MODEL_DIR):
    print(f"Downloading {MODEL_ID} to {MODEL_DIR}... (This will take a few minutes)")
    snapshot_download(
        repo_id=MODEL_ID, 
        local_dir=MODEL_DIR, 
        local_dir_use_symlinks=False # Ensures actual files are downloaded, not symlinks
    )
    print("Download complete!")
else:
    print("Model files already exist. Skipping download.")

# Load the model using the NVIDIA GPU
print("Loading BGE-M3 model on NVIDIA GPU...")
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"Using device: {device}")

model = BGEM3FlagModel(
    MODEL_DIR, 
    use_fp16=True, # Uses half precision to save VRAM and speed up inference
    device=device
)

print("✅ BGE-M3 Model successfully installed and loaded!")
