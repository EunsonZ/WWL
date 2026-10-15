"""重绘 PostgreSQL 时间线；输出到图源所在目录，不接触数据库。
需要已有 matplotlib；默认解析中文字体族 Heiti TC，可显式传 --font-file。
同版本 matplotlib 与同一字体下，SVG 去除时间元数据并稳定 ID/行尾。
"""
from pathlib import Path
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.font_manager import FontProperties, findfont


def render(font, preview_dir=None):
    base = Path(__file__).resolve().parent
    matplotlib.rcParams['svg.fonttype'] = 'path'
    matplotlib.rcParams['svg.hashsalt'] = 'wwl-postgres-timelines-v1'

    def figure(name, title, headers, rows, footer):
        width, height = 1120, 180 + len(rows) * 85
        fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
        try:
            fig.patch.set_facecolor('#f5f7fb')
            ax.set_position([0, 0, 1, 1])
            ax.set_xlim(0, width)
            ax.set_ylim(height, 0)
            ax.axis('off')

            def text(x, y, value, size):
                ax.text(x, y, value, fontproperties=font, fontsize=size,
                        color='#17243b', va='center')

            text(30, 36, title, 19)
            for column, value in enumerate(headers):
                text(30 + column * 360, 78, value, 13)
            for row, values in enumerate(rows):
                y = 104 + row * 85
                for column, value in enumerate(values):
                    ax.add_patch(FancyBboxPatch(
                        (20 + column * 360, y), 345, 70,
                        boxstyle='round,pad=0,rounding_size=9', linewidth=0,
                        facecolor=['#dceaff', '#e7e1ff', '#ddf2e7'][column]))
                    for line, value_line in enumerate(value.split('\n')):
                        text(32 + column * 360, y + 24 + line * 25, value_line, 13)
            text(30, height - 24, footer, 11)
            output = base / name
            fig.savefig(output, format='svg', metadata={'Date': None})
            # 只去除行尾空格/Tab；保留SVG文字和几何信息。
            output.write_text('\n'.join(line.rstrip(' \t')
                              for line in output.read_text().splitlines()) + '\n')
            if preview_dir is not None:
                preview_dir.mkdir(parents=True, exist_ok=True)
                fig.savefig(preview_dir / (Path(name).stem + '.png'))
        finally:
            plt.close(fig)

    figure('postgres-duty-timeline.svg','同一交错：RR 两笔成功；Serializable 第二笔被拒绝',
     ['步骤（由上往下）','会话 A / 医生 1','会话 B / 医生 2'],[
     ('1 · 两笔事务开始','BEGIN；读 count = 2','BEGIN；读 count = 2'),
     ('2 · A 修改并提交','医生 1 → 离岗；COMMIT','仍持有读到 2 的旧快照'),
     ('3 · B 用旧判断写','A 已成功提交','医生 2 → 离岗；尝试 COMMIT'),
     ('4 · 隔离级别分叉','RR：最终 count = 0','Serializable：SQLSTATE 40001'),
     ('5 · 全事务重试（Serializable）','医生 1 离岗，医生 2 在岗','ROLLBACK → BEGIN → 读 1\n取消离岗；COMMIT；count = 1')],
     '计数单位：人；两笔并发事务在各自第一次读时固定快照。错误可能在 UPDATE 或 COMMIT。')
    figure('postgres-recovery-timeline.svg','进程中断前后的三个观察者：同一张 durable 表',
     ['阶段（由上往下）','已提交状态 / 新会话观察','会话 B 自己看到的未提交状态'],[
     ('1 · 建表，CHECKPOINT','id 1 = 0；id 2 = 0','尚未开始'),
     ('2 · A 更新并 COMMIT','id 1 = 10；id 2 = 0','尚未开始'),
     ('3 · B BEGIN，更新两行','A 仍读到 (10, 0)','B 自己读到 (99, 20)；无 COMMIT'),
     ('4 · 自有集群 immediate stop','连接终止；无正常关闭检查点','B 没有提交确认'),
     ('5 · 同数据目录重启','新会话读到 (10, 0)','未提交版本不成为可见业务状态')],
     'server.log：database system was interrupted → redo starts at → redo done at。进程中断 ≠ 断电。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-family', default='Heiti TC', help='已有中文字体族')
    parser.add_argument('--font-file', type=Path, help='可选：已有中文字体文件')
    parser.add_argument('--preview-dir', type=Path, help='可选：库外PNG预览目录')
    args = parser.parse_args()
    if args.font_file is not None:
        if not args.font_file.is_file():
            parser.error('--font-file 必须指向已有字体文件')
        font_file = args.font_file
    else:
        font_file = findfont(FontProperties(family=args.font_family),
                             fallback_to_default=False)
    render(FontProperties(fname=str(font_file)), args.preview_dir)


if __name__ == '__main__':
    main()
