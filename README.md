# IDLark - A library for parsing WebIDL

### Example

```python

from idlark import IDLark
from pathlib import Path

def main():
    webidl_path = Path("path/to/webidl")
    parser = IDLark()
    idl_definitions = parser.parse(webidl_path.read_text(encoding="utf-8"))

if __name__ == '__main__':
    main()
```
