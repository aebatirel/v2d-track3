"""GDRN-style correspondence network: 256² grey crop -> 64² visible mask, amodal mask, normalised XYZ (own code)."""
import torch, torch.nn as nn, torch.nn.functional as F
import torchvision


def block(i, o):
    return nn.Sequential(nn.Conv2d(i, o, 3, padding=1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
                         nn.Conv2d(o, o, 3, padding=1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True))


class PotNet(nn.Module):
    def __init__(self, pretrained=True):
        super().__init__()
        w = torchvision.models.ResNet34_Weights.IMAGENET1K_V1 if pretrained else None
        r = torchvision.models.resnet34(weights=w)
        self.stem = nn.Sequential(r.conv1, r.bn1, r.relu, r.maxpool)     # /4 -> 64
        self.l1, self.l2, self.l3, self.l4 = r.layer1, r.layer2, r.layer3, r.layer4   # 64,32,16,8 px; 64,128,256,512 ch
        self.u3 = block(512 + 256, 256)
        self.u2 = block(256 + 128, 128)
        self.u1 = block(128 + 64, 128)
        self.head = nn.Conv2d(128, 5, 1)                                  # vis, full, xyz(3)
        self.register_buffer('mean', torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1))
        self.register_buffer('std', torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1))

    def forward(self, g):                                                 # g: (B,1,256,256) in [0,1]
        x = (g.expand(-1, 3, -1, -1) - self.mean) / self.std
        x1 = self.l1(self.stem(x)); x2 = self.l2(x1); x3 = self.l3(x2); x4 = self.l4(x3)
        up = lambda a, b: torch.cat([F.interpolate(a, size=b.shape[-2:], mode='bilinear', align_corners=False), b], 1)
        y = self.u3(up(x4, x3)); y = self.u2(up(y, x2)); y = self.u1(up(y, x1))
        o = self.head(y)
        return o[:, 0], o[:, 1], torch.tanh(o[:, 2:])                     # logits vis, logits full, xyz in [-1,1]
