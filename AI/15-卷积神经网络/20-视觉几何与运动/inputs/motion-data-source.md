---
type: reference
aliases:
  - 像素运动实验数据出处
sources:
  - https://scikit-image.org/docs/0.25.x/api/skimage.data.html#skimage.data.camera
---

# 像素材料的出处与生成边界

`camera.png` 是scikit-image v0.25.2保存的512×512灰度真实照片。官方该版本文档明确摄影者Lav Varshney以CC0提供，并说明0.18替换了更早的版权不明文件；不能用新版许可为任意旧同名“cameraman”图背书。本文件经GitHub内容API核对后从该tag下载，保留原始PNG，没有重编码。

- [固定提交中的原文件](https://github.com/scikit-image/scikit-image/blob/e8a42ba85aaf5fd9322ef9ca51bc21063b22fcae/skimage/data/camera.png)：v0.25.2 tag指向commit `e8a42ba85aaf5fd9322ef9ca51bc21063b22fcae`。
- 原文件139512 bytes，Git blob `cdb3405d0086639638a13a2c72bfb646060180e2`；本地按Git blob格式独立重算一致。
- 原PNG SHA256 `b0793d2adda0fa6ae899c03989482bff9a42d3d5690fc7e3648f2795d730c23a`。
- [版本化官方许可说明](https://scikit-image.org/docs/0.25.x/api/skimage.data.html#skimage.data.camera)，读取日期2026-10-17。这里只保留小数据所需出处，不下载整个数据集或安装scikit-image。

`photo-pair.npy` 是 `flow_lab.photo_case` 从这个原PNG生成的两个128×192 float64灰度数组：裁剪左上角原图(v=128,u=128)，高斯σ1.2px，第二张由第一张双线性人工平移(u=1.25,v=-.75)px，生成阶段使用夹取边界延拓。跟踪器自身禁止越界采样。照片纹理是真实的，位移、重采样、曝光不变和两帧关系是指定模型，不是一次真实时间采集。

`motion-pixels.npy` 是 `flow_lab.scene` 按 `motion-spec.json` 生成的 `(T=5,eye=2,H=128,W=192)` float32灰度数组，只有12个静态正对相机的平面纹理块。第j块纹理按相对投影中心的像素坐标dx/dy计算：

$$
.45+.17\sin(.39dx+.17dy+.43j)+.16\cos(-.23dx+.41dy+.27j)+.09\sin(.13dx-.27dy+.61j).
$$

支撑域 $|dx|,|dy|\le12$ px，背景.08；默认块不重叠，没有可见性排序或真实相机模型。每块深度固定，同一纹理由给定f和深度对应一块静态物理平面；限定为相机只侧向平移且旋转真值I；源码拒绝非零Z平移，不把缺少纹理深度缩放的图当成静态物理场景，因此成像是本地平移。所有位置仍由已有01 `project`计算，不是预先给跟踪器写答案。真值像素仅用于评价，跟踪器只读灰度图和给定初始种子；真实照片的种子则由实际结构张量检测器得到。

`flow-results.json` 保存全部真投影、真实逐像素跟踪值与逐点停止/残差记录。`window-ba-results.json` 进一步保存独立高斯坐标误差、每条观测的原始像素来源ID与被指派地图ID、初值、预测/残差和最后参数。噪声seed29、σ.12px固定，错误回环只是控制变量的身份置换，未冒称实际识别结果。

本实验全部可在本机CPU复建，不下载视频、不采集相机、不运行真实实体回环，也未对照片中的人或物体作身份识别。
