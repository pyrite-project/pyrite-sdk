import json
import re
from enum import Enum
from typing import Any, List, Union
from abc import ABC, abstractmethod

class RFWSerializable(ABC):
    @abstractmethod
    def to_rfw(self) -> str:
        raise NotImplementedError("to_rfw is empty")

    def to_data(self) -> Any:
        return self.to_rfw()

class DataSerializer(RFWSerializable):
    def __init__(self, data: Any, serialize: bool = True) -> None:
        self.data: Any = data
        self.serialize: bool = serialize
        self.serializer = _serialize_value if serialize else lambda v, serialize=False: _serialize_value(v, serialize=False)

    def to_rfw(self) -> str:
        if isinstance(self.data, (list, tuple)):
            items = [self.serializer(x) for x in self.data]
            if any("\n" in item for item in items):
                rendered_items = ["  " + item.replace("\n", "\n  ") for item in items]
                return '[\n' + ',\n'.join(rendered_items) + '\n]'
            return '[' + ', '.join(items) + ']'
        if isinstance(self.data, dict):
            return '{' + ', '.join(f'{self.serializer(k)}: {self.serializer(v)}' for k, v in self.data.items()) + '}'
        if self.data is None:
            return 'null'
        if isinstance(self.data, bool):
            return 'true' if self.data else 'false'
        if isinstance(self.data, (int, float)):
            return str(self.data)
        if isinstance(self.data, RFWSerializable):
            return self.data.to_rfw()
        if isinstance(self.data, Enum):
            return _serialize_value(self.data.value, serialize=self.serialize)
        if not self.serialize:
            return str(self.data)
        if isinstance(self.data, str):
            return _quote_string(self.data)
        raise ValueError(f'Unsupported value type: {type(self.data)}')

def _serialize_value(v: Any, serialize: bool = True) -> str:
    return DataSerializer(v, serialize=serialize).to_rfw()

def _quote_string(v: str) -> str:
    return json.dumps(v, ensure_ascii=False)

def raw(v: Any) -> DataSerializer:
    return DataSerializer(v, serialize=False)

def to_data(value: Any) -> Any:
    if isinstance(value, RFWSerializable):
        return value.to_data()
    if isinstance(value, dict):
        return {key: to_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_data(item) for item in value]
    return value

class DataParser(RFWSerializable):
    def __init__(self, data: Union[str, dict, list]) -> None:
        self._pattern = re.compile(r'\\(.)|\$\[(.*?)\]|([^\\$]+|.)')
        self.data: Union[str, dict, list] = data

    def parse_string(self, text: str) -> List[str]:
        tokens: List[str] = []
        current_lit: List[str] = []

        def flush_literal() -> None:
            if current_lit:
                tokens.append(_quote_string("".join(current_lit)))
                current_lit.clear()

        for match in self._pattern.finditer(text):
            esc, var, lit = match.groups()

            if esc:
                current_lit.append(esc)
            elif var:
                flush_literal()
                tokens.append(var)
            elif lit:
                current_lit.append(lit)

        flush_literal()
        return tokens

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
            parsed_value = self._parse_value(value)
            data[_quote_string(str(key))] = parsed_value
        return data

    def _parse_value(self, data: Any) -> DataSerializer:
        if isinstance(data, str):
            return raw(self.parse_string(data))
        if isinstance(data, dict):
            return raw(self.parse_map(data))
        if isinstance(data, list):
            return raw([self._parse_value(x) for x in data])
        return DataSerializer(data)

    def parse(self) -> DataSerializer:
        return self._parse_value(self.data)

    def to_rfw(self) -> str:
        return self.parse().to_rfw()
