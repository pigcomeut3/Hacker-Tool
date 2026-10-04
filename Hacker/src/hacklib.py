import base64
import binascii
import calendar
import codecs
import ctypes
import datetime
import hashlib
import json
import math
import os
import platform
import random
import re
import shutil
import socket
import string
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

HACKLIB = {}
HACKLIB_GROUPS = {}


def _reg(name, func, group="core"):
    HACKLIB[name] = func
    HACKLIB_GROUPS[name] = group


def total_count():
    return len(HACKLIB)


def group_stats():
    stats = {}
    for name, group in HACKLIB_GROUPS.items():
        stats[group] = stats.get(group, 0) + 1
    return stats


_reg("is_int", lambda v: isinstance(v, int) and not isinstance(v, bool), "types")
_reg("is_float", lambda v: isinstance(v, float), "types")
_reg("is_num", lambda v: isinstance(v, (int, float)), "types")
_reg("is_str", lambda v: isinstance(v, str), "types")
_reg("is_list", lambda v: isinstance(v, list), "types")
_reg("is_dict", lambda v: isinstance(v, dict), "types")
_reg("is_bool", lambda v: isinstance(v, bool), "types")
_reg("is_alpha", lambda v: str(v).isalpha(), "types")
_reg("is_digit", lambda v: str(v).isdigit(), "types")
_reg("is_alnum", lambda v: str(v).isalnum(), "types")
_reg("is_upper", lambda v: str(v).isupper(), "types")
_reg("is_lower", lambda v: str(v).islower(), "types")
_reg("is_space", lambda v: str(v).isspace(), "types")
_reg("is_empty", lambda v: str(v).strip() == "", "types")
_reg("is_blank", lambda v: str(v).strip() == "", "types")
_reg("is_none", lambda v: v is None, "types")
_reg("to_int", lambda v: int(v), "types")
_reg("to_float", lambda v: float(v), "types")
_reg("to_str", lambda v: str(v), "types")
_reg("to_bool", lambda v: bool(v), "types")
_reg("to_list", lambda v: list(v), "types")
_reg("to_tuple", lambda v: tuple(v), "types")
_reg("to_dict", lambda v: dict(v), "types")
_reg("to_set", lambda v: set(v), "types")
_reg("to_bytes", lambda v: str(v).encode(), "types")
_reg("to_chr", lambda v: chr(v), "types")
_reg("to_ord", lambda v: ord(str(v)[0]) if str(v) else 0, "types")

_reg("str_upper", lambda v: str(v).upper(), "strings")
_reg("str_lower", lambda v: str(v).lower(), "strings")
_reg("str_title", lambda v: str(v).title(), "strings")
_reg("str_capitalize", lambda v: str(v).capitalize(), "strings")
_reg("str_swapcase", lambda v: str(v).swapcase(), "strings")
_reg("str_reverse", lambda v: str(v)[::-1], "strings")
_reg("str_strip", lambda v: str(v).strip(), "strings")
_reg("str_lstrip", lambda v: str(v).lstrip(), "strings")
_reg("str_rstrip", lambda v: str(v).rstrip(), "strings")
_reg("str_len", lambda v: len(str(v)), "strings")
_reg("str_find", lambda v, s: str(v).find(s), "strings")
_reg("str_rfind", lambda v, s: str(v).rfind(s), "strings")
_reg("str_count", lambda v, s: str(v).count(s), "strings")
_reg("str_startswith", lambda v, s: str(v).startswith(s), "strings")
_reg("str_endswith", lambda v, s: str(v).endswith(s), "strings")
_reg("str_contains", lambda v, s: s in str(v), "strings")
_reg("str_split", lambda v, sep=" ": str(v).split(sep), "strings")
_reg("str_splitlines", lambda v: str(v).splitlines(), "strings")
_reg("str_replace", lambda v, a, b: str(v).replace(a, b), "strings")
_reg("str_join", lambda items, sep=" ": sep.join(str(i) for i in items), "strings")
_reg("first_char", lambda v: str(v)[0] if str(v) else "", "strings")
_reg("last_char", lambda v: str(v)[-1] if str(v) else "", "strings")
_reg("nth_char", lambda v, n: str(v)[n] if 0 <= n < len(str(v)) else "", "strings")
_reg("slice_str", lambda v, a, b=None: str(v)[a:b] if b is not None else str(v)[a:], "strings")
_reg("chars", lambda v: list(str(v)), "strings")
_reg("words", lambda v: str(v).split(), "strings")
_reg("lines", lambda v: str(v).splitlines(), "strings")
_reg("sort_chars", lambda v: "".join(sorted(str(v))), "strings")
_reg("reverse_words", lambda v: " ".join(reversed(str(v).split())), "strings")
_reg("unique_chars", lambda v: "".join(dict.fromkeys(str(v))), "strings")
_reg("shuffle_str", lambda v: "".join(random.sample(str(v), len(str(v)))), "strings")
_reg("sample_str", lambda v, n: "".join(random.sample(str(v), min(n, len(str(v))))), "strings")
_reg("truncate", lambda v, n: str(v)[:n] + ("..." if len(str(v)) > n else ""), "strings")
_reg("ellipsize", lambda v, n: str(v)[:n] + "..." if len(str(v)) > n else str(v), "strings")
_reg("pad_left", lambda v, n, c=" ": str(v).rjust(n, c), "strings")
_reg("pad_right", lambda v, n, c=" ": str(v).ljust(n, c), "strings")
_reg("pad_center", lambda v, n, c=" ": str(v).center(n, c), "strings")
_reg("collapse_spaces", lambda v: re.sub(r"\s+", " ", str(v)).strip(), "strings")
_reg("wrap_quotes", lambda v: f"'{v}'", "strings")
_reg("wrap_dquotes", lambda v: f'"{v}"', "strings")
_reg("wrap_parens", lambda v: f"({v})", "strings")
_reg("wrap_brackets", lambda v: f"[{v}]", "strings")
_reg("wrap_braces", lambda v: f"{{{v}}}", "strings")
_reg("wrap_angle", lambda v: f"<{v}>", "strings")
_reg("wrap_stars", lambda v: f"*{v}*", "strings")
_reg("wrap_hash", lambda v: f"#{v}#", "strings")
_reg("wrap_slashes", lambda v: f"/{v}/", "strings")
_reg("wrap_backticks", lambda v: f"`{v}`", "strings")
_reg("join_comma", lambda items: ", ".join(str(i) for i in items), "strings")
_reg("join_space", lambda items: " ".join(str(i) for i in items), "strings")
_reg("join_pipe", lambda items: " | ".join(str(i) for i in items), "strings")
_reg("join_dash", lambda items: " - ".join(str(i) for i in items), "strings")
_reg("join_dot", lambda items: ".".join(str(i) for i in items), "strings")
_reg("join_underscore", lambda items: "_".join(str(i) for i in items), "strings")
_reg("join_slash", lambda items: "/".join(str(i) for i in items), "strings")
_reg("join_newline", lambda items: "\n".join(str(i) for i in items), "strings")
_reg("join_plus", lambda items: " + ".join(str(i) for i in items), "strings")
_reg("join_tab", lambda items: "\t".join(str(i) for i in items), "strings")
_reg("split_comma", lambda v: str(v).split(","), "strings")
_reg("split_pipe", lambda v: str(v).split("|"), "strings")
_reg("split_dash", lambda v: str(v).split("-"), "strings")
_reg("split_dot", lambda v: str(v).split("."), "strings")
_reg("split_underscore", lambda v: str(v).split("_"), "strings")
_reg("split_slash", lambda v: str(v).split("/"), "strings")
_reg("split_newline", lambda v: str(v).splitlines(), "strings")
_reg("split_tab", lambda v: str(v).split("\t"), "strings")
_reg("split_none", lambda v: str(v).split(), "strings")
_reg("count_vowels", lambda v: sum(1 for c in str(v).lower() if c in "aeiou"), "strings")
_reg("count_consonants", lambda v: sum(1 for c in str(v).lower() if c.isalpha() and c not in "aeiou"), "strings")
_reg("count_digits", lambda v: sum(1 for c in str(v) if c.isdigit()), "strings")
_reg("count_letters", lambda v: sum(1 for c in str(v) if c.isalpha()), "strings")
_reg("count_spaces", lambda v: sum(1 for c in str(v) if c.isspace()), "strings")
_reg("count_upper", lambda v: sum(1 for c in str(v) if c.isupper()), "strings")
_reg("count_lower", lambda v: sum(1 for c in str(v) if c.islower()), "strings")
_reg("count_words", lambda v: len(str(v).split()), "strings")
_reg("count_lines", lambda v: len(str(v).splitlines()), "strings")
_reg("count_symbols", lambda v: sum(1 for c in str(v) if not c.isalnum() and not c.isspace()), "strings")
_reg("count_punct", lambda v: sum(1 for c in str(v) if c in string.punctuation), "strings")
_reg("count_chars", lambda v: len(str(v)), "strings")
_reg("only_digits", lambda v: "".join(c for c in str(v) if c.isdigit()), "strings")
_reg("only_letters", lambda v: "".join(c for c in str(v) if c.isalpha()), "strings")
_reg("only_alnum", lambda v: "".join(c for c in str(v) if c.isalnum()), "strings")
_reg("only_upper", lambda v: "".join(c for c in str(v) if c.isupper()), "strings")
_reg("only_lower", lambda v: "".join(c for c in str(v) if c.islower()), "strings")
_reg("remove_digits", lambda v: "".join(c for c in str(v) if not c.isdigit()), "strings")
_reg("remove_letters", lambda v: "".join(c for c in str(v) if not c.isalpha()), "strings")
_reg("remove_spaces", lambda v: "".join(c for c in str(v) if not c.isspace()), "strings")
_reg("remove_vowels", lambda v: "".join(c for c in str(v) if c.lower() not in "aeiou"), "strings")
_reg("remove_consonants", lambda v: "".join(c for c in str(v) if not c.isalpha() or c.lower() in "aeiou"), "strings")
_reg("remove_punct", lambda v: "".join(c for c in str(v) if c not in string.punctuation), "strings")
_reg("remove_newlines", lambda v: str(v).replace("\n", "").replace("\r", ""), "strings")
_reg("remove_tabs", lambda v: str(v).replace("\t", ""), "strings")
_reg("strip_punct", lambda v: str(v).strip(string.punctuation), "strings")
_reg("strip_quotes", lambda v: str(v).strip("'\"`"), "strings")
_reg("replace_spaces", lambda v, r="_": str(v).replace(" ", r), "strings")
_reg("replace_tabs", lambda v, r=" ": str(v).replace("\t", r), "strings")
_reg("replace_newlines", lambda v, r=" ": str(v).replace("\n", r), "strings")
_reg("replace_dots", lambda v, r="_": str(v).replace(".", r), "strings")
_reg("replace_dashes", lambda v, r="_": str(v).replace("-", r), "strings")
_reg("replace_underscores", lambda v, r=" ": str(v).replace("_", r), "strings")
_reg("is_palindrome", lambda v: str(v).lower() == str(v)[::-1].lower(), "strings")
_reg("is_anagram", lambda a, b: sorted(str(a).lower()) == sorted(str(b).lower()), "strings")
_reg("is_title_case", lambda v: str(v).istitle(), "strings")
_reg("is_snake_case", lambda v: re.fullmatch(r"[a-z0-9]+(_[a-z0-9]+)*", str(v)) is not None, "strings")
_reg("is_kebab_case", lambda v: re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(v)) is not None, "strings")
_reg("is_upper_case", lambda v: str(v).isupper() and any(c.isalpha() for c in str(v)), "strings")
_reg("is_lower_case", lambda v: str(v).islower() and any(c.isalpha() for c in str(v)), "strings")
_reg("case_constant", lambda v: re.sub(r"[A-Z]", lambda m: "_" + m.group(0), str(v)).upper().replace(" ", "_"), "strings")
_reg("case_title", lambda v: str(v).title(), "strings")
_reg("case_upper", lambda v: str(v).upper(), "strings")
_reg("case_lower", lambda v: str(v).lower(), "strings")

_reg("enc_base64", lambda v: base64.b64encode(str(v).encode()).decode(), "encode")
_reg("dec_base64", lambda v: base64.b64decode(v).decode("utf-8", errors="replace"), "encode")
_reg("enc_base32", lambda v: base64.b32encode(str(v).encode()).decode(), "encode")
_reg("dec_base32", lambda v: base64.b32decode(v).decode("utf-8", errors="replace"), "encode")
_reg("enc_base85", lambda v: base64.b85encode(str(v).encode()).decode(), "encode")
_reg("dec_base85", lambda v: base64.b85decode(v).decode("utf-8", errors="replace"), "encode")
_reg("enc_hex", lambda v: str(v).encode().hex(), "encode")
_reg("dec_hex", lambda v: bytes.fromhex(v).decode("utf-8", errors="replace"), "encode")
_reg("enc_url", lambda v: urllib.parse.quote(str(v)), "encode")
_reg("dec_url", lambda v: urllib.parse.unquote(v), "encode")
_reg("enc_utf8", lambda v: str(v).encode("utf-8").hex(), "encode")
_reg("enc_bin", lambda v: "".join(f"{ord(c):08b}" for c in str(v)), "encode")
_reg("dec_bin", lambda v: "".join(chr(int(v[i:i + 8], 2)) for i in range(0, len(v) - 7, 8)), "encode")
_reg("enc_ascii", lambda v: " ".join(str(ord(c)) for c in str(v)), "encode")
_reg("dec_ascii", lambda v: "".join(chr(int(p)) for p in str(v).split()), "encode")
_reg("enc_html", lambda v: v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"), "encode")
_reg("dec_html", lambda v: v.replace("&quot;", '"').replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&"), "encode")
_reg("enc_unicode", lambda v: "".join(f"\\u{ord(c):04x}" for c in str(v)), "encode")
_reg("enc_oct", lambda v: " ".join(f"{ord(c):o}" for c in str(v)), "encode")
_reg("dec_oct", lambda v: "".join(chr(int(p, 8)) for p in str(v).split()), "encode")

_MORSE = {
    "a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".", "f": "..-.",
    "g": "--.", "h": "....", "i": "..", "j": ".---", "k": "-.-", "l": ".-..",
    "m": "--", "n": "-.", "o": "---", "p": ".--.", "q": "--.-", "r": ".-.",
    "s": "...", "t": "-", "u": "..-", "v": "...-", "w": ".--", "x": "-..-",
    "y": "-.--", "z": "--..", "0": "-----", "1": ".----", "2": "..---",
    "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.",
}
_MORSE_REVERSE = {value: key for key, value in _MORSE.items()}


def _case_camel(text):
    return re.sub(r"[_\-\s]+(.)", lambda m: m.group(1).upper(), str(text).lower())


def _case_snake(text):
    return re.sub(r"[\s\-]+", "_", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(text))).lower()


def _case_kebab(text):
    return re.sub(r"[\s_]+", "-", re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", str(text))).lower()


def _case_pascal(text):
    result = re.sub(r"[_\-\s]+(.)", lambda m: m.group(1).upper(), str(text).lower())
    return result[0].upper() + result[1:] if result else ""


_reg("case_camel", lambda v: _case_camel(v), "strings")
_reg("case_snake", lambda v: _case_snake(v), "strings")
_reg("case_kebab", lambda v: _case_kebab(v), "strings")
_reg("case_pascal", lambda v: _case_pascal(v), "strings")


def _enc_morse(text):
    result = []
    for char in str(text).lower():
        if char == " ":
            result.append("/")
        elif char in _MORSE:
            result.append(_MORSE[char])
    return " ".join(result)


def _dec_morse(text):
    result = []
    for token in str(text).split():
        if token == "/":
            result.append(" ")
        elif token in _MORSE_REVERSE:
            result.append(_MORSE_REVERSE[token])
    return "".join(result)


_reg("enc_morse", _enc_morse, "encode")
_reg("dec_morse", _dec_morse, "encode")


def _rot47(text):
    result = []
    for char in str(text):
        code = ord(char)
        if 33 <= code <= 126:
            result.append(chr(33 + ((code + 14) % 94)))
        else:
            result.append(char)
    return "".join(result)


_reg("enc_rot47", _rot47, "encode")
_reg("dec_rot47", _rot47, "encode")
_reg("enc_rot13", lambda v: codecs.encode(str(v), "rot_13"), "encode")
_reg("dec_rot13", lambda v: codecs.encode(str(v), "rot_13"), "encode")

_reg("md5", lambda v: hashlib.md5(str(v).encode()).hexdigest(), "hash")
_reg("sha1", lambda v: hashlib.sha1(str(v).encode()).hexdigest(), "hash")
_reg("sha224", lambda v: hashlib.sha224(str(v).encode()).hexdigest(), "hash")
_reg("sha256", lambda v: hashlib.sha256(str(v).encode()).hexdigest(), "hash")
_reg("sha384", lambda v: hashlib.sha384(str(v).encode()).hexdigest(), "hash")
_reg("sha512", lambda v: hashlib.sha512(str(v).encode()).hexdigest(), "hash")
_reg("sha3_256", lambda v: hashlib.sha3_256(str(v).encode()).hexdigest(), "hash")
_reg("sha3_512", lambda v: hashlib.sha3_512(str(v).encode()).hexdigest(), "hash")
_reg("blake2b", lambda v: hashlib.blake2b(str(v).encode()).hexdigest(), "hash")
_reg("blake2s", lambda v: hashlib.blake2s(str(v).encode()).hexdigest(), "hash")
_reg("crc32", lambda v: f"{binascii.crc32(str(v).encode()) & 0xFFFFFFFF:08x}", "hash")


def _hash_file(path, algorithm):
    digest = hashlib.new(algorithm)
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 256)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


_reg("hash_file_md5", lambda p: _hash_file(p, "md5"), "hash")
_reg("hash_file_sha1", lambda p: _hash_file(p, "sha1"), "hash")
_reg("hash_file_sha256", lambda p: _hash_file(p, "sha256"), "hash")
_reg("hash_all", lambda v: {a: hashlib.new(a, str(v).encode()).hexdigest() for a in hashlib.algorithms_available if a not in ("shake_128", "shake_256")}, "hash")


def _is_prime(number):
    number = abs(int(number))
    if number < 2:
        return False
    if number % 2 == 0:
        return number == 2
    for divisor in range(3, int(math.isqrt(number)) + 1, 2):
        if number % divisor == 0:
            return False
    return True


def _nth_prime(number):
    count = 0
    candidate = 2
    while True:
        if _is_prime(candidate):
            count += 1
            if count >= number:
                return candidate
        candidate += 1


_reg("factorial", lambda n: math.factorial(int(n)), "math")
_reg("fibonacci", lambda n: _fib(int(n)), "math")
_reg("is_prime", _is_prime, "math")
_reg("nth_prime", _nth_prime, "math")
_reg("next_prime", lambda n: _nth_prime(_prime_index(n) + 1) if _is_prime(n) else _next_prime_after(int(n)), "math")
_reg("prev_prime", lambda n: _prev_prime_before(int(n)), "math")
_reg("primes_below", lambda n: [i for i in range(2, int(n)) if _is_prime(i)], "math")
_reg("gcd", lambda a, b: math.gcd(int(a), int(b)), "math")
_reg("lcm", lambda a, b: abs(int(a) * int(b)) // math.gcd(int(a), int(b)), "math")
_reg("is_even", lambda n: int(n) % 2 == 0, "math")
_reg("is_odd", lambda n: int(n) % 2 != 0, "math")
_reg("is_square", lambda n: math.isqrt(int(n)) ** 2 == int(n), "math")
_reg("is_cube", lambda n: round(int(n) ** (1 / 3)) ** 3 == int(n), "math")
_reg("is_power_of_two", lambda n: int(n) > 0 and (int(n) & (int(n) - 1)) == 0, "math")
_reg("is_palindrome_num", lambda n: str(n) == str(n)[::-1], "math")
_reg("digit_sum", lambda n: sum(int(d) for d in str(abs(int(n)))), "math")
_reg("digit_product", lambda n: math.prod((int(d) for d in str(abs(int(n))))) if str(abs(int(n))) else 0, "math")
_reg("digit_count", lambda n: len(str(abs(int(n)))), "math")
_reg("digit_reverse", lambda n: int(str(n)[::-1]), "math")
_reg("square", lambda n: int(n) ** 2, "math")
_reg("cube", lambda n: int(n) ** 3, "math")
_reg("sqrt", lambda n: math.sqrt(n), "math")
_reg("cbrt", lambda n: n ** (1 / 3), "math")
_reg("abs_val", lambda n: abs(n), "math")
_reg("ceil", lambda n: math.ceil(n), "math")
_reg("floor", lambda n: math.floor(n), "math")
_reg("round_num", lambda n, d=0: round(n, d), "math")
_reg("sign", lambda n: (n > 0) - (n < 0), "math")
_reg("clamp", lambda n, a, b: max(a, min(b, n)), "math")
_reg("lerp", lambda a, b, t: a + (b - a) * t, "math")
_reg("deg_to_rad", lambda n: math.radians(n), "math")
_reg("rad_to_deg", lambda n: math.degrees(n), "math")
_reg("log10", lambda n: math.log10(n), "math")
_reg("log2", lambda n: math.log2(n), "math")
_reg("ln", lambda n: math.log(n), "math")
_reg("exp", lambda n: math.exp(n), "math")
_reg("power", lambda a, b: a ** b, "math")
_reg("hypot", lambda a, b: math.hypot(a, b), "math")
_reg("pi", lambda: math.pi, "math")
_reg("e", lambda: math.e, "math")
_reg("tau", lambda: math.tau, "math")
_reg("triangular", lambda n: int(n) * (int(n) + 1) // 2, "math")
_reg("is_triangular", lambda n: math.isqrt(8 * int(n) + 1) ** 2 == 8 * int(n) + 1, "math")
_reg("is_armstrong", lambda n: sum(int(d) ** len(str(n)) for d in str(n)) == int(n), "math")
_reg("is_perfect", lambda n: sum(d for d in _divisors(int(n)) if d != int(n)) == int(n), "math")
_reg("is_repdigit", lambda n: len(set(str(n))) == 1, "math")
_reg("collatz", lambda n: _collatz(int(n)), "math")
_reg("divisors", lambda n: _divisors(int(n)), "math")
_reg("phi", lambda n: _phi(int(n)), "math")
_reg("is_coprime", lambda a, b: math.gcd(int(a), int(b)) == 1, "math")
_reg("is_happy", lambda n: _is_happy(int(n)), "math")
_reg("add", lambda a, b: a + b, "math")
_reg("subtract", lambda a, b: a - b, "math")
_reg("multiply", lambda a, b: a * b, "math")
_reg("divide", lambda a, b: a / b, "math")
_reg("mod", lambda a, b: a % b, "math")
_reg("negate", lambda n: -n, "math")
_reg("double", lambda n: n * 2, "math")
_reg("triple", lambda n: n * 3, "math")
_reg("half", lambda n: n / 2, "math")
_reg("percent", lambda n, total: n * 100 / total if total else 0, "math")
_reg("percentage", lambda part, whole: part * whole / 100, "math")
_reg("avg", lambda items: sum(items) / len(items) if items else 0, "math")
_reg("mean", lambda items: sum(items) / len(items) if items else 0, "math")
_reg("median", lambda items: _median(list(items)), "math")
_reg("mode", lambda items: max(set(items), key=items.count), "math")
_reg("variance", lambda items: sum((x - sum(items) / len(items)) ** 2 for x in items) / len(items) if items else 0, "math")
_reg("stddev", lambda items: math.sqrt(sum((x - sum(items) / len(items)) ** 2 for x in items) / len(items)) if items else 0, "math")
_reg("min_of", lambda items: min(items), "math")
_reg("max_of", lambda items: max(items), "math")
_reg("sum_of", lambda items: sum(items), "math")
_reg("squares_upto", lambda n: [i ** 2 for i in range(1, int(n) + 1)], "math")
_reg("cubes_upto", lambda n: [i ** 3 for i in range(1, int(n) + 1)], "math")
_reg("fib_upto", lambda n: [i for i in _fib_range(int(n))], "math")
_reg("primes_upto", lambda n: [i for i in range(2, int(n) + 1) if _is_prime(i)], "math")
_reg("odds_upto", lambda n: list(range(1, int(n) + 1, 2)), "math")
_reg("evens_upto", lambda n: list(range(2, int(n) + 1, 2)), "math")
_reg("powers2_upto", lambda n: [2 ** i for i in range(int(n) + 1)], "math")
_reg("powers3_upto", lambda n: [3 ** i for i in range(int(n) + 1)], "math")


def _fib(number):
    a, b = 0, 1
    for _ in range(int(number)):
        a, b = b, a + b
    return a


def _fib_range(number):
    a, b = 0, 1
    result = []
    while a <= number:
        result.append(a)
        a, b = b, a + b
    return result


def _divisors(number):
    result = []
    for divisor in range(1, int(math.isqrt(number)) + 1):
        if number % divisor == 0:
            result.append(divisor)
            if divisor != number // divisor:
                result.append(number // divisor)
    return sorted(result)


def _phi(number):
    result = number
    remaining = number
    divisor = 2
    while divisor * divisor <= remaining:
        if remaining % divisor == 0:
            while remaining % divisor == 0:
                remaining //= divisor
            result -= result // divisor
        divisor += 1
    if remaining > 1:
        result -= result // remaining
    return result


def _is_happy(number):
    seen = set()
    while number != 1 and number not in seen:
        seen.add(number)
        number = sum(int(d) ** 2 for d in str(number))
    return number == 1


def _prime_index(number):
    count = 0
    for candidate in range(2, int(number) + 1):
        if _is_prime(candidate):
            count += 1
    return count


def _next_prime_after(number):
    candidate = number + 1
    while not _is_prime(candidate):
        candidate += 1
    return candidate


def _prev_prime_before(number):
    candidate = number - 1
    while candidate > 1:
        if _is_prime(candidate):
            return candidate
        candidate -= 1
    return None


def _median(items):
    ordered = sorted(items)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _mult_table(number):
    return "\n".join(f"{number} x {i} = {number * i}" for i in range(1, 11))


for _n in range(2, 17):
    _reg(f"mult_table_{_n}", (lambda n: lambda: _mult_table(n))(_n), "math")

_reg("rand_int", lambda a=0, b=100: random.randint(a, b), "random")
_reg("rand_float", lambda a=0.0, b=1.0: random.uniform(a, b), "random")
_reg("rand_bool", lambda: random.choice([True, False]), "random")
_reg("rand_choice", lambda items: random.choice(items), "random")
_reg("rand_choices", lambda items, k=1: random.choices(items, k=k), "random")
_reg("rand_shuffle", lambda items: random.sample(items, len(items)), "random")
_reg("rand_sample", lambda items, k=1: random.sample(items, min(k, len(items))), "random")
_reg("rand_password", lambda length=12: "".join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*", k=length)), "random")
_reg("rand_hex", lambda length=8: "".join(random.choices("0123456789abcdef", k=length)), "random")
_reg("rand_token", lambda length=16: "".join(random.choices(string.ascii_letters + string.digits, k=length)), "random")
_reg("rand_digit", lambda: random.randint(0, 9), "random")
_reg("rand_letter", lambda: random.choice(string.ascii_letters), "random")
_reg("rand_string", lambda length=8: "".join(random.choices(string.ascii_letters + string.digits, k=length)), "random")
_reg("rand_color", lambda: "#{:06x}".format(random.randint(0, 0xFFFFFF)), "random")
_reg("rand_uuid4", lambda: str(uuid.uuid4()), "random")
_reg("rand_uuid1", lambda: str(uuid.uuid1()), "random")
_reg("coin_flip", lambda: random.choice(["Heads", "Tails"]), "random")
_reg("dice", lambda: random.randint(1, 6), "random")

_reg("list_sort", lambda items: sorted(items), "lists")
_reg("list_reverse", lambda items: list(reversed(items)), "lists")
_reg("list_unique", lambda items: list(dict.fromkeys(items)), "lists")
_reg("list_flatten", lambda items: _flatten(items), "lists")
_reg("list_chunk", lambda items, size=2: [items[i:i + size] for i in range(0, len(items), size)], "lists")
_reg("list_shuffle", lambda items: random.sample(items, len(items)), "lists")
_reg("list_sum", lambda items: sum(items), "lists")
_reg("list_max", lambda items: max(items), "lists")
_reg("list_min", lambda items: min(items), "lists")
_reg("list_avg", lambda items: sum(items) / len(items) if items else 0, "lists")
_reg("list_median", lambda items: _median(list(items)), "lists")
_reg("list_mode", lambda items: max(set(items), key=items.count), "lists")
_reg("list_range", lambda a, b=None, step=1: list(range(a, b, step)) if b is not None else list(range(a)), "lists")
_reg("list_zip", lambda a, b: list(zip(a, b)), "lists")
_reg("list_head", lambda items, n=5: items[:n], "lists")
_reg("list_tail", lambda items, n=5: items[-n:], "lists")
_reg("list_first", lambda items: items[0] if items else None, "lists")
_reg("list_last", lambda items: items[-1] if items else None, "lists")
_reg("list_contains", lambda items, value: value in items, "lists")
_reg("list_count", lambda items, value: items.count(value), "lists")
_reg("list_append", lambda items, value: items + [value], "lists")
_reg("list_extend", lambda items, more: items + list(more), "lists")
_reg("list_remove", lambda items, value: [i for i in items if i != value], "lists")
_reg("list_pop", lambda items, index=-1: items.pop(index), "lists")
_reg("list_len", lambda items: len(items), "lists")
_reg("list_copy", lambda items: list(items), "lists")
_reg("list_merge", lambda *lists: [item for lst in lists for item in lst], "lists")
_reg("list_index", lambda items, value: items.index(value) if value in items else -1, "lists")


def _flatten(items):
    result = []
    for item in items:
        if isinstance(item, list):
            result.extend(_flatten(item))
        else:
            result.append(item)
    return result


_reg("dict_keys", lambda d: list(d.keys()), "dicts")
_reg("dict_values", lambda d: list(d.values()), "dicts")
_reg("dict_items", lambda d: list(d.items()), "dicts")
_reg("dict_get", lambda d, key, default=None: d.get(key, default), "dicts")
_reg("dict_set", lambda d, key, value: {**d, key: value}, "dicts")
_reg("dict_merge", lambda a, b: {**a, **b}, "dicts")
_reg("dict_invert", lambda d: {value: key for key, value in d.items()}, "dicts")
_reg("dict_sort", lambda d: dict(sorted(d.items())), "dicts")
_reg("dict_len", lambda d: len(d), "dicts")
_reg("dict_pop", lambda d, key, default=None: d.pop(key, default), "dicts")
_reg("dict_update", lambda d, more: {**d, **more}, "dicts")
_reg("dict_has", lambda d, key: key in d, "dicts")
_reg("dict_flip", lambda d: {value: key for key, value in d.items()}, "dicts")

_reg("net_hostname", lambda: platform.node(), "network")
_reg("net_ip_local", lambda: socket.gethostbyname(socket.gethostname()), "network")
_reg("net_dns", lambda host: socket.gethostbyname(host), "network")


def _net_ping(host):
    result = subprocess.run(["ping", "-n", "1", "-w", "1000", str(host)], capture_output=True)
    return result.returncode == 0


def _net_is_port_open(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        return sock.connect_ex((host, int(port))) == 0
    finally:
        sock.close()


def _net_public_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=8) as response:
            return response.read().decode("utf-8", errors="replace").strip()
    except (OSError, urllib.error.URLError):
        return None


def _net_http_get(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return response.read().decode("utf-8", errors="replace")
    except (OSError, urllib.error.URLError) as error:
        return f"Error: {error}"


def _net_download(url, destination):
    try:
        urllib.request.urlretrieve(url, str(destination))
        return str(destination)
    except (OSError, urllib.error.URLError) as error:
        return f"Error: {error}"


def _net_scan_ports(host, ports):
    open_ports = []
    for port in ports:
        if _net_is_port_open(host, port):
            open_ports.append(int(port))
    return open_ports


_reg("net_ping", _net_ping, "network")
_reg("net_is_port_open", _net_is_port_open, "network")
_reg("net_public_ip", _net_public_ip, "network")
_reg("net_http_get", _net_http_get, "network")
_reg("net_download", _net_download, "network")
_reg("net_scan_ports", _net_scan_ports, "network")


def _sys_memory():
    class _Status(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = _Status()
    status.dwLength = ctypes.sizeof(_Status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return {}
    return {
        "load": status.dwMemoryLoad,
        "total": status.ullTotalPhys,
        "available": status.ullAvailPhys,
        "used": status.ullTotalPhys - status.ullAvailPhys,
    }


def _sys_uptime():
    return ctypes.windll.kernel32.GetTickCount64() // 1000


def _sys_battery():
    class _Power(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte),
            ("BatteryFlag", ctypes.c_ubyte),
            ("BatteryLifePercent", ctypes.c_ubyte),
            ("SystemStatusFlag", ctypes.c_ubyte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    status = _Power()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return {}
    return {
        "ac": status.ACLineStatus,
        "percent": None if status.BatteryLifePercent == 255 else status.BatteryLifePercent,
    }


def _sys_disk():
    result = {}
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            usage = shutil.disk_usage(root)
            result[letter] = {"total": usage.total, "used": usage.used, "free": usage.free}
    return result


_reg("sys_memory", _sys_memory, "system")
_reg("sys_memory_used", lambda: _sys_memory().get("used", 0), "system")
_reg("sys_memory_free", lambda: _sys_memory().get("available", 0), "system")
_reg("sys_memory_load", lambda: _sys_memory().get("load", 0), "system")
_reg("sys_cpu_cores", lambda: os.cpu_count(), "system")
_reg("sys_uptime", _sys_uptime, "system")
_reg("sys_user", lambda: os.environ.get("USERNAME") or os.environ.get("USER") or "", "system")
_reg("sys_hostname", lambda: platform.node(), "system")
_reg("sys_os", lambda: f"{platform.system()} {platform.release()}", "system")
_reg("sys_python_version", lambda: sys.version.split()[0], "system")
_reg("sys_platform", lambda: platform.platform(), "system")
_reg("sys_architecture", lambda: platform.architecture()[0], "system")
_reg("sys_processor", lambda: platform.processor(), "system")
_reg("sys_machine", lambda: platform.machine(), "system")
_reg("sys_battery", _sys_battery, "system")
_reg("sys_disk", _sys_disk, "system")
_reg("sys_env", lambda name="": os.environ.get(name, ""), "system")
_reg("sys_ver", lambda: platform.version(), "system")
_reg("sys_workdir", lambda: os.getcwd(), "system")
_reg("sys_pid", lambda: os.getpid(), "system")
_reg("sys_path", lambda: os.environ.get("PATH", ""), "system")

_reg("file_read", lambda path: Path(path).read_text(encoding="utf-8", errors="replace") if Path(path).is_file() else None, "files")
_reg("file_write", lambda path, text: Path(path).write_text(str(text), encoding="utf-8"), "files")
_reg("file_append", lambda path, text: Path(path).open("a", encoding="utf-8").write(str(text) + "\n"), "files")
_reg("file_exists", lambda path: Path(path).exists(), "files")
_reg("file_is_file", lambda path: Path(path).is_file(), "files")
_reg("file_is_dir", lambda path: Path(path).is_dir(), "files")
_reg("file_delete", lambda path: Path(path).unlink() if Path(path).is_file() else None, "files")
_reg("file_rename", lambda old, new: Path(old).rename(Path(new)), "files")
_reg("file_copy", lambda source, destination: shutil.copy2(source, destination), "files")
_reg("file_move", lambda source, destination: shutil.move(source, destination), "files")
_reg("file_size", lambda path: Path(path).stat().st_size if Path(path).exists() else 0, "files")
_reg("file_lines", lambda path: len(Path(path).read_text(encoding="utf-8", errors="replace").splitlines()) if Path(path).is_file() else 0, "files")
_reg("file_touch", lambda path: Path(path).touch(exist_ok=True), "files")
_reg("file_name", lambda path: Path(path).name, "files")
_reg("file_dir", lambda path: str(Path(path).parent), "files")
_reg("file_extension", lambda path: Path(path).suffix, "files")
_reg("file_stem", lambda path: Path(path).stem, "files")
_reg("file_absolute", lambda path: str(Path(path).resolve()), "files")
_reg("file_list", lambda path=".": sorted(str(p) for p in Path(path).iterdir()), "files")


def _file_find(pattern, root="."):
    results = []
    for current, directories, files in os.walk(root):
        for name in files + directories:
            if pattern.casefold() in name.casefold():
                results.append(str(Path(current) / name))
    return results


_reg("file_find", _file_find, "files")
_reg("dir_create", lambda path: Path(path).mkdir(parents=True, exist_ok=True), "files")
_reg("dir_delete", lambda path: shutil.rmtree(path, ignore_errors=True) if Path(path).is_dir() else None, "files")
_reg("dir_size", lambda path: sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file()) if Path(path).exists() else 0, "files")

_reg("time_now", lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "time")
_reg("time_date", lambda: datetime.date.today().isoformat(), "time")
_reg("time_year", lambda: datetime.datetime.now().year, "time")
_reg("time_month", lambda: datetime.datetime.now().month, "time")
_reg("time_day", lambda: datetime.datetime.now().day, "time")
_reg("time_hour", lambda: datetime.datetime.now().hour, "time")
_reg("time_minute", lambda: datetime.datetime.now().minute, "time")
_reg("time_second", lambda: datetime.datetime.now().second, "time")
_reg("time_epoch", lambda: int(time.time()), "time")
_reg("time_format", lambda fmt="%Y-%m-%d %H:%M:%S": datetime.datetime.now().strftime(fmt), "time")
_reg("date_iso", lambda: datetime.date.today().isoformat(), "time")
_reg("date_ymd", lambda: datetime.date.today().strftime("%Y%m%d"), "time")
_reg("date_weekday", lambda: datetime.date.today().strftime("%A"), "time")
_reg("date_weeks", lambda: datetime.date.today().isocalendar().week, "time")
_reg("date_days_in_month", lambda: calendar.monthrange(datetime.date.today().year, datetime.date.today().month)[1], "time")
_reg("sleep_sec", lambda seconds: time.sleep(seconds), "time")
_reg("sleep_ms", lambda millis: time.sleep(millis / 1000), "time")

_reg("art_star", lambda: "\n".join(["  *  ", " *** ", "*****", " *** ", "  *  "]), "fun")
_reg("art_heart", lambda: "\n".join([" ** ** ", "*******", "*******", " ***** ", "  ***  ", "   *   "]), "fun")
_reg("art_arrow", lambda: "\n".join(["   ^   ", "  /|\\  ", " / | \\ ", "/  |  \\", "   |   ", "   |   "]), "fun")
_reg("art_diamond", lambda: "\n".join(["   *   ", "  ***  ", " ***** ", "*******", " ***** ", "  ***  ", "   *   "]), "fun")
_reg("art_tree", lambda: "\n".join(["   ^   ", "  / \\  ", " /   \\ ", "/_____\\", "   |   "]), "fun")
_reg("art_robot", lambda: "\n".join(["  _____  ", " |_ _ _| ", " | o o | ", " |  ^  | ", " | --- | ", " |_____| "]), "fun")
_reg("ascii_skull", lambda: "\n".join(["  _____  ", " / _ _ \\ ", "| 0 0 | |", "|  ^  | |", "| ~~~ | |", " \\_____/ "]), "fun")
_reg("ascii_hacker", lambda: "\n".join(["$_$  ", "|o o|", "| ~ |", "|___|"]), "fun")
_reg("ascii_terminal", lambda: "\n".join(["+-----+", "| >_  |", "+-----+"]), "fun")
_reg("ascii_sword", lambda: "\n".join(["   /\\   ", "  /  \\  ", " /----\\ ", "/      \\", "|  ()  |", "\\______/"]), "fun")
_reg("fun_matrix_line", lambda: "".join(random.choice("01") for _ in range(80)), "fun")
_reg("fun_hack_line", lambda: f"[{random.randint(0, 9999):04d}] 0x{random.getrandbits(48):012X}", "fun")
_reg("fun_sudo", lambda: "Nice try, hacker. This incident will be reported.", "fun")
_reg("fun_coin_flip", lambda: random.choice(["Heads", "Tails"]), "fun")
_reg("fun_dice", lambda: random.randint(1, 6), "fun")
_reg("fun_magic8", lambda: random.choice(["Yes", "No", "Maybe", "Ask again later", "Definitely", "Never", "Signs point to yes", "Outlook not so good"]), "fun")
_reg("fun_quote", lambda: random.choice([
    "With great power comes great responsibility.",
    "The quieter you become, the more you are able to hear.",
    "Hack the planet!",
    "There is no spoon.",
    "Stay hungry, stay foolish.",
    "The best way to predict the future is to invent it.",
]), "fun")
_reg("fun_joke", lambda: random.choice([
    "Why do hackers wear glasses? Because they can't C#.",
    "There are 10 types of people: those who understand binary and those who don't.",
    "A SQL query walks into a bar, sees two tables and asks: 'Can I join you?'",
]), "fun")

_reg("color_green", lambda text: f"\033[92m{text}\033[0m", "colors")
_reg("color_red", lambda text: f"\033[91m{text}\033[0m", "colors")
_reg("color_yellow", lambda text: f"\033[93m{text}\033[0m", "colors")
_reg("color_blue", lambda text: f"\033[94m{text}\033[0m", "colors")
_reg("color_magenta", lambda text: f"\033[95m{text}\033[0m", "colors")
_reg("color_cyan", lambda text: f"\033[96m{text}\033[0m", "colors")
_reg("color_white", lambda text: f"\033[97m{text}\033[0m", "colors")
_reg("color_bold", lambda text: f"\033[1m{text}\033[0m", "colors")
_reg("color_dim", lambda text: f"\033[2m{text}\033[0m", "colors")
_reg("color_underline", lambda text: f"\033[4m{text}\033[0m", "colors")
_reg("color_blink", lambda text: f"\033[5m{text}\033[0m", "colors")
_reg("color_reverse", lambda text: f"\033[7m{text}\033[0m", "colors")
_reg("colorize", lambda text, code=92: f"\033[{code}m{text}\033[0m", "colors")

_reg("bit_and", lambda a, b: int(a) & int(b), "bits")
_reg("bit_or", lambda a, b: int(a) | int(b), "bits")
_reg("bit_xor", lambda a, b: int(a) ^ int(b), "bits")
_reg("bit_not", lambda a: ~int(a), "bits")
_reg("bit_shift_left", lambda a, n: int(a) << int(n), "bits")
_reg("bit_shift_right", lambda a, n: int(a) >> int(n), "bits")
_reg("bit_count", lambda a: bin(int(a)).count("1"), "bits")
_reg("bit_test", lambda a, n: bool(int(a) & (1 << int(n))), "bits")
_reg("bit_set", lambda a, n: int(a) | (1 << int(n)), "bits")
_reg("bit_clear", lambda a, n: int(a) & ~(1 << int(n)), "bits")
_reg("bit_toggle", lambda a, n: int(a) ^ (1 << int(n)), "bits")
_reg("int_to_bin", lambda a: bin(int(a)), "bits")
_reg("int_to_hex", lambda a: hex(int(a)), "bits")
_reg("int_to_oct", lambda a: oct(int(a)), "bits")
_reg("bin_to_int", lambda b: int(b, 2), "bits")

_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def _convert_base(value, source_base, target_base):
    text = str(value).strip().lower()
    sign = ""
    if text.startswith("-"):
        sign = "-"
        text = text[1:]
    try:
        number = int(text, source_base)
    except ValueError:
        return None
    if number == 0:
        return "0"
    result = ""
    while number:
        result = _DIGITS[number % target_base] + result
        number //= target_base
    return sign + result


for _source in range(2, 37):
    for _target in range(2, 37):
        if _source == _target:
            continue

        def _make(s, t):
            def _func(value):
                return _convert_base(value, s, t)

            return _func

        _reg(f"b{_source}_to_b{_target}", _make(_source, _target), "base-convert")


def _caesar(text, shift):
    result = []
    for char in str(text):
        if "a" <= char <= "z":
            result.append(chr((ord(char) - 97 + shift) % 26 + 97))
        elif "A" <= char <= "Z":
            result.append(chr((ord(char) - 65 + shift) % 26 + 65))
        else:
            result.append(char)
    return "".join(result)


for _shift in range(1, 27):
    _reg(f"caesar{_shift}", (lambda s: lambda v: _caesar(v, s))(_shift), "caesar")
    _reg(f"uncaesar{_shift}", (lambda s: lambda v: _caesar(v, -s))(_shift), "caesar")
