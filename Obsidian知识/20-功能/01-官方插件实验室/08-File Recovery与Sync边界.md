---
type: lesson
stage: 4
status: ready
difficulty: 进阶
estimated_minutes: 20
topics:
  - File recovery
  - Obsidian Sync
  - 备份边界
tags:
  - playground/core-plugins
  - core/file-recovery
  - service/sync
---

# 08 · File Recovery 与 Sync 边界

> [!danger] 三者不是同义词
> File Recovery 是本机快照，Sync 是可选付费同步服务，Backup 是独立、可恢复的副本。任何一个都不能自动等同于另外两个。

## 目标

- 查看 File Recovery 的本机快照设置。
- 理解快照、版本历史、同步与备份的不同职责。
- 准确描述 Sync 核心插件入口与付费服务的关系。
- 在不登录、不连接、不上传的情况下完成边界检查。

## 动手

### 1. 检查 File Recovery

打开“设置 → 核心插件 → File recovery”，观察：

- Snapshot interval
- History length
- View snapshots

官方默认值是快照之间至少 5 分钟，保留 7 天；用户可以修改。新建一篇无敏感内容的 `恢复练习.md`，写入“版本 A”，稍后再改成“版本 B”。无需为课程一直等待；在后续学习中回到 **View snapshots**，观察本机是否已经产生可恢复版本。

> [!danger] 不要点 Clear history
> 清除快照历史是不可逆操作，不属于本课练习。

### 2. 比较四层恢复能力

| 能力 | 保存在哪里 | 是否跨设备 | 主要用途 |
| --- | --- | --- | --- |
| Undo | 当前编辑会话 | 否 | 撤销近期编辑 |
| File Recovery | 当前设备的 Obsidian 全局设置 | 否 | 恢复 `.md` / `.canvas` 的本机快照 |
| Sync version history | Obsidian Sync 远程服务 | 是，需订阅 | 查看和恢复有限保留期的远程版本 |
| 独立 Backup | 你选择的独立介质或系统 | 取决于方案 | 应对误删、损坏、设备丢失和同步传播 |

### 3. 只检查 Sync 入口，不连接

Sync 出现在核心插件列表中，因为客户端入口随应用附带；真正的 Obsidian Sync 是付费 add-on service。

本课只阅读 [Obsidian Sync 官方介绍](https://obsidian.md/help/sync)，不要：

- 登录或购买订阅
- 创建 remote vault
- 选择远程 vault
- 点击 Start Syncing
- 把当前 Vault 同时交给多套同步服务

如果未来选择使用 Sync，顺序应是：先做独立备份，再确认当前 Vault 不被 iCloud、Dropbox、OneDrive 等另一套同步系统同时管理，然后设置 selective sync，最后才连接远程 Vault。

### 4. 写下自己的恢复策略

补完这句话：

> 我的实时同步方案是 ______；我的独立备份在 ______；我会用 ______ 验证备份真的能够恢复。

## 成功标准

- [ ] 我看到了 File Recovery 的 interval、history length 和 snapshots
- [ ] 我知道 File Recovery 快照不会通过 Sync 传到其他设备
- [ ] 我能解释 Sync 核心插件入口与付费服务的区别
- [ ] 我没有登录、连接或上传任何数据
- [ ] 我能指出自己独立备份的位置和恢复验证方法

## 限制与边界

- File Recovery 不是完整备份；快照有保留期限。
- File Recovery 只能恢复 `.md` 与 `.canvas`，且快照与设备及原路径相关。
- File Recovery 快照不会通过 Sync 同步。
- Sync 会传播创建、修改和删除，因此“所有设备都一样”不等于“有独立备份”。
- 不要让同一 Vault 同时由 Obsidian Sync 与 iCloud、Dropbox、OneDrive 等多套系统管理。
- 新远程 Vault 可使用端到端加密；加密密码丢失时 Obsidian 无法替你恢复。
- Sync 的端到端加密保护远程 Vault 和传输，不会自动加密本地 Vault。
- 套餐、容量、文件上限和版本保留期会变化，应查看实时官方页面。

## 官方文档链接

- [File recovery](https://obsidian.md/help/plugins/file-recovery)
- [Introduction to Obsidian Sync](https://obsidian.md/help/sync)
- [Sync security and privacy](https://obsidian.md/help/sync/security)
- [Back up your Obsidian files](https://obsidian.md/help/backup)
- [Current pricing](https://obsidian.md/pricing)

---

**上一站**：[[Obsidian知识/20-功能/01-官方插件实验室/07-Note Composer-Outline与Word Count|07-Note Composer-Outline与Word Count]] · **下一站**：[[Obsidian知识/20-功能/01-官方插件实验室/09-Web Viewer|09-Web Viewer]] · **返回 MOC**：[[Obsidian知识/20-功能/01-官方插件实验室/00-官方插件实验室-MOC|00-官方插件实验室-MOC]]
