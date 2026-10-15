# 补充 H2 标签勘误

原执行 executor_oracle.py 和 expected-before-output.json 的 full_H2_seminorm_on_sector_annulus 字段实际计算扇形环带上的积分 ∫|D²w|_F² dx。按此处 Hessian Frobenius 约定，|D²w|_F² = w_xx² + 2w_xy² + w_yy²；该积分是二阶半范数的平方。半范数本身应取平方根。正确的语义字段名为 squared_H2_seminorm_on_sector_annulus。

固定 alpha=2/3 的系数 2alpha²(alpha-1)²=8/81；完整平方量是原径向因子乘扇形角度3pi/2及8/81。原cutoff .1/.01/.001对应所记数值约1.4812586559、13.2816098932、68.0539884289均按平方量解释。这里采用 Frobenius convention；不能无说明改成只计一次混合导数的多指标半范数约定。

这是一项表达勘误。原两份候选 stdout、独立 oracle 原 stdout/stderr、原执行driver、expected-before-output.json及冻结source inputs保持原字节，不重新签作新字段执行。没有生成修正driver或数值重跑。原artifact-manifest绑定勘误前包；新增勘误与README变更由ERRATUM-receipt.json单独记录。一般H0¹、弱式与Hessian不可积证明由review209pdecomplex独核，本补证仍只是有限公式复算。
