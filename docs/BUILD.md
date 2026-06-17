# Tauri 打包说明（Windows）

> 本文档说明如何在 Windows 上把"个人 AI 知识库"前端打成 `.msi` / `.exe` 安装包。

## ✅ 一键打包（推荐）

```powershell
cd windows-client
.\build.ps1
```

脚本会自动：
1. 检查 Rust / Node 是否就绪
2. 检查 MSVC BuildTools / Windows SDK 是否就绪
3. `npm install`（首次较慢）
4. `npm run build`（构建前端）
5. `npx tauri build`（打包成 .msi + .exe）

**首次运行需要 30-60 分钟**（下载 200+ 个 Rust crate + 编译）。

## 📦 产物位置

打包成功后，产物在：
```
windows-client\src-tauri\target\release\bundle\
├── msi\知识库_0.1.0_x64_en-US.msi          ← Windows 安装包（推荐）
└── nsis\知识库_0.1.0_x64-setup.exe         ← NSIS 安装包（备选）
```

**体积**：~10-15 MB（WebView2 在 Win10 1803+ / Win11 自带）。

## 🔧 打包前置条件

### 1. Node.js 18+（必装）
- 下载：https://nodejs.org/
- 装完验证：`node --version`

### 2. Rust 工具链（必装）
- 下载安装：https://rustup.rs/
- 装完验证：
  ```powershell
  rustc --version
  cargo --version
  ```

### 3. MSVC 编译器（必装，**最容易遗漏**）
Tauri 2 在 Windows 上必须用 MSVC 链接，**没有 VS BuildTools 就 build 不出 .exe**。

#### 推荐：VS BuildTools 2022
- 下载：https://aka.ms/vs/17/release/vs_buildtools.exe （4.4 MB 引导器）
- 静默安装（约 1.5 GB）：
  ```powershell
  # 装到默认位置 C:\BuildTools
  vs_buildtools.exe --quiet --wait --norestart --nocache `
    --add Microsoft.VisualStudio.Workload.VCTools `
    --installPath "C:\BuildTools"
  ```
- **也可以图形安装**（更直观）：双击 → 选"C++ 桌面开发"工作负载 → 安装

#### 验证
```powershell
"C:\BuildTools\VC\Tools\MSVC\<版本号>\bin\Hostx64\x64\cl.exe" 2>&1 | findstr "Compiler"
"C:\BuildTools\VC\Auxiliary\Build\Microsoft.VCToolsVersion.default.txt"
"C:\Program Files (x86)\Windows Kits\10\Include\<sdk版本>\ucrt\corecrt.h"
```

如果三项都在 → ✅ 可以开始打包。

### 4. WebView2 Runtime（一般已自带）
- Win 10 1803+ / Win 11 必带
- 老系统装：https://developer.microsoft.com/microsoft-edge/webview2/

## 🚀 手工打包（不用脚本）

```powershell
cd windows-client
npm install
npm run build         # 构建前端到 dist/
npx tauri build       # Tauri 读 dist/，打 .msi
```

## 🌐 跨平台

同样代码可以打 macOS / Linux：
```bash
# macOS ARM
npx tauri build --target aarch64-apple-darwin
# Linux
npx tauri build --target x86_64-unknown-linux-gnu
```

需要对应平台的 Rust 工具链：`rustup target add <target>`。

## 🐛 常见打包问题

### 1. `error: linker 'link.exe' not found`
没装 MSVC。回到上面"3. MSVC 编译器"一节。

### 2. `error: failed to run custom build command for openssl-sys`
Rust 默认用 vendored OpenSSL 慢。改 `src-tauri/Cargo.toml`：
```toml
[dependencies]
tauri = { version = "2.1", features = [] }
```
然后：
```bash
cd src-tauri
cargo clean
npx tauri build
```

### 3. WebView2 找不到
Win10 1803+ 自带，Win11 必带。老系统去微软下载。

### 4. 杀毒软件误报
Tauri 打的 exe 偶尔被 Windows Defender / 火绒误报。
- 加白名单
- 或代码签名（高级，付费证书）

### 5. 体积太大
`Cargo.toml` release profile 已经优化过（LTO + strip + opt-level=s）。
想更小：去掉 `tauri-plugin-shell` 等不用的 plugin。

## 🔄 自动更新（可选）

Tauri 2 自带 `tauri-plugin-updater`，需要：
- 自己搭更新服务（或用 GitHub Releases）
- 每次发版：build → 上传 .msi / .nsis 到 releases → 用户自动收更新提示

简单方案：每次发版让用户重装 .msi。

## 📋 配置说明

主要配置文件：
- `src-tauri/tauri.conf.json` — 窗口大小、icon、bundle 目标
- `src-tauri/Cargo.toml` — Rust 依赖 + release profile
- `src-tauri/capabilities/default.json` — Tauri 权限（默认 `core:default`）

修改 `tauri.conf.json` 后必须重启 `npx tauri build`（热重载不感知）。
