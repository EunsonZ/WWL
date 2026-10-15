---
type: lesson
stage: 4
status: ready
difficulty: 入门
estimated_minutes: 12
topics:
  - Web viewer
  - Reader view
  - 网页研究
tags:
  - playground/core-plugins
  - core/web-viewer
  - safety/web
---

# 09 · Web Viewer

> [!warning] 只用公开网页练习
> Web viewer 适合在桌面端快速阅读公开研究资料，但不是主浏览器。不要在其中处理网银、邮箱、密码管理器或其他敏感登录。

## 目标

- 在 Obsidian 标签页中打开一个公开外部链接。
- 使用 Reader view 阅读正文。
- 了解 Save to vault 与 Canvas 网页卡片的衔接。
- 理解社区插件对 Web viewer Cookie 的安全边界。

## 动手

### 1. 打开官方帮助页

使用这个公开链接：[Web viewer 官方帮助](https://obsidian.md/help/plugins/web-viewer)。

在桌面端右键或通过可用命令把它 **Open in Web viewer**。网页会作为 Obsidian 标签页出现，可以：

- 与课程页并排
- 移动到另一个标签组
- 弹出到独立窗口

### 2. 使用 Reader view

点击眼镜图标，切换 Reader view。它使用 Mozilla Readability 清理页面，适合专注阅读，但不保证保留网页全部交互和视觉布局。

### 3. 观察 Save to vault

打开更多操作，找到 **Save to vault**。先观察保存位置和将要创建的内容，再决定是否执行。保存网页得到的是一次抓取结果，不会与原网页持续同步。

### 4. 与 Canvas 联动

回到 [[Obsidian知识/20-功能/01-官方插件实验室/04-Canvas|04-Canvas]] 创建的画布：

1. 加入同一个公开 URL 的网页卡片。
2. 从 Canvas 打开为 Web viewer 标签页。
3. 比较“网页卡片”“Web viewer 标签页”“保存到 Vault 的本地笔记”三种形态。

## 成功标准

- [ ] 我在 Obsidian 内打开了一个公开网页
- [ ] 我切换过 Reader view
- [ ] 我能区分实时网页、Canvas 网页卡片和保存到 Vault 的本地内容
- [ ] 我没有在 Web viewer 中输入敏感凭据
- [ ] 我知道为什么 Web viewer 不能替代主浏览器

## 限制与边界

- Web viewer 只在桌面端提供。
- 它不具备专用浏览器完整的功能、安全控制和扩展生态。
- Reader view 会清理页面，复杂页面可能丢失布局或交互。
- Web viewer 默认阻止广告，也允许配置规则；这不等于完整的隐私或反跟踪方案。
- Obsidian 社区插件不在独立沙箱中运行；当 Obsidian 运行时，第三方插件可访问 Web viewer Cookie。
- 有社区插件的环境中，敏感或需要登录的网站应使用主浏览器。
- Save to vault 创建本地副本，不会让内容自动保持最新。

## 官方文档链接

- [Web viewer](https://obsidian.md/help/plugins/web-viewer)
- [Plugin security](https://obsidian.md/help/plugin-security)
- [Canvas](https://obsidian.md/help/plugins/canvas)
- [Pop-out windows](https://obsidian.md/help/pop-out-windows)

---

**上一站**：[[Obsidian知识/20-功能/01-官方插件实验室/08-File Recovery与Sync边界|08-File Recovery与Sync边界]] · **下一站**：[[Obsidian知识/20-功能/01-官方插件实验室/10-更多核心插件速览|10-更多核心插件速览]] · **返回 MOC**：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]
