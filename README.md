# bo_morph

PMX Bone Morph Generator - 为 PMX 模型自动生成面部 bone morph 的 Blender 插件。

## 功能

- 18 个标准 MMD 面部表情自动生成（blink、smile、A/I/U/E/O、眉毛等）
- **自动校准闭眼**：通过上下眼皮曲线拟合，自动计算最优闭眼参数
- 支持 XPS 英文骨骼名和日文 MMD 骨骼名
- 手动 pose 捕获为 bone morph
- 通过远程通道部署到 Windows Blender

## 安装方式

### 方式一：永久安装（推荐）

1. 将 `bo_morph.py` 复制到 Blender 的 addons 目录：
   - Windows: `%APPDATA%\Blender Foundation\Blender\3.6\scripts\addons\`
   - Mac: `~/Library/Application Support/Blender/3.6/scripts/addons/`
2. 打开 Blender → Edit → Preferences → Add-ons
3. 搜索 "PMX Bone Morph"，勾选启用

### 方式二：远程部署

```bash
# 需要先启动 win_b 的 server.py + ngrok
python3 deploy.py            # 部署插件
python3 deploy.py --generate  # 部署 + 生成全部表情
python3 deploy.py --preview 0 # 预览第0个morph
python3 deploy.py --clear     # 清除pose
```

## 使用方法

### 1. 生成表情

1. 在 Blender 中选中 PMX 模型的 **Armature**
2. 按 **N** 打开侧栏 → 找到 **"MMD Morph"** 标签
3. 展开 **"Expression Presets"** 面板
4. 点击 **"Generate All"** → 自动校准闭眼 + 生成18个表情

也可按分类生成：**Eye** / **Mouth** / **Brow**

### 2. 自动校准闭眼

点击 **"Auto-Calibrate Blink"** 按钮，插件会：

1. 识别上下眼皮的边缘顶点曲线
2. 网格搜索最优旋转角度和平移量
3. 使上眼皮边缘尽可能贴合下眼皮边缘

Generate All 时会自动执行此步骤。

### 3. 预览 / 删除

- 在 **"Bone Morphs"** 面板中，点击 **▶** 预览，**✕** 删除
- 点击 **"Reset Pose"** 恢复初始状态

### 4. 手动捕获

1. 进入 Pose Mode，手动调整骨骼姿态
2. 在 **"Manual Capture"** 面板中点击 **"Capture Pose as Bone Morph"**
3. 输入名称和分类，确认

### 5. 导出

生成的 morph 已写入 mmd_tools 数据结构，使用 mmd_tools 的 **File → Export → PMX** 导出即可。

## 支持的表情

| 类别 | 表情 | 说明 |
|------|------|------|
| 目 | まばたき | 闭眼（自动校准） |
| 目 | 笑い | 笑眼 + 脸颊上推 + 眼球后移 |
| 目 | ウィンク / ウィンク右 | 左/右单眼闭合 |
| 目 | ウィンク２ / ウィンク２右 | 下眼皮为主的闭眼 |
| 口 | あ / い / う / え / お | 五元音口型 |
| 眉 | 上 / 下 | 眉毛升降 |
| 眉 | 怒り / 困る | 怒眉 / 愁眉 |
| 口 | にやり | 咧嘴笑 |
| 口 | ∧ | 猫嘴 |
| 口 | べー | 吐舌 |

## 支持的骨骼命名

| 部位 | XPS 英文名 | 日文 MMD 名 |
|------|-----------|------------|
| 上眼皮 | head eyelid upper left/right | 左目上 / 右目上 |
| 下眼皮 | head eyelid lower left/right | 左目下 / 右目下 |
| 眼球 | head eyeball left/right | 左目 / 右目 |
| 下巴 | head jaw | あご |
| 上唇 | head lip upper left/right/middle | 上唇左 / 上唇右 / 上唇中 |
| 下唇 | head lip lower left/right/middle | 下唇左 / 下唇右 / 下唇中 |
| 嘴角 | head mouth corner left/right | 左口角 / 右口角 |
| 眉毛 | head eyebrow left/right root/1/2/3 | 左眉根 / 右眉根 等 |
| 脸颊 | head cheek left/right 1 | 左ほほ / 右ほほ |
| 舌头 | head tongue 1/2/3 | 舌1 / 舌2 / 舌3 |
| 鼻翼 | head nose nostril left/right | 左鼻 / 右鼻 |

## 技术原理

### 旋转计算

使用 cross-product 方法确定旋转轴：`rot_axis = bone_direction × desired_motion`，自动适配不同骨骼朝向，左右镜像骨骼自动处理。

### 闭眼自动校准

将上下眼皮建模为两条曲线，在旋转角度 × 平移量的二维参数空间中网格搜索，最小化上眼皮变形后与下眼皮的平均距离。

### 语义轴

- `close`：bone_dir × (0,0,-1)，正值=下移（闭眼、张嘴）
- `lateral`：bone_dir × (1,0,0)，正值=左移（嘴巴展开/收缩）

## 版本历史

- **v1.2** - 自动校准闭眼（曲线拟合）
- **v1.1** - 反向旋转防止外侧过度闭合，眼球后移防穿模
- **v1.0** - 18个标准表情，语义轴旋转，双语骨骼支持
