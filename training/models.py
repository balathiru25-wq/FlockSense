import torch
import torch.nn as nn
import torchvision.models as models
from torchvision.models import ResNet18_Weights

class FlockSenseResNet18(nn.Module):
    """
    Bioacoustic classifier based on ResNet18 adapted for single-channel log-Mel spectrograms.
    Outputs class logits for [Healthy (0), Unhealthy (1), Noise (2)].
    """
    def __init__(self, num_classes=3, pretrained=True, dropout=0.3):
        super().__init__()
        self.num_classes = num_classes

        # Load ResNet18 backbone
        weights = ResNet18_Weights.DEFAULT if pretrained else None
        backbone = models.resnet18(weights=weights)

        # Adapt first conv layer from 3 channels (RGB) to 1 channel (Mel spectrogram)
        orig_conv1 = backbone.conv1
        self.conv1 = nn.Conv2d(
            in_channels=1,
            out_channels=orig_conv1.out_channels,
            kernel_size=orig_conv1.kernel_size,
            stride=orig_conv1.stride,
            padding=orig_conv1.padding,
            bias=False
        )

        if pretrained:
            # Initialize 1-channel weights as the average of the 3 RGB channels
            with torch.no_grad():
                self.conv1.weight.copy_(orig_conv1.weight.mean(dim=1, keepdim=True))

        self.bn1 = backbone.bn1
        self.relu = backbone.relu
        self.maxpool = backbone.maxpool

        self.layer1 = backbone.layer1
        self.layer2 = backbone.layer2
        self.layer3 = backbone.layer3
        self.layer4 = backbone.layer4

        self.avgpool = backbone.avgpool

        # Custom classification head
        in_features = backbone.fc.in_features  # 512
        self.fc = nn.Sequential(
            nn.Dropout(p=dropout),
            nn.Linear(in_features, 128),
            nn.LayerNorm(128),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout * 0.7),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        """
        Input: [batch, 1, 128, time_steps]
        Output: [batch, num_classes]
        """
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        logits = self.fc(x)
        return logits

    def count_parameters(self):
        total = sum(p.numel() for p in self.parameters())
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        return total, trainable
