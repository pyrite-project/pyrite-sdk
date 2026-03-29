import re
from typing import List

class RFWSerializable:
    def to_rfw(self) -> str:
        raise NotImplementedError()

class DataSerializer(RFWSerializable):
    def __init__(self, data, serialize = True):
        self.data = data
        self.serialize = serialize
        self.serializer = _serialize_value if serialize else lambda v: _serialize_value(v, serialize=False)

    def to_rfw(self) -> str:
        if isinstance(self.data, (list, tuple)):
            return '[' + ', '.join(self.serializer(x) for x in self.data) + ']'
        if isinstance(self.data, dict):
            return '{' + ', '.join(f'{self.serializer(k)}: {self.serializer(v)}' for k, v in self.data.items()) + '}'
        if not self.serialize:
            return str(self.data)
        if isinstance(self.data, RFWSerializable):
            return self.data.to_rfw()
        if isinstance(self.data, str):
            return f'"{self.data}"'
        if isinstance(self.data, bool):
            return 'true' if self.data else 'false'
        if isinstance(self.data, (int, float)):
            return str(self.data)
        raise ValueError(f'Unsupported value type: {type(self.data)}')

def _serialize_value(v, serialize=True):
    return DataSerializer(v, serialize=serialize).to_rfw()

class _Parser:
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
                tokens.append(f'\"{esc}\"')
            elif var:
                # 处理变量：$[xxx] -> xxx
                tokens.append(var)
            elif lit:
                # 处理普通文本
                tokens.append(f'\"{lit}\"')

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
                    res.append(f'\"{ "".join(current_lit) }\"')
                    current_lit = []
                res.append(t)
        if current_lit:
            res.append(f'\"{ "".join(current_lit) }\"')
        return res

    def parse_map(self, map: dict) -> dict:
        data = {}
        for key, value in map.items():
            if not isinstance(value, str): continue
            data[f'"{key}"'] = self.parse_string(value)
        return data

    def parse(self, data) -> DataSerializer:
        if isinstance(data, str):
            return DataSerializer(self.parse_string(data), serialize=False)
        elif isinstance(data, dict):
            return DataSerializer(self.parse_map(data), serialize=False)
        raise ValueError(f'Unsupported value type: {type(data)}')

parse = _Parser().parse