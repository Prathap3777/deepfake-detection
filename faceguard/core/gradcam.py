"""
FACEGUARD AI - Explainable AI (XAI) Grad-CAM Heatmap Engine
Module: faceguard/core/gradcam.py
Generates Gradient-Weighted Class Activation Maps from ResNet-18 layer4
"""
import os
import cv2
import numpy as np
import torch
from torchvision import transforms
from PIL import Image
from faceguard.config import Config

IMAGE_SIZE = (128, 128)

class GradCAM:
    """
    Explainable AI engine for Deep Residual Networks (ResNet-18).
    Extracts spatial gradients from the final convolutional stage to highlight
    the exact facial regions influencing genuine or manipulated classifications.
    """
    def __init__(self, model, target_layer=None):
        self.model = model
        self.device = next(model.parameters()).device
        # Target the final residual basic block in ResNet-18 layer4
        self.target_layer = target_layer or model.backbone.layer4[-1]
        self.activations = None
        self.gradients = None

        self.transform = transforms.Compose([
            transforms.Resize(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def _save_activation(self, module, input, output):
        self.activations = output.detach()

    def _save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate(self, face_bgr, target_class=None):
        """
        Generates genuine Grad-CAM activation map for a cropped facial image.
        Returns:
            heatmap_raw: 2D numpy array [0.0 - 1.0]
            heatmap_jet: Colorized JET colormap BGR
            overlay_bgr: Blended face + heatmap overlay
            predicted_class: 0 ('fake') or 1 ('real')
            class_name: 'FAKE' or 'REAL'
            focus_regions: text summary of activation hotspots
        """
        h_orig, w_orig, _ = face_bgr.shape
        face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(face_rgb)
        tensor_input = self.transform(pil_img).unsqueeze(0).to(self.device)

        # Register forward and backward hooks on target conv layer
        handle_act = self.target_layer.register_forward_hook(self._save_activation)
        handle_grad = self.target_layer.register_full_backward_hook(self._save_gradient)

        try:
            with torch.enable_grad():
                tensor_input = tensor_input.clone().requires_grad_(True)
                self.model.zero_grad()
                logits = self.model(tensor_input)

                # Class 0: fake, Class 1: real
                if target_class is None:
                    target_class = int(torch.argmax(logits, dim=1).item())

                score = logits[0, target_class]
                score.backward(retain_graph=False)

            # Global average pooling of gradients: weights alpha_k
            weights = torch.mean(self.gradients, dim=[2, 3], keepdim=True)
            # Weighted combination of forward activation maps
            cam = torch.sum(weights * self.activations, dim=1, keepdim=True)
            # ReLU: only features with positive influence on class score
            cam = torch.relu(cam)

            cam = cam.squeeze().cpu().numpy()
            cam_min = np.min(cam)
            cam_max = np.max(cam)
            if cam_max - cam_min > 1e-8:
                cam = (cam - cam_min) / (cam_max - cam_min)
            else:
                cam = np.zeros_like(cam)

        finally:
            handle_act.remove()
            handle_grad.remove()
            self.model.zero_grad()
            self.activations = None
            self.gradients = None

        # Resize CAM to match original cropped face dimensions
        cam_resized = cv2.resize(cam, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)
        heatmap_uint8 = np.uint8(255 * cam_resized)
        heatmap_jet = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)

        # Alpha blend overlay: 65% original face, 35% heatmap
        overlay_bgr = cv2.addWeighted(face_bgr, 0.65, heatmap_jet, 0.35, 0)

        class_name = "REAL" if target_class == 1 else "FAKE"

        # Determine spatial attention hotspots
        # Divide face into 3 vertical zones: Upper (Eyes/Forehead), Mid (Nose/Cheeks), Lower (Mouth/Jaw)
        third_h = h_orig // 3
        upper_act = float(np.mean(cam_resized[0:third_h, :]))
        mid_act = float(np.mean(cam_resized[third_h:2*third_h, :]))
        lower_act = float(np.mean(cam_resized[2*third_h:, :]))

        zone_scores = [("Eyes & Periorbital Boundary", upper_act),
                       ("Nose Bridge & Mid-Face", mid_act),
                       ("Mouth, Lips & Jawline Seam", lower_act)]
        zone_scores.sort(key=lambda z: z[1], reverse=True)
        top_zone = zone_scores[0][0]

        focus_desc = f"Primary CNN gradient attention concentrated in the {top_zone}."

        return {
            "heatmap_raw": cam_resized,
            "heatmap_jet": heatmap_jet,
            "overlay_bgr": overlay_bgr,
            "target_class": target_class,
            "class_name": class_name,
            "primary_focus": top_zone,
            "focus_description": focus_desc,
            "zone_distribution": {
                "upper_eyes": round(upper_act * 100, 1),
                "mid_cheeks": round(mid_act * 100, 1),
                "lower_mouth": round(lower_act * 100, 1)
            }
        }
