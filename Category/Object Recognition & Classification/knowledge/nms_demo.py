"""
非极大值抑制 (NMS) 示例

输入:
    - boxes: N 个候选框, 形状 [N, 4], 格式 [x1, y1, x2, y2]
    - scores: 对应的置信度, 形状 [N]

中间操作:
    1. 按置信度从高到低排序
    2. 依次选择当前最高分框, 将与其 IoU 大于阈值的其它框抑制掉

输出:
    - keep_indices: 经过 NMS 后保留的索引列表
"""

from typing import List

import numpy as np


def compute_iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])

    inter_w = np.maximum(0.0, x2 - x1)
    inter_h = np.maximum(0.0, y2 - y1)
    inter = inter_w * inter_h

    area_box = (box[2] - box[0]) * (box[3] - box[1])
    area_boxes = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    union = area_box + area_boxes - inter

    union = np.maximum(union, 1e-6)
    return inter / union


def nms(
    boxes: np.ndarray,
    scores: np.ndarray,
    iou_thresh: float = 0.5,
) -> List[int]:
    if boxes.size == 0:
        return []

    order = scores.argsort()[::-1]
    keep: List[int] = []

    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break

        ious = compute_iou(boxes[i], boxes[order[1:]])
        remain = np.where(ious <= iou_thresh)[0]
        order = order[remain + 1]

    return keep


if __name__ == "__main__":
    # 使用一组虚拟候选框演示 NMS 的输入与输出
    boxes = np.array(
        [
            [10, 10, 50, 50],
            [12, 12, 48, 48],
            [60, 10, 100, 50],
        ],
        dtype=np.float32,
    )
    scores = np.array([0.9, 0.8, 0.7], dtype=np.float32)
    keep = nms(boxes, scores, iou_thresh=0.5)
    print("输入候选框数:", len(boxes))
    print("保留索引:", keep)
    print("保留的候选框:", boxes[keep])

