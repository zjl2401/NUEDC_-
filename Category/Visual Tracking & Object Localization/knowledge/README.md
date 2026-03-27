# Visual Tracking Knowledge 说明

该目录用于沉淀「视觉追踪与定位」知识点示例，按感知/筛选/定位分层组织。

## 目录结构

- `1.感知层`：颜色空间、阈值、连通域、光照归一化
- `2.筛选层`：形状/面积/目标筛选
- `3.定位层`：质心、透视、目标选择与定位

## 历史命名说明

目录中存在部分历史文件名（例如以 `#` 开头、带空格或括号混排）。这些文件目前保留以避免影响已存在引用。

后续新增文件请遵循 `Category/knowledge_统一规范.md`：

- 使用 `snake_case` 命名
- 不再使用 `#` 前缀
- 文件开头写明用途、输入输出

## 建议新增格式

- `demo_hsv_threshold.py`
- `demo_contour_filter.py`
- `demo_perspective_transform.py`
- `notes_localization.md`

