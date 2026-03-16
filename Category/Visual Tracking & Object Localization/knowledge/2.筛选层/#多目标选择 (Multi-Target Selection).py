#多目标选择 (Multi-Target Selection)
'''
当画面中出现多个符合条件的目标时，算法必须根据业务逻辑“挑出”那一个。
输入： 包含多个检测结果的列表。
中间操作：
    特征比对： 比较每个目标的面积、距离中心位置、或颜色深度。
    时域跟踪 (ID 锁定)： 比较当前目标与上一帧目标的位置，选择位移最小的（防止目标跳变）。
输出： 选定的单一目标数据。

Python
class TargetSelector:
    def __init__(self):
        self.last_target_pos = None # 记录上一帧位置

    def select(self, candidates):
        """
        candidates: 格式为 [{'id': 0, 'pos': (x,y), 'area': 1000}, ...]
        """
        if not candidates: return None
        
        # 逻辑 1：如果没有历史记录，选择面积最大的 (通常是最接近相机的)
        if self.last_target_pos is None:
            target = max(candidates, key=lambda x: x['area'])
        
        # 逻辑 2：如果有历史记录，选择距离上一帧最近的 (连续跟踪)
        else:
            target = min(candidates, key=lambda x: np.linalg.norm(np.array(x['pos']) - np.array(self.last_target_pos)))
            
            # 距离过大可能是误报，需要阈值判断
            dist = np.linalg.norm(np.array(target['pos']) - np.array(self.last_target_pos))
            if dist > 100: # 100 像素阈值
                target = max(candidates, key=lambda x: x['area']) # 重置
        
        self.last_target_pos = target['pos']
        return target
'''