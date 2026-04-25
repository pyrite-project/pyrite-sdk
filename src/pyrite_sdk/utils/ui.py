import re
from typing import Any, List, Union

class RFWSerializable:
    def to_rfw(self) -> str:
        raise NotImplementedError()

class DataSerializer(RFWSerializable):
    def __init__(self, data: Any, serialize: bool = True) -> None:
        self.data: Any = data
        self.serialize: bool = serialize
        self.serializer = _serialize_value if serialize else lambda v, serialize=False: _serialize_value(v, serialize=False)

    def to_rfw(self) -> str:
        if isinstance(self.data, (list, tuple)):
            return '[' + ', '.join(self.serializer(x) for x in self.data) + ']'
        if isinstance(self.data, dict):
            return '{' + ', '.join(f'{self.serializer(k)}: {self.serializer(v)}' for k, v in self.data.items()) + '}'
        if isinstance(self.data, bool):
            return 'true' if self.data else 'false'
        if isinstance(self.data, (int, float)):
            return str(self.data)
        if isinstance(self.data, RFWSerializable):
            return self.data.to_rfw()
        if not self.serialize:
            return str(self.data)
        if isinstance(self.data, str):
            return f'"{self.data}"'
        raise ValueError(f'Unsupported value type: {type(self.data)}')

def _serialize_value(v: Any, serialize: bool = True) -> str:
    return DataSerializer(v, serialize=serialize).to_rfw()

class DataParser(RFWSerializable):
    def __init__(self, data: Union[str, dict, list]) -> None:
        self._pattern = re.compile(r'\\(.)|\$\[(.*?)\]|([^\\$]+|.)')
        self.data: Union[str, dict, list] = data

    def parse_string(self, text: str) -> List[str]:
        tokens: List[str] = []
        for match in self._pattern.finditer(text):
            esc, var, lit = match.groups()

            if esc:
                tokens.append(f'\"{esc}\"')
            elif var:
                tokens.append(var)
            elif lit:
                tokens.append(f'\"{lit}\"')

        return self.merge_literals(tokens)

    def merge_literals(self, tokens: List[str]) -> List[str]:
        if not tokens: return []
        res: List[str] = []
        current_lit: List[str] = []

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
        data: dict = {}
        for key, value in map.items():
            if not isinstance(value, str): continue
            data[f'"{key}"'] = self.parse_string(value)
        return data

    def parse(self) -> DataSerializer:
        if isinstance(self.data, str):
            return DataSerializer(self.parse_string(self.data), serialize=False)
        elif isinstance(self.data, dict):
            return DataSerializer(self.parse_map(self.data), serialize=False)
        elif isinstance(self.data, list):
            return DataSerializer([self.parse(x) for x in self.data], serialize=False)
        else:
            return DataSerializer(self.data, serialize=False)

    def to_rfw(self) -> str:
        return self.parse().to_rfw()