# Android 高清版仙剑 — 执行计划

## 目标

在 Android 手机上玩到画面经过高清化处理的《仙剑奇侠传》。

## 现状分析

SDLPAL 项目已具备以下能力：
- Android 构建管线完整（NDK Build + SDL3）
- GLSL shader 后处理管线已就绪（`PAL_HAS_GLSL=1`）
- 设置界面已有 GLSL、HDR、Shader 路径、纹理分辨率等配置项
- 内置 CRT、Cartoon 等 shader，并兼容 RetroArch GLSL Shader 格式

游戏内部渲染固定为 320×200 8-bit，"高清"通过 GLSL shader 将低分辨率画面智能放大到高分辨率纹理输出。

---

## 高清方案对比

| 方案 | 原理 | 画质 | 性能 | 改动量 | 适合仙剑 |
|------|------|------|------|--------|----------|
| **xBRZ-freescale** | 规则检测像素边缘，智能插值平滑 | ★★★★ | 实时 60fps | 零代码，纯配置 | ✅ 最佳性价比 |
| **ScaleFX** | 多 pass 边缘感知缩放，RetroArch 公认最优像素放大 | ★★★★★ | 实时，4-5 pass 稍重 | 零代码，纯配置 | ✅ 效果最好的纯 shader 方案 |
| **Anime4K** | 轻量 GLSL 线条重建算法，实时超分 | ★★★½ | 实时 60fps | 需适配 shader 格式 | ⚠️ 针对动画优化，像素画非最佳 |
| **Real-ESRGAN** | AI 神经网络超分（GAN 模型） | ★★★★★+ | ❌ 无法实时 | 需集成 ncnn 推理引擎 | ❌ 不适合实时游戏 |

### 为什么 Real-ESRGAN 预处理素材替换也不可行

直觉上最好的方案：用 Real-ESRGAN 预先把所有素材离线放大 4x，替换进游戏，运行时就不需要实时推理了。

**但这条路走不通**，原因是仙剑的代码架构：

1. **全局 320×200 硬编码无处不在**
   - `gpScreen` 固定创建为 320×200 8-bit surface，所有绘制最终写入这里
   - FBP（全屏背景）硬编码 `if (w != 320 || h != 200) return -1`
   - RNG 动画硬编码 `x = dst_ptr % 320; y = dst_ptr / 320`
   - 波浪特效写死 `// WARNING: assuming the screen width is 320`

2. **169+ 处绝对像素坐标硬编码**
   - 所有 UI 元素位置（菜单、状态、装备、战斗）用 `PAL_XY(数字, 数字)` 写死
   - 分布在 `uigame.c`(43处)、`uibattle.c`(18处)、`battle.c`(20处) 等十几个文件

3. **8-bit RLE 编码绑定整个渲染链**
   - Sprite 是自定义 RLE 格式，解码器直接按字节操作（1像素=1字节=1个调色板索引）
   - 所有 Blit 函数假设目标是 8-bit surface
   - 如果素材改为高分辨率，需要重写整个 RLE 解码器 + 所有渲染路径

4. **地图瓦片 32×15 固定尺寸**
   - 坐标转换 `x*32 + h*16, y*16 + h*8` 硬编码在地图系统中
   - 碰撞检测半径 `16` 像素、移动步长 `±16/±8` 全部固定

5. **调色板系统是 256 色索引色**
   - 所有色彩操作（阴影、渐变、闪白）通过操作索引值的高4位/低4位实现
   - 高分辨率 true-color 素材无法直接进入这套系统

**结论：** 替换素材 = 重写整个游戏引擎（渲染、UI、地图、碰撞、特效），工作量是月级别的，远超合理范围。

### 推荐方案：ScaleFX + HDR（效果最优）

**ScaleFX** 是 RetroArch 社区公认的像素艺术最高质量放大 shader：
- 多 pass 边缘检测 + 智能插值，效果接近手绘放大
- 比 xBRZ 边缘更平滑，细节保留更好
- 在手机 GPU 上完全可以实时运行
- 项目已支持 multi-pass GLSL shader，无需改代码

**备选：xBRZ-freescale**（如果手机性能较弱，ScaleFX 的多 pass 略卡，可退回 xBRZ 单 pass 方案）。

---

## 执行步骤

### 第一步：拉取子模块

```bash
git submodule update --init --recursive
```

确保 `3rd/SDL` 等依赖就位。

### 第二步：准备游戏资源

1. 从 Steam 购买《仙剑奇侠传》（或使用已有的正版光盘数据）
2. 将游戏数据文件准备好（后续会传到模拟器/手机中）
3. 所有文件名需为小写

### 第三步：下载高清 Shader

从 [libretro/glsl-shaders](https://github.com/libretro/glsl-shaders) 下载：

**首选 — ScaleFX：**
- `scalefx/` 目录下的全部 `.glsl` 和 `.glslp` 文件

**备选 — xBRZ：**
- `xbrz/` 目录下的 `xbrz-freescale.glsl` 和 `.glslp` 文件

将 shader 文件放入项目 `shaders/` 目录。

### 第四步：优化默认配置

修改 `android/app/src/main/cpp/pal_config.h`，将默认纹理分辨率提高到适配手机屏幕：

```c
#define PAL_DEFAULT_TEXTURE_WIDTH   1920
#define PAL_DEFAULT_TEXTURE_HEIGHT  1200
```

当前默认值为 960×720，提高后 shader 输出画质更好。

### 第五步：构建 APK 并在模拟器验证

1. 用 Android Studio 打开 `android/` 目录
2. 处理符号链接：确认 `android/app/src/main/java/org/libsdl/app` 正确链接到 `3rd/SDL/android-project/app/src/main/java/org/libsdl/app`
3. 点击 Build → Make Project
4. **选择 Android 模拟器运行**（建议 Pixel 设备，API 30+，开启 GPU 硬件加速）
5. 将游戏数据文件推送到模拟器：
   ```bash
   adb push <游戏数据目录>/* /sdcard/sdlpal/
   ```
6. 首次启动进入设置界面，配置：
   - **游戏资源路径**：`/sdcard/sdlpal/`
   - **Enable GLSL**：开启
   - **Enable HDR**：开启
   - **Shader**：指向 scalefx.glslp（或 xbrz-freescale.glslp）
   - **Texture Width**：1920
   - **Texture Height**：1200
   - **Keep Aspect Ratio**：开启
7. 保存配置，验证效果

### 第六步：安装到真机

模拟器验证通过后，Build → Generate Signed APK，安装到手机。

---

## 预期效果

320×200 原始画面 → ScaleFX 多 pass 智能放大到 1920×1200 → HDR 色彩增强 → 全屏输出。

像素边缘平滑自然，接近手绘效果，色彩更丰富，在手机高分屏上获得清晰的"高清"体验。
