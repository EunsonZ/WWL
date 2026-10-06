---
type: checklist
domain: computer-science
stage: 33
status: ready
difficulty: 进阶
estimated_minutes: 30
topics:
  - Arch Linux
  - 虚拟机
  - 安装
  - 恢复
tags:
  - computer-science/linux
  - computer-science/lab
  - topic/arch-linux
---

# Arch 虚拟机安装检查单

本页不是替代 Arch Installation guide 的命令清单，而是安装过程的停止点和验收表。执行当天先读 [Arch 官方 Installation guide](https://wiki.archlinux.org/title/Installation_guide)，再按 [[计算机知识/20-操作系统/01-Linux/11-ArchLinux安装前规划|安装前规划]]、[[计算机知识/20-操作系统/01-Linux/12-ArchLinux安装实战|安装实战]] 和 [[计算机知识/20-操作系统/01-Linux/13-ArchLinux安装后配置维护与安全|安装后维护]] 操作。

> [!danger] 作用域
> 第一次只在新建虚拟磁盘的 VM 中练习。不要把 `/dev/sda`、`/dev/nvme0n1` 等示例名称复制到实体机；设备名必须由现场只读证据确认。

## VM 创建前

- [ ] 已记录虚拟化平台与版本；
- [ ] VM 固件明确选择 UEFI 或 BIOS；
- [ ] 新建虚拟磁盘，无个人数据；
- [ ] 网络模式已知；
- [ ] 已取得 Arch ISO 并按官方校验和/签名说明验证；
- [ ] 已建立“空磁盘”快照或明确可删除重建 VM；
- [ ] 安装当天已阅读 Arch News 与 Installation guide。

## Live 环境停止点

先证明当前确实是虚拟机，而不是根据设备名猜测：

```bash
systemd-detect-virt --vm
systemd-detect-virt --container
```

第一条必须可用并返回明确的 VM 类型，若输出为空或为 `none` 就停止；第二条应返回 `none`，若输出容器类型就停止。还要在虚拟化平台控制台中读回当前 VM 名称、虚拟磁盘容量/标识和“空磁盘”快照名称。命令不可用、结果不符合上述预期或控制台证据不一致时，**立即停止**：不得进入安装实战的分区与格式化阶段，也不得改用实体机“试一下”。

- [ ] `systemd-detect-virt --vm` 与虚拟化平台记录共同证明当前是预期 VM；
- [ ] 未检测到容器，当前环境是完整 VM；
- [ ] 已在平台控制台读回当前 VM、目标虚拟磁盘和“空磁盘”快照的精确标识；
- [ ] 固件模式与计划一致；
- [ ] 键盘、时间和网络已验证；
- [ ] `lsblk` 中目标虚拟磁盘的容量与型号符合预期；
- [ ] 目标磁盘没有挂载的文件系统；
- [ ] 分区表和挂载方案已经写在记录中；
- [ ] 在任何格式化命令前再次核对设备、分区、容量和用途。

## 安装阶段验收

| 阶段 | 必须观察到的证据 | 失败时 |
| --- | --- | --- |
| 分区与格式化 | 设备树、文件系统类型符合计划 | 停止，不继续 pacstrap |
| 挂载 | 根、ESP 及其他挂载点与计划一致 | 卸载并纠正规划 |
| 基础系统 | pacstrap 完成且无未处理错误 | 保留日志，检查网络/镜像/空间 |
| fstab | UUID 与 `findmnt`/`lsblk -f` 一致 | 在 chroot 前修正 |
| chroot 配置 | 时区、locale、hostname、用户明确 | 逐项验证，不靠记忆 |
| initramfs / microcode | 与 kernel、CPU 和根文件系统方案匹配 | 不急于 reboot，回看日志 |
| bootloader | 能找到 kernel/initramfs 与正确 root | 保留 ISO，准备 chroot 恢复 |

## 第一次重启

- [ ] VM 从虚拟磁盘而不是 ISO 启动；
- [ ] bootloader 可见或按预期直接启动；
- [ ] kernel 找到根文件系统；
- [ ] systemd 到达目标 target；
- [ ] 普通用户可以登录；
- [ ] 网络和 DNS 分别验证；
- [ ] `systemctl --failed` 没有未解释失败；
- [ ] `journalctl -b -p warning` 已审阅而非盲目追求零输出；
- [ ] 建立“首次可启动”VM 快照；
- [ ] 已记录从 ISO 重新进入并 chroot 的恢复路径。

## 故障注入练习

第一次只做固定的“普通用户脚本缺少执行权限”故障，不修改服务、hostname、分区、bootloader、kernel、驱动或系统配置。以普通用户运行：

```bash
fault_dir="$(mktemp -d)"
if [ -n "$fault_dir" ] && [ -d "$fault_dir" ]; then
  fault_script="$fault_dir/run-me.sh"
  printf '%s\n' '#!/bin/sh' 'printf "permission fault repaired\n"' > "$fault_script"
  chmod 600 "$fault_script"

  if "$fault_script"; then
    printf '异常：缺少执行位的脚本竟然运行成功，停止实验\n' >&2
  else
    fault_status="$?"
    printf 'expected non-zero exit=%s\n' "$fault_status"
  fi
  ls -l -- "$fault_script"

  chmod u+x "$fault_script"
  "$fault_script"

  rm -- "$fault_script"
  rmdir -- "$fault_dir"
  test ! -e "$fault_dir" && printf '故障实验已恢复\n'
else
  printf '无法建立故障实验目录；停止实验\n' >&2
fi
```

第一次直接运行应因缺少执行位而失败，并产生非零退出码；`ls -l` 是证据。只增加当前用户执行位后，脚本应打印 `permission fault repaired`。最后逐文件清理且确认临时目录不存在，才算手工恢复完成。再从“首次可启动”快照启动一次，比较：手工修复只改正这个对象，快照恢复会丢弃快照之后的全部 VM 状态。

若 `mktemp -d` 失败、变量为空或路径看不懂，停止，不运行清理命令。不要把这项练习升级为损坏分区表、删除 bootloader、卸载 kernel、随机 blacklist 驱动或修改未知服务。

## 完成标准

- [ ] 我能从固件、bootloader、kernel、initramfs、root、PID 1 六个阶段定位启动失败；
- [ ] 所有设备名都来自当前 VM 的只读证据；
- [ ] 每个写操作前有停止点和预期；
- [ ] 已经成功从 ISO 进入安装系统并验证 chroot 恢复路径；
- [ ] 固定权限故障已用证据定位、手工修复并逐文件清理；
- [ ] VM 快照之外还有课程记录；我知道快照不等于真实数据备份。

---

**上一项**：[[计算机知识/80-实践/02-Linux/02-系统观察与故障定位|系统观察与故障定位]] · **返回实验室**：[[计算机知识/80-实践/02-Linux/00-Linux实验室|Linux 实验室]] · **返回课程**：[[计算机知识/20-操作系统/01-Linux/00-Linux基础-MOC|Linux 基础]]


<!-- revision-2-navigation -->
## 本轮课程定位与机制补充

课程顺序与原稿入口：[[计算机知识/00-开始/课程地图/13-Linux-课程地图|Linux · 课程地图]]。进一步的机制推演与反例：[[计算机知识/20-操作系统/01-Linux/16-服务资源容器与分层故障定位|Linux 深化：服务、资源、容器与分层排障]]。跨学科辨析：[[计算机知识/90-资源/11-跨学科概念辨析|跨学科概念辨析]]。
