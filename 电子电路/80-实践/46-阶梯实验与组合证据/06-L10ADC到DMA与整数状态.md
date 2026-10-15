---
type: lab
domain: electronics
stage: 3
content_status: usable
evidence_status: partial
aliases: []
sources: []
prerequisites:
  - "[[电子电路/44-嵌入式采集与控制/01-电压编码校准与数据契约#块与算法状态]]"
  - "[[电子电路/44-嵌入式采集与控制/03-定时中断DMA与实时预算#从块周期推出最坏预算]]"
---
# L10：怎样从一个电压样本追到一个及时且有状态的输出

基础入口画出第0点0ms采样到第一块6.3ms处理完成；快进入口用整数码、有限事件和独立有理数核同一链。问题是：滤波数字正确，但数据已被覆盖或索引删去了，结果还代表原物理输入吗？

## 固定单位与输入合同

理想12bit、Vref3.3V、Ts1ms，Δ=3.3/4096=.8056640625mV。32点有限输入v[n]=1.65+4nΔ，n0…31，对应codes2048+4n，t[n]=nms。floor分箱定义来自 [[电子电路/44-嵌入式采集与控制/01-电压编码校准与数据契约#编码区间先于重建电压]]：每码只给区间，midpoint不是实测。3.3V特殊末码标端点，bool/complex/NaN/越界拒绝；本例名义尺度而非四点校准，输出参考明确是1.65V。

将q=c−2048作为有符号count；FIR=round_even((q[n]+2q[n−1]+q[n−2])/4)，IIR=round_even((3y[n−1]+q[n])/4)。IIR初值0，FIR前两点缺历史invalid。输入0,4,8,12count给FIR0,1,4,8，IIR0,1,3,5；最后乘Δ得到V偏差，不能先转V再减2048。

## 时间戳与所有权同时核对

B4双槽、IRQ最坏J.3ms、处理C2ms。块k的ready=(k+1)4ms、start=max(ready+J,前finish)、finish=start+C、reuse=(k+2)4ms。第一块样本0/1/2/3ms，ready4ms、IRQ4.3ms、finish6.3ms、reuse8ms，slack1.7ms；首点年龄6.3ms、末点3.3ms。输出完成并不证明DAC/PWM已经在该时刻施加。

![[电子电路/80-实践/30-采集DMA与闭环/assets/04-timeline.svg]]

`pipeline_lab.py` 调用正式OwnedRing、CountFilter、schedule、adc。先完整校验32样本，再publish(t=(epoch,generation,slot))→take→process→release，payload不可被旧token释放。跨块不重置历史；异常gap/epoch在状态改变前拒绝。software Ring不使真实循环DMA自动暂停，cache可见性、硬件停止和平台屏障沿 [[电子电路/44-嵌入式采集与控制/03-定时中断DMA与实时预算#内存可见性与 cache 是另一个合同]] 的独立合同。

## 执行、可核输出与失败

```bash
.venv/bin/python -B '电子电路/80-实践/46-阶梯实验与组合证据/pipeline_lab.py' --vault . --output /private/tmp/L10-chain-new
.venv/bin/python -B -m unittest discover -s '电子电路/80-实践/46-阶梯实验与组合证据' -p test_pipeline_lab.py -v
```

L10-pipeline.csv含input_V、code、capture_ns、finish_ns、FIR_count/IIR_count、FIR_valid和output_deviation_V，status=CPU_result_only。第3点c2060，IIR5count、偏差4.0283203125mV。固定4+4…块与独立全历史有理数/一次ties-even应逐点一致。q范围−2048…2047，这个正权平均模型无额外整数溢出；它不是任意Q系数滤波器的稳定或溢出保证。

改C5ms，首块finish9.3ms超过reuse8ms；所有八块discard，连接器不产生伪有效滤波数。它仍记录真实物理索引；丢块后如果以后恢复，须明确换epoch/origin/暖机，不能给后续旧索引重新编号。当前有限反例全部discard，不宣称模型已经实现任意交错恢复。原正式 [[电子电路/80-实践/30-采集DMA与闭环/README#运行与输出]] 还能独立生成其校准管线，但该校准参考1.6487904V不同，不能把本卡名义尺度混进它的结果。

## 四题与理由

1. C4ms、J.3ms，服务率等于到达率是否安全？**否。** 首块finish8.3ms已越reuse；一般f_k递推还要纳入IRQ/积压。增加容量能推迟失败，不能凭平均吞吐证明deadline。
2. 在块边界重置IIR为0，后块是否等价整段？**不等价。** 原状态承载先前输入，须跨块保存；显式系统复位可重置但要改epoch和解释。
3. 丢去4点后把后块start_index减4，什么被改变？**物理时间和递归模型。** Ts固定时缺测时刻被悄悄压缩；应拒gap或明确缺测模型。
4. 若CPUfloat输出越3.3V而整数码仍合法，能直接输出执行器吗？**不能。** 数值输出需要幅度/参考/限幅与保持时刻合同；本例有限平均在输入码域内，其他增益/控制不享有此结论。

实际CPU连接与8独立组合检查通过；真实ADC、DMA驱动、cache、中断最坏上界、DAC/PWM、固定点硬件和真人阅读未执行。不能把CPU CSV视为示波器采样。
