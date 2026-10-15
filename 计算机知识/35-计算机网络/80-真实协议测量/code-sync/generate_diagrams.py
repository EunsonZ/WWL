from pathlib import Path

OUT = Path(__file__).parents[1] / "_assets"
OUT.mkdir(exist_ok=True)
diagrams = {
 "framing.svg": '''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="220"><rect width="100%" height="100%" fill="#ffffff"/><style>text{font:16px sans-serif;fill:#172033}.b{fill:#e8f1ff;stroke:#173b73}</style><text x="20" y="28">一个可能的 API 返回切片；不是实测 TCP 分段</text><rect class="b" x="25" y="60" width="130" height="45"/><text x="45" y="88">recv #1: H</text><rect class="b" x="170" y="60" width="220" height="45"/><text x="190" y="88">recv #2: ello世</text><rect class="b" x="405" y="60" width="180" height="45"/><text x="425" y="88">recv #3: 界</text><path d="M25 145h560" stroke="#173b73"/><text x="25" y="180">应用规则：Content-Length=11（UTF-8 字节）→ 缓冲到 11 才交付</text></svg>''',
 "states.svg": '''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="245"><rect width="100%" height="100%" fill="#ffffff"/><style>text{font:16px sans-serif;fill:#172033}.b{fill:#edf9ef;stroke:#1d6b45}</style><text x="20" y="28">一次读取结果必须按 API 状态解释</text><rect class="b" x="30" y="65" width="170" height="55"/><text x="55" y="98">bytes &gt; 0</text><rect class="b" x="255" y="65" width="170" height="55"/><text x="310" y="98">b'' (EOF)</text><rect class="b" x="480" y="65" width="170" height="55"/><text x="520" y="98">timeout</text><path d="M115 120v42m225-42v42m225-42v42" stroke="#1d6b45"/><text x="25" y="195">继续累积；够帧才完成</text><text x="235" y="195">完整帧？正常结束；否则截断</text><text x="470" y="195">本次等待无结果；业务状态未知</text></svg>'''
}
for name, content in diagrams.items(): (OUT / name).write_text(content, encoding="utf-8")
