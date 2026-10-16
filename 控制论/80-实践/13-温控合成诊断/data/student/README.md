# 温控记录调查

全部为教学合成数据。case-01.csv 至 case-05.csv 为中性编号，编号不提供原因标签。experiment.json 给公开参数。

每行在 t_sample_s 读取 y_K，使用 z_old_K_s 计算 u_cmd_W；status=ok 仅表示在 ack_time_s 收到命令。u_applied_W 是本模型在 [apply_start_s, apply_end_s) 施加的功率；z_next_K_s 供下一拍使用，y_next_K 是 next_sample_time_s 的新读数。

调查任务、单位与判断标准见课程项目的学生入口 README.md。
