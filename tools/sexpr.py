"""KiCad S式の最小パーサ/ライタ。文字列は QStr、それ以外のアトムは str として保持する。"""


class QStr(str):
    """ダブルクォートで囲まれていた文字列。"""


def parse(text):
    i, n = 0, len(text)
    stack = [[]]
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "(":
            new = []
            stack[-1].append(new)
            stack.append(new)
            i += 1
        elif c == ")":
            stack.pop()
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while text[j] != '"':
                if text[j] == "\\":
                    nxt = text[j + 1]
                    buf.append({"n": "\n", "t": "\t"}.get(nxt, nxt))
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            stack[-1].append(QStr("".join(buf)))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n()":
                j += 1
            stack[-1].append(text[i:j])
            i = j
    return stack[0][0]


def _atom(a):
    if isinstance(a, QStr):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    return str(a)


def dump(node, indent=0):
    if not isinstance(node, list):
        return _atom(node)
    pad = "\t" * indent
    if all(not isinstance(c, list) for c in node):
        return pad + "(" + " ".join(_atom(c) for c in node) + ")"
    head = []
    k = 0
    while k < len(node) and not isinstance(node[k], list):
        head.append(_atom(node[k]))
        k += 1
    lines = [pad + "(" + " ".join(head)]
    for c in node[k:]:
        if isinstance(c, list):
            lines.append(dump(c, indent + 1))
        else:
            lines.append("\t" * (indent + 1) + _atom(c))
    lines.append(pad + ")")
    return "\n".join(lines)


def find(node, key):
    """直下の子から先頭が key のリストを全て返す。"""
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def first(node, key, default=None):
    r = find(node, key)
    return r[0] if r else default
