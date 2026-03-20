# 高清仙剑 Android 游玩指南

## 方式一：内置资源 APK（推荐）

安装即玩，无需额外传文件、无需授权存储权限。

### 编译步骤

#### 1. 准备游戏资源

将正版《仙剑奇侠传》数据文件（Steam 版或光盘版）放到 `android/app/src/main/assets/gamedata/`：

```
android/app/src/main/assets/gamedata/
├── 0.rpg, m.msg, word.dat
├── abc.mkf, ball.mkf, data.mkf, f.mkf, fbp.mkf, fire.mkf
├── gop.mkf, map.mkf, mgo.mkf, mus.mkf, pat.mkf
├── rgm.mkf, rng.mkf, sounds.mkf, sss.mkf
├── 1.avi ~ 6.avi（过场动画，可选）
├── scalefx.glslp
└── shaders/
    └── scalefx-pass0.glsl ~ scalefx-pass4.glsl
```

**所有文件名必须小写。** Shader 文件从项目 `shaders/` 目录复制：

```bash
mkdir -p android/app/src/main/assets/gamedata/shaders
cp shaders/scalefx.glslp android/app/src/main/assets/gamedata/
cp shaders/scalefx/*.glsl android/app/src/main/assets/gamedata/shaders/
```

#### 2. 编译

```bash
git submodule update --init --recursive
cd android
./gradlew assembleDebug
```

生成的 APK 位于 `android/app/build/outputs/apk/debug/app-debug.apk`（约 237MB）。

#### 3. 安装并游玩

把 APK 传到手机安装，打开即可直接进入游戏。

首次启动会自动解压资源到 App 私有目录并写入默认高清配置（ScaleFX shader + 1920×1200）。

---

## 方式二：外部资源

APK 不含游戏资源，需要手动传文件到手机。适合不想把资源打包进 APK 的情况。

### 步骤

1. 编译不含资源的 APK（不放文件到 `assets/gamedata/` 即可）
2. 安装 APK 后，将游戏资源和 shader 文件复制到手机内部存储的 `sdlpal` 文件夹
3. 打开 App，在文件选择器中选择 `sdlpal` 文件夹
4. 在设置界面开启 **Enable GLSL**，设置 **Texture Width** = `1920`，**Texture Height** = `1200`
5. 点击 **FINISH** 启动游戏

> ⚠️ Android 10+ 的 Scoped Storage 限制可能导致存储权限问题，需要通过 `adb shell pm grant` 手动授权。

---

## 高清效果说明

| 项目 | 说明 |
|------|------|
| 游戏画面 | 320×200 → ScaleFX 5-pass 智能放大至 1920×1200，像素边缘平滑 |
| 过场动画 | AVI 原始视频直接播放，不受 shader 影响 |
| HDR | 开启后色彩更丰富（需 GPU 支持） |
| 性能 | ScaleFX 5-pass 在现代手机上可流畅 60fps |
| ⚠️ 模拟器 | 模拟器软件模拟 GPU 不支持 ScaleFX，开启会花屏，仅真机可用 |

## 操作方式

游戏默认使用触屏虚拟按键：

- **方向键**（左侧）：移动角色
- **A 键**：确认 / 对话
- **B 键**：取消 / 返回
- **X 键**：打开菜单
- **Y 键**：加速

## 故障排除

### 提示 "Cannot find data file"
- 内置资源版：检查 `assets/gamedata/` 目录文件是否齐全后重新编译
- 外部资源版：检查文件名是否全部小写，Android 10+ 需授予存储权限

### 画面花屏
- 模拟器不支持 ScaleFX shader，关闭 GLSL 即可
- 真机上如果花屏，检查 GPU 是否支持 OpenGL ES 3.0+

### 画面黑屏 / 闪退
- 查看日志：`adb logcat | grep -i sdlpal`
