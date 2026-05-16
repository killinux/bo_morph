# PMX Bone Morph Generator - Blender Addon

## Context

当前PMX模型（从XPS转换而来）有36个面部骨骼（眼睑、眉毛、嘴唇、下巴、舌头等），但没有任何bone morph。需要一个Blender插件，能为任意PMX模型自动生成标准MMD面部表情的bone morph，同时支持手动pose捕获。插件通过现有的client.py远程通道部署到Windows Blender。

## 实现方案

### 产出文件

- `bo_morph.py` — 单文件Blender插件（所有逻辑、预设、UI）
- `deploy.py` — 部署脚本，通过client.py将插件发送到远程Blender并注册

### 插件架构（bo_morph.py）

```
bl_info
BONE_NAME_MAP          — 36个骨骼的 canonical_key → (XPS英文名, 日文MMD名) 映射
EXPRESSION_PRESETS     — 18个标准MMD表情的骨骼变换定义
resolve_bone_name()    — 在armature中查找实际骨骼名（先试XPS名再试日文名）
find_mmd_root()        — 沿层级向上查找mmd_root对象
make_rotation_quat()   — 轴+角度 → 四元数
compute_semantic_axes() — 运行时从骨骼矩阵推断语义旋转轴（close/lateral）

BoneMorphCalibrator    — 基于骨骼几何自动缩放变换幅度
BoneMorphGenerator     — 核心：解析骨骼名 → 计算四元数 → 写入mmd_root.bone_morphs

BOMP_OT_generate_presets    — 一键/分类生成预设表情
BOMP_OT_capture_pose        — 从当前pose捕获为bone morph
BOMP_OT_apply_morph_preview — 预览bone morph效果
BOMP_OT_clear_pose          — 清除pose回rest状态
BOMP_OT_register_display    — 注册morph到表情显示面板

BOMP_PT_main_panel     — 主面板（模型信息）
BOMP_PT_presets_panel   — 预设生成面板
BOMP_PT_capture_panel   — 手动捕获面板

register() / unregister()
```

### 骨骼名映射（双语支持）

36个面部骨骼的canonical key映射，例如：
- `eyelid_upper_L` → `("head eyelid upper left", "左目上")`
- `jaw` → `("head jaw", "あご")`
- `lip_upper_mid` → `("head lip upper middle", "上唇中")`

查找优先级：XPS英文名 → 日文MMD名 → 模糊匹配

### 自动校准算法

基于模型几何自动缩放预设的旋转角度和位移：
1. 测量双眼间距（参考模型Inase54为0.726）
2. 计算全局缩放因子 = 参考值 / 实际值
3. 对每个骨骼：参考骨骼长度 / 实际骨骼长度 → 角度缩放
4. 位移值也按缩放因子调整

### 语义轴检测

核心难点：不同模型骨骼朝向不同，同一个"X轴旋转"在不同模型上效果不同。

解决方案：运行时从骨骼矩阵推断语义轴方向
- `close`轴：最接近世界X轴（左右方向）的骨骼局部轴 — 用于眼睑闭合、下巴张开
- `lateral`轴：最接近世界Z轴（上下方向）的骨骼局部轴 — 用于嘴角左右拉伸

预设使用语义名（`"close"`, `"lateral"`），生成时动态解析为实际轴。

### 18个预设表情

| 类别 | 表情名 | 英文名 | 涉及骨骼 |
|------|--------|--------|----------|
| 目 | まばたき | Blink | 上下眼睑L/R |
| 目 | 笑い | Smile | 眼睑+脸颊+嘴角 |
| 目 | ウィンク | Wink | 左眼睑 |
| 目 | ウィンク右 | Wink_R | 右眼睑 |
| 目 | ウィンク２ | Wink2 | 左眼睑（柔和） |
| 目 | ウィンク２右 | Wink2_R | 右眼睑（柔和） |
| 口 | あ | A | 下巴+全部嘴唇+嘴角 |
| 口 | い | I | 下巴+嘴唇侧+嘴角横拉 |
| 口 | う | U | 下巴+嘴唇收拢+嘴角收 |
| 口 | え | E | 下巴+嘴唇中+嘴角 |
| 口 | お | O | 下巴+嘴唇圆+嘴角收 |
| 眉 | 上 | Brows_Up | 全部眉毛上提 |
| 眉 | 下 | Brows_Down | 全部眉毛下压 |
| 眉 | 怒り | Brows_Angry | 内侧下压+外侧上提 |
| 眉 | 困る | Brows_Sad | 内侧上提+外侧下压 |
| 口 | にやり | Grin | 嘴角+上唇 |
| 口 | ∧ | Mouth_Cat | 嘴角+唇中 |
| 口 | べー | Tongue_Out | 下巴+舌头链 |

### mmd_tools集成

- 写入 `mmd_root.bone_morphs` 集合
- 每个data项：`bone`(名称)、`location`(Vector3)、`rotation`(四元数WXYZ)
- 注册到 `display_item_frames` 的"表情"帧
- category使用mmd_tools枚举值（`'EYE'`/`'EYEBROW'`/`'MOUTH'`/`'OTHER'`）

### 部署方式

通过 `client.py execute` 将整个插件代码作为字符串发送到远程Blender执行：
```
deploy.py 读取 bo_morph.py → 构造execute请求 → client.py → ngrok → server.py → Blender
```

## 验证步骤

1. 部署插件到远程Blender，确认注册成功（UI面板出现在3D视图侧栏）
2. 选中Inase54_arm，点击"All Presets"生成全部18个预设
3. 逐个预览每个morph，验证面部变形方向和幅度正确
4. 确认morph已注册到"表情"显示面板
5. 如角度不对，调整预设参数并重新生成
6. 测试手动pose捕获：摆pose → 捕获 → 验证存储
