"""Invisible-ink codec: hide ASCII inside Unicode tag characters (U+E0000 block).

Every ASCII char in [0x20, 0x7E] maps to U+E0000 + codepoint. These render as
nothing in virtually all UIs/fonts, but survive copy-paste and are trivially
decodable by anyone who knows to look. This is the M2 exfiltration channel:
no tools, no network - just the model's own answer text.
"""


def encode(s: str) -> str:
    return "".join(chr(0xE0000 + ord(c)) for c in s if 0x20 <= ord(c) <= 0x7E)


def decode(s: str) -> str:
    return "".join(chr(ord(c) - 0xE0000) for c in s if 0xE0000 <= ord(c) <= 0xE007E)


def is_inked(s: str) -> bool:
    return any(0xE0000 <= ord(c) <= 0xE007F for c in s)


def strip_ink(s: str) -> str:
    return "".join(c for c in s if not (0xE0000 <= ord(c) <= 0xE007F))


if __name__ == "__main__":
    demo = encode("DEEPSPY|ACTIVE|log4shell")
    print("encoded :", repr(demo))
    print("decoded:", decode(demo))
    print("inked? :", is_inked("plain answer " + demo))
    print("visible: plain answer " + demo + "<- ink hidden between 'answer ' and this arrow")
