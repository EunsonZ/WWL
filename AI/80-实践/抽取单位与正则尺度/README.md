---
type: lab
aliases: []
sources:
  - "https://www.dsprelated.com/freebooks/sasp/Downsampling_Aliasing.html"
prerequisites:
  - "[[AI/15-卷积神经网络/05-采样混叠感受野与平移鲁棒性#同一数组怎样把时间频率折到空间频率]]"
---
# 抽取共同数组：单位、增益与非线性顺序

主解释见[[AI/15-卷积神经网络/05-采样混叠感受野与平移鲁棒性#同一数组怎样把时间频率折到空间频率|CNN采样页]]。同一序列可解释成时间样本或各行重复的空间特征图，单位换算在正文完成。脚本只核数组和频响，不训练模型、不播放音频、不读取外部文件或网络；使用Python标准库，输入从同目录JSON读取、输出只到标准输出。

## 固定输入与执行接口

[aliasing_inputs.json](aliasing_inputs.json) 固定24点。这是8点周期与6点周期的共同整数周期，使用周期边界；不把它当任意有限记录的理想砖墙滤波器。两倍抽取保留相位0。

```bash
python3 -B aliasing.py
python3 -B aliasing.py | python3 -B verify_aliasing.py
```

[aliasing.py](aliasing.py) 直接算余弦数组、两点均值的复频响，并以完整周期DFT严格保留 $|\omega|<\pi/2$ 的bin，比较滤波/平方顺序。[verify_aliasing.py](verify_aliasing.py) 不导入实现，用根式、已推导周期表和DC值核对，绝对容差 `1e-11`。预期抽取共同周期 `[1,0,-1,0]`，增益约 `.923880,.382683,0`；平方后直接抽取或先滤输入再平方抽取得 `[1,.25,.25]`，平方后低通再抽取为常量 `.5`。

该有限周期核对不证明所有整数恒等式；全网格证明由正文三角恒等式承担。改变相位、有限记录边界或周期长度时，要独立推导新预期，不直接修改答案掩盖失配。两点均值的带外残留不意味着所有滤波器组都不可逆；本例没有实现多子带重建。

源码和静态检查不等于已运行。实际执行输出、非作者论证审阅、Obsidian导航显示、真实CNN/设备结果与真人理解分别记录。

## 规范源码与输入镜像

以下镜像只供离线阅读与逐字核对；规范文件在同目录。执行层由固定来源的独立复算另行记录。

<!-- code-sync: ./aliasing.py -->
```python
"""Periodic finite-array checks of the stated infinite-grid examples."""
import cmath
import json
import math
from pathlib import Path


def ideal_lowpass_periodic(samples):
    """Keep periodic DFT bins strictly inside |omega| < pi/2."""
    n = len(samples)
    spectrum = [sum(x*cmath.exp(-2j*math.pi*k*t/n) for t,x in enumerate(samples))
                for k in range(n)]
    kept = [v if abs(k if k <= n//2 else k-n) < n/4 else 0j
            for k,v in enumerate(spectrum)]
    return [sum(v*cmath.exp(2j*math.pi*k*t/n) for k,v in enumerate(kept)).real/n
            for t in range(n)]


def calculate(config):
    n = config['period_samples']
    if type(n) is not int or n <= 0 or n % 24 or n > 240:
        raise ValueError('Use a positive multiple of 24, at most 240.')
    low = [math.cos(math.pi*t/4) for t in range(n)]
    high = [math.cos(3*math.pi*t/4) for t in range(n)]
    original = [math.cos(math.pi*t/3) for t in range(n)]
    squared = [x*x for x in original]
    prefiltered = ideal_lowpass_periodic(original)
    gains = [abs((1+cmath.exp(-1j*w))/2) for w in (math.pi/4,3*math.pi/4,math.pi)]
    return {'low_first_eight': low[:8], 'high_first_eight': high[:8],
            'low_downsampled': low[::2], 'high_downsampled': high[::2],
            'gains': gains, 'square_downsampled': squared[::2],
            'filter_square_downsampled': [x*x for x in prefiltered][::2],
            'square_filter_downsampled': ideal_lowpass_periodic(squared)[::2]}


if __name__ == '__main__':
    config=json.loads(Path(__file__).with_name('aliasing_inputs.json').read_text())
    print(json.dumps(calculate(config),indent=2))
```

<!-- code-sync: ./aliasing_inputs.json -->
```json
{
  "period_samples": 24
}
```

<!-- code-sync: ./verify_aliasing.py -->
```python
"""Algebraic-value and period-table oracle; imports no aliasing implementation."""
import json
import math
import sys


def check(actual, expected):
    assert len(actual) == len(expected)
    for i,(a,b) in enumerate(zip(actual,expected)):
        assert math.isfinite(a) and abs(a-b) <= 1e-11, (i,a,b)


if __name__ == '__main__':
    data=json.load(sys.stdin)
    a=math.sqrt(2)/2
    check(data['low_first_eight'],[1,a,0,-a,-1,-a,0,a])
    check(data['high_first_eight'],[1,-a,0,a,-1,a,0,-a])
    check(data['low_downsampled'],[1,0,-1,0]*3)
    check(data['high_downsampled'],[1,0,-1,0]*3)
    check(data['gains'],[math.sqrt(2+math.sqrt(2))/2,math.sqrt(2-math.sqrt(2))/2,0])
    check(data['square_downsampled'],[1,1/4,1/4]*4)
    check(data['filter_square_downsampled'],[1,1/4,1/4]*4)
    check(data['square_filter_downsampled'],[1/2]*12)
    print('PASS: shared samples, gain radicals, and nonlinear/filter ordering')
```


## 2026-10-10 的实际独立执行

本固定24点周期数组已由独立执行者运行；业务CLI、作者供件verify及外部oracle均退出0。相位0共同数组、两个增益和平方/滤波顺序与独立解析表相符，最大浮点差约4.22×10⁻¹⁵，小于1e−11。外部oracle另核相位1、因果均值的幅相和周期/零延拓边界；作者verify仍属于供件自检，不冒充独立审阅。原输出、运行前预期、环境/命令、源码身份及新空目录复建在 [[AI/80-实践/抽取单位与正则尺度/results/2026-10-10/r1/README|实际结果入口]]。本有限观察不证明全部整数恒等式、全带抗混叠、训练后CNN效果、客户端显示或真人理解。
