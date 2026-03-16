"""
预训练 CNN 迁移学习分类骨架示例 (以 PyTorch 为例)

说明:
    这是一个“骨架代码”，重点在于输入/中间操作/输出流程，
    方便在电赛环境中根据实际硬件与数据集裁剪，而不是一键跑完 ImageNet 级别训练。

输入:
    - 训练/验证集目录, 目录结构形如:
        dataset_root/
            train/
                class0/
                class1/
                ...
            val/
                class0/
                class1/
                ...

中间操作:
    1. 使用 torchvision.datasets.ImageFolder + DataLoader 读入数据
    2. 加载预训练模型 (如 ResNet18), 冻结前几层
    3. 替换最后的全连接层为“电赛类别数”的输出
    4. 进行若干轮微调训练, 观察损失和准确率

输出:
    - 训练好的模型权重文件 (如 best_model.pth)
    - 训练/验证集的准确率日志
"""

from pathlib import Path


def main():
    try:
        import torch
        from torch import nn, optim
        from torch.utils.data import DataLoader
        from torchvision import datasets, models, transforms
    except ImportError as e:
        raise SystemExit(
            "此示例依赖 PyTorch 与 torchvision, "
            "请先安装: pip install torch torchvision\n"
            f"详细错误: {e}"
        )

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--data_root", type=str, required=True, help="数据根目录, 下含 train/ 与 val/")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--num_classes", type=int, required=True)
    args = parser.parse_args()

    data_root = Path(args.data_root)

    # 1. 图像增强与归一化
    train_tf = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    val_tf = transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    train_ds = datasets.ImageFolder(str(data_root / "train"), transform=train_tf)
    val_ds = datasets.ImageFolder(str(data_root / "val"), transform=val_tf)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=2)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 2. 加载预训练 ResNet18 并冻结 Backbone
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    for param in model.layer1.parameters():
        param.requires_grad = False
    for param in model.layer2.parameters():
        param.requires_grad = False

    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, args.num_classes)
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=args.lr)

    best_val_acc = 0.0
    best_path = data_root / "best_model.pth"

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * labels.size(0)
            _, preds = outputs.max(1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        train_loss = total_loss / total
        train_acc = correct / total

        # 验证
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)
                outputs = model(images)
                _, preds = outputs.max(1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

        val_acc = val_correct / max(1, val_total)
        print(f"Epoch {epoch}/{args.epochs} - train_loss={train_loss:.4f}, train_acc={train_acc:.3f}, val_acc={val_acc:.3f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), best_path)
            print(f"  * 更新最佳模型, 保存至 {best_path}")

    print(f"训练完成, 最佳验证准确率: {best_val_acc:.3f}")


if __name__ == "__main__":
    main()

