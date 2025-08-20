import re

def normalize_phone(txt: str) -> str:
    digits = re.sub(r'\D', '', txt)
    if digits.startswith('8'):
        digits = '7' + digits[1:]
    if not digits.startswith('7'):
        digits = '7' + digits
    return '+' + digits

def snils_checksum_ok(snils: str) -> bool:
    nums = re.sub(r'\D', '', snils)
    if len(nums) != 11: return False
    s = sum(int(nums[i]) * (9 - i) for i in range(9))
    c = int(nums[-2:])
    if s < 100: return s == c
    if s in (100, 101): return c == 0
    s = s % 101
    return (0 if s == 100 else s) == c

def addr_incomplete(txt: str) -> bool:
    return ('кв' in txt or 'кв.' in txt) and not any(ch.isdigit() for ch in txt.split('кв')[-1])
