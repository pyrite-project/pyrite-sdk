import re
from typing import List

class Map:
    def __init__(self, **kws):
        self.data = kws

    def __getitem__(self, key):
        return self.data[key]

    def to_string(self):
        result = [f"{k}: {v}" for k, v in self.data.items()]
        return ", ".join(result)

class Parser:
    def __init__(self):
        # 组1 (Escaped): \\(.) -> 匹配 \ 后跟任意字符
        # 组2 (Variable): \$\[(.*?)\] -> 匹配 $[...]
        # 组3 (Literal): ([^\\$]+|. ) -> 匹配不含 \ 和 $ 的文本，或者兜底的单个字符
        self._pattern = re.compile(r'\\(.)|\$\[(.*?)\]|([^\\$]+|.)')

    def parse_string(self, text: str) -> List[str]:
        """
        解析模板字符串
        """

        tokens = []
        for match in self._pattern.finditer(text):
            esc, var, lit = match.groups()

            if esc:
                # 处理转义：如 \\ -> \, \$ -> $
                # 转义字符通常被视为普通文本的一部分
                tokens.append(f'"{esc}"')
            elif var:
                # 处理变量：$[xxx] -> xxx
                tokens.append(var)
            elif lit:
                # 处理普通文本
                tokens.append(f'"{lit}"')

        # 合并连续的字符串部分
        return self.merge_literals(tokens)

    def merge_literals(self, tokens: List[str]) -> List[str]:
        if not tokens: return []
        res = []
        current_lit = []

        for t in tokens:
            if t.startswith('"') and t.endswith('"'):
                current_lit.append(t[1:-1])
            else:
                if current_lit:
                    res.append(f'"{ "".join(current_lit) }"')
                    current_lit = []
                res.append(t)
        if current_lit:
            res.append(f'"{ "".join(current_lit) }"')
        return res

    def parse_map(self, map: Map) -> Map:
        data = {}
        for key, value in map.data.items():
            data[key] = self.parse_string(value)
        return Map(**data)

    def parse(self, data) -> str | Map:
        if isinstance(data, str):
            return self.parse_string(data)
        elif isinstance(data, Map):
            return self.parse_map(data)
        raise TypeError("Unknown data type in Parse.")

parser = Parser()
parse = parser.parse

def raw(n: str):
    n = n.replace("$", "\\$").replace("[", "\\[").replace("]", "\\]")
    return f"$[{n}]"

def arg(n: str):
    return raw(f"args.{n}")

def var(n: str):
    return raw(f"data.{n}")

# print(parse("$[xxx]yyy"))
# print(parse("Hello \\$[world]"))
# print(parse("$[var]\\$[next]"))
# print(parse("A\\\\B$[C]D"))
# print(Map(a="$[xxx]yyy", b="Hi").to_string())
# print(parse(Map(a="$[xxx]yyy", b="Hi")).to_string())