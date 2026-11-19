"""
Module: train_model.py
Purpose: Trains Deepfake Detection Model using Pre-trained ResNet-18 Transfer Learning
"""
import os
import sys
import json
import time
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Configuration
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DIR = os.path.join(PROJECT_DIR, "dataset", "processed")
MODEL_SAVE_PATH = os.path.join(PROJECT_DIR, "model", "deepfake_detector.pt")
CLASS_MAPPING_PATH = os.path.join(PROJECT_DIR, "model", "classes.json")
METRICS_PLOT_PATH = os.path.join(PROJECT_DIR, "static", "confusion_matrix.png")

BATCH_SIZE = 8
EPOCHS = 15
LEARNING_RATE = 0.0003
IMAGE_SIZE = (128, 128)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ==========================================
# 1. Transfer Learning Deepfake Detector
# ==========================================
class DeepfakeDetectorNet(nn.Module):
    def __init__(self, num_classes=2, pretrained=False):
        super(DeepfakeDetectorNet, self).__init__()
        # Use ResNet-18 backbone (only download ImageNet default when training from scratch)
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        self.backbone = models.resnet18(weights=weights)
        in_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Sequential(
            nn.Dropout(p=0.4),
            nn.Linear(in_features, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.3),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        return self.backbone(x)

# Backward-compatible alias
DeepfakeCNN = DeepfakeDetectorNet

# ==========================================
# 2. Data Loaders & Data Augmentation
# ==========================================
def get_data_loaders():
    train_dir = os.path.join(PROCESSED_DIR, "train")
    val_dir = os.path.join(PROCESSED_DIR, "val")
    test_dir = os.path.join(PROCESSED_DIR, "test")

    for path, name in [(train_dir, "Train"), (val_dir, "Val"), (test_dir, "Test")]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"{name} folder missing at {path}. Run prepare_dataset.py first!")

    # Rich data augmentation to simulate diverse real-world lighting and camera angles
    train_transforms = transforms.Compose([
        transforms.Resize(IMAGE_SIZE),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=12),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_test_transforms = transforms.Compose([
        transforms.Resize(IMAGE_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_dataset = datasets.ImageFolder(train_dir, transform=train_transforms)
    val_dataset = datasets.ImageFolder(val_dir, transform=val_test_transforms)
    test_dataset = datasets.ImageFolder(test_dir, transform=val_test_transforms)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    classes = train_dataset.classes # ['fake', 'real']
    with open(CLASS_MAPPING_PATH, 'w') as f:
        json.dump(classes, f, indent=4)
    print(f"[✓] Class mapping saved: {classes} -> {CLASS_MAPPING_PATH}")

    return train_loader, val_loader, test_loader, classes

# ==========================================
# 3. Training & Evaluation
# ==========================================
def train_and_evaluate():
    print("=" * 65)
    print("DEEPFAKE DETECTION - ADVANCED RESNET-18 TRAINING PIPELINE")
    print("=" * 65)
    print(f"[+] Compute Hardware: {DEVICE}")

    train_loader, val_loader, test_loader, classes = get_data_loaders()
    print(f"[+] Dataset Loaded: {len(train_loader.dataset)} Train, {len(val_loader.dataset)} Val, {len(test_loader.dataset)} Test")

    model = DeepfakeDetectorNet(num_classes=len(classes)).to(DEVICE)
    
    # Balanced cross entropy loss with label smoothing
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_val_loss = float('inf')
    start_time = time.time()

    print("-" * 65)
    print(f"{'Epoch':<8} | {'Train Loss':<12} | {'Train Acc':<10} | {'Val Loss':<10} | {'Val Acc':<10}")
    print("-" * 65)

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss, train_correct, train_total = 0.0, 0, 0
        for images, labels in train_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            train_correct += (preds == labels).sum().item()
            train_total += labels.size(0)

        scheduler.step()
        train_epoch_loss = train_loss / max(1, train_total)
        train_epoch_acc = (train_correct / max(1, train_total)) * 100

        # Validation
        model.eval()
        val_loss, val_correct, val_total = 0.0, 0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(DEVICE), labels.to(DEVICE)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * images.size(0)
                _, preds = torch.max(outputs, 1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

        val_epoch_loss = val_loss / max(1, val_total)
        val_epoch_acc = (val_correct / max(1, val_total)) * 100

        print(f"{epoch:<8} | {train_epoch_loss:<12.4f} | {train_epoch_acc:<9.1f}% | {val_epoch_loss:<10.4f} | {val_epoch_acc:<9.1f}%")

        if val_epoch_loss < best_val_loss:
            best_val_loss = val_epoch_loss
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'classes': classes,
                'val_acc': val_epoch_acc
            }, MODEL_SAVE_PATH)

    elapsed = time.time() - start_time
    print("-" * 65)
    print(f"[✓] Model training completed in {elapsed:.1f} seconds.")
    print(f"[✓] Best model weights saved to: {MODEL_SAVE_PATH}")

    # Testing & Metrics
    print("=" * 65)
    print("TEST SET EVALUATION & PERFORMANCE METRICS")
    print("=" * 65)

    checkpoint = torch.load(MODEL_SAVE_PATH, map_location=DEVICE, weights_only=True)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    all_preds, all_labels = [], []
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(DEVICE)
            outputs = model(images)
            _, preds = torch.max(outputs, 1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    acc = accuracy_score(all_labels, all_preds) * 100
    precision, recall, f1, _ = precision_recall_fscore_support(all_labels, all_preds, average='weighted', zero_division=0)

    print(f"Test Accuracy  : {acc:.2f}%")
    print(f"Weighted F1    : {f1:.4f}")
    print(f"Weighted Recall: {recall:.4f}")
    print(f"Precision      : {precision:.4f}")

    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=[c.upper() for c in classes],
                yticklabels=[c.upper() for c in classes])
    plt.title(f'Deepfake Detection Confusion Matrix (Acc: {acc:.1f}%)')
    plt.xlabel('Predicted Label')
    plt.ylabel('Ground Truth Label')
    plt.tight_layout()
    plt.savefig(METRICS_PLOT_PATH, dpi=150)
    plt.close()
    print(f"[✓] Confusion matrix visualization saved to: {METRICS_PLOT_PATH}")
    print("=" * 65)

if __name__ == "__main__":
    train_and_evaluate()
