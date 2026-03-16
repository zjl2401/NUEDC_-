## NUEDC 仓库总览

本仓库用于整理和复用 **全国大学生电子设计竞赛（NUEDC）** 相关题目的代码与知识库，按照「能力类别」与「难度等级」两条主线组织：

- **Category/**：按技术方向分类（视觉跟踪与目标定位、目标识别与分类、精密测量与建图、自主飞行与避障等），更偏“知识图谱 + 模板工程”。
- **Difficulty Levels/**：按题目综合难度分级（如 1/2/3/4 级），聚合不同年份但难度相近的完整赛题工程。

希望做到：**同一类算法在不同年份题目间可以复用，而不必每次“从零再写一遍”。**

---

### 一、目录结构

- **Category/** 按技术方向划分的通用模板与知识库
  - `Visual Tracking & Object Localization/`
    - 各年份子题工程（如 `2005E/`, `2023E/`, `2025E/` 等）。
    - `knowledge/`：视觉跟踪与目标定位的通用知识库：
      - `总流程.ini`：从感知层 → 筛选层 → 定位层 → 状态估计层 → 输出/通信层的完整流程说明。
      - 若干 `#.py` 示例：灰度/HSV 分割、形态学、连通域过滤、形状分析、四边形检测、透视变换等基础算法模板。
  - `Object Recognition & Classification/`
    - 各年份子题工程（如 `2021F/`, `2021H/`, `2023G/`, `2025H/`）。
    - `knowledge/`：
      - `总流程.ini`：从图像预处理、候选生成、特征表示、分类决策，到多帧融合与训练评估的标准流水线。
      - `算法与知识点总结.md`：颜色/形态预处理、连通域与候选框、传统特征 (HOG/LBP/SIFT)、深度特征、SVM/CNN/Transformer 分类等知识点梳理。
  - `Precision Measurement & Mapping/`
    - 各年份子题工程（如 `2021D/`, `2025C/`, `2025I/`）。
    - `knowledge/`：
      - `总流程.ini`：标定与预处理 → 特征匹配 → 几何测量/深度估计 → 点云与建图 → 精度评估 的总体思路。
      - `算法与知识点总结.md`：相机内外参标定、RANSAC、双目/视差测距、PnP 位姿解算、ICP/NDT 配准、误差指标等。
  - `Autonomous Flight & Obstacle Avoidance/`
    - 各年份子题工程（如 `2017C/`, `2021G/`, `2025H/`）。
    - `knowledge/`：
      - `总流程.ini`：感知 → 环境建模/障碍检测 → 轨迹规划/局部避障 → 飞行控制 → 状态估计与闭环优化。
      - `算法与知识点总结.md`：视觉/雷达感知、占据栅格与代价地图、A*/RRT/DWA、级联 PID/MPC、EKF/UKF 等。

- **Difficulty Levels/** 按难度分级的完整赛题工程
  - `1Laser Spot & Color Blob Tracking/`
  - `2Line Following, Character Recognition & Basic Measurement/`
  - `3UAV Navigation Firefighting in Complex Environments/`
  - `4Dynamic Perception & Scene Understanding in Complex Scenarios/`
  - 每个难度子目录下又按年份/题号（如 `2005E/`, `2023E/`, `2025H/` 等）拆分，并配有各自的 `README.md` 与 `requirements.txt`，用于快速跑通某一具体赛题。

---

### 二、使用建议

- **按“知识类型”检索**  
  如果你在准备某类算法（比如“视觉定位”、“目标识别”、“建图”、“避障”），优先从 `Category/` 对应大类入手：
  - 阅读该类 `knowledge/` 下的 `总流程.ini` 和 `算法与知识点总结.md`，快速建立整体认知。
  - 结合 `Category` 里对应年份的工程代码，查函数/模块如何落地实现。

- **按“具体赛题”复盘与演练**  
  如果你要复现或学习某一年某一题：
  - 在 `Difficulty Levels/` 中找到相应难度 + 年份的子目录（通常同目录下会有多道相似风格的题目）。
  - 按该子目录的 `README.md` 安装依赖、运行 `main.py` / `run.py` / `simulator.py` 等入口脚本。

---

### 三、扩展与维护约定

- **新增题目/工程时**
  - 在对应的 `Category/` 与 `Difficulty Levels/` 下都放一份工程（前者偏“算法模板与复用”，后者偏“原题工程结构”）。
  - 若引入了新的算法套路或重要经验，优先补充到对应 `Category/.../knowledge` 下，而不是只写在代码里。

- **文档命名约定**
  - `README.md`：放在每一个“可单独运行”的工程目录里，说明运行方式与依赖。
  - `算法实现与知识点总结.md`：描述某个具体工程中的函数划分、行号分布以及需要掌握的理论。
  - `knowledge/总流程.ini` + `knowledge/算法与知识点总结.md`：作为该技术方向的“通用知识库”，与年份/题号解耦。

---

### 四、快速上手路线（建议）

1. 从 `Category/Visual Tracking & Object Localization/knowledge` 入门基础的视觉检测与定位流程。
2. 根据兴趣与赛题方向，在 `Object Recognition & Classification` / `Precision Measurement & Mapping` / `Autonomous Flight & Obstacle Avoidance` 中各挑一类深入。
3. 回到 `Difficulty Levels/`，选取对应难度的一道近年赛题，按该题 `README.md` 跑通仿真/真实系统。
4. 在此基础上，对比不同年份的解法，尝试提取自己的通用模板或封装库，并补充到本仓库中。

通过这种组织方式，本仓库既可以作为 **NUEDC 系统备赛笔记**，也可以作为 **计算机视觉 + 控制 + 机器人方向的项目样例库** 持续迭代。

