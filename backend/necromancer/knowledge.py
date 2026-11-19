"""What changed between Python 2 / early Python 3 and Python 3.12.

Pure data, shared by the autopsy (detection) and the resurrection (repair).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from necromancer.models import MarkerCategory


@dataclass(frozen=True)
class Rule:
    kind: str
    category: MarkerCategory
    pattern: re.Pattern[str]
    hint: str
    # Optional deterministic replacement applied by the `api` fixer: (regex, replacement).
    fix: tuple[re.Pattern[str], str] | None = None


def _r(expr: str) -> re.Pattern[str]:
    return re.compile(expr)


# --------------------------------------------------------------------------- syntax
# Evaluated on code with string contents and comments blanked out.

SYNTAX_RULES: list[Rule] = [
    Rule(
        "print_statement",
        MarkerCategory.SYNTAX,
        _r(r"^\s*print(?:\s*$|\s+(?![\s=(\[.,)])|\s*>>)"),
        "print is a function in Python 3: print(...)",
    ),
    Rule(
        "except_comma",
        MarkerCategory.SYNTAX,
        _r(r"\bexcept\s+(?:\([^)]*\)|[\w.]+)\s*,\s*\w+\s*:"),
        "use `except Error as e:`",
    ),
    Rule(
        "raise_comma",
        MarkerCategory.SYNTAX,
        _r(r"^\s*raise\s+[\w.]+\s*,\s*\S"),
        "use `raise Error(message)`",
    ),
    Rule("backticks", MarkerCategory.SYNTAX, _r(r"`"), "backtick repr was removed; use repr()"),
    Rule("ne_operator", MarkerCategory.SYNTAX, _r(r"<>"), "`<>` was removed; use `!=`"),
    Rule(
        "exec_statement",
        MarkerCategory.SYNTAX,
        _r(r"^\s*exec\s+(?!\()[\w\"']"),
        "exec is a function in Python 3",
    ),
    Rule(
        "octal_literal",
        MarkerCategory.SYNTAX,
        _r(r"(?<![\w.])0[0-7]+(?![\w.])"),
        "octal literals need the 0o prefix",
    ),
    Rule(
        "long_suffix",
        MarkerCategory.SYNTAX,
        _r(r"(?<![\w.])\d+[lL](?!\w)"),
        "the long-integer suffix L was removed",
    ),
    Rule(
        "tuple_parameter",
        MarkerCategory.SYNTAX,
        _r(r"^\s*def\s+\w+\s*\([^)]*\(\s*\w+\s*,"),
        "tuple parameter unpacking was removed (PEP 3113)",
    ),
]

# Evaluated on the raw line because they concern string prefixes.
RAW_SYNTAX_RULES: list[Rule] = [
    Rule(
        "ur_prefix",
        MarkerCategory.SYNTAX,
        _r(r"(?<![\w\"'])[uU][rR][\"']"),
        "the ur'' string prefix was removed",
    ),
]

# --------------------------------------------------------------------------- builtins

BUILTIN_RULES: list[Rule] = [
    Rule("dict_iteritems", MarkerCategory.BUILTIN, _r(r"\.iteritems\s*\("), "use .items()"),
    Rule("dict_itervalues", MarkerCategory.BUILTIN, _r(r"\.itervalues\s*\("), "use .values()"),
    Rule("dict_iterkeys", MarkerCategory.BUILTIN, _r(r"\.iterkeys\s*\("), "use .keys() or iter(d)"),
    Rule("dict_has_key", MarkerCategory.BUILTIN, _r(r"\.has_key\s*\("), "use `key in d`"),
    Rule("xrange", MarkerCategory.BUILTIN, _r(r"(?<![\w.])xrange\s*\("), "use range()"),
    Rule("raw_input", MarkerCategory.BUILTIN, _r(r"(?<![\w.])raw_input\s*\("), "use input()"),
    Rule("unicode", MarkerCategory.BUILTIN, _r(r"(?<![\w.])unicode(?!\w)"), "use str"),
    Rule("basestring", MarkerCategory.BUILTIN, _r(r"(?<![\w.])basestring(?!\w)"), "use str"),
    Rule("long", MarkerCategory.BUILTIN, _r(r"(?<![\w.])long\s*\("), "use int()"),
    Rule("unichr", MarkerCategory.BUILTIN, _r(r"(?<![\w.])unichr\s*\("), "use chr()"),
    Rule("execfile", MarkerCategory.BUILTIN, _r(r"(?<![\w.])execfile\s*\("), "read + exec()"),
    Rule("file_builtin", MarkerCategory.BUILTIN, _r(r"(?<![\w.])file\s*\("), "use open()"),
    Rule("cmp_builtin", MarkerCategory.BUILTIN, _r(r"(?<![\w.])cmp\s*\("), "cmp() was removed"),
    Rule("apply_builtin", MarkerCategory.BUILTIN, _r(r"(?<![\w.])apply\s*\("), "call f(*args)"),
    Rule(
        "reduce_builtin",
        MarkerCategory.BUILTIN,
        _r(r"(?<![\w.])reduce\s*\("),
        "reduce moved to functools",
    ),
    Rule("iterator_next", MarkerCategory.BUILTIN, _r(r"\.next\s*\(\s*\)"), "use next(it)"),
    Rule("sys_maxint", MarkerCategory.BUILTIN, _r(r"\bsys\.maxint\b"), "use sys.maxsize"),
    Rule("getcwdu", MarkerCategory.BUILTIN, _r(r"\bos\.getcwdu\s*\("), "use os.getcwd()"),
    Rule(
        "string_letters",
        MarkerCategory.BUILTIN,
        _r(r"\bstring\.(?:letters|lowercase|uppercase)\b"),
        "use string.ascii_*",
    ),
]

# --------------------------------------------------------------------------- stdlib

REMOVED_MODULES: dict[str, str] = {
    # Python 2 names
    "urllib2": "urllib.request / urllib.error",
    "urlparse": "urllib.parse",
    "ConfigParser": "configparser",
    "StringIO": "io.StringIO",
    "cStringIO": "io.StringIO / io.BytesIO",
    "cPickle": "pickle",
    "Queue": "queue",
    "HTMLParser": "html.parser",
    "htmlentitydefs": "html.entities",
    "httplib": "http.client",
    "cookielib": "http.cookiejar",
    "Cookie": "http.cookies",
    "BaseHTTPServer": "http.server",
    "SimpleHTTPServer": "http.server",
    "SocketServer": "socketserver",
    "xmlrpclib": "xmlrpc.client",
    "commands": "subprocess",
    "thread": "_thread / threading",
    "dummy_thread": "_dummy_thread",
    "Tkinter": "tkinter",
    "tkMessageBox": "tkinter.messagebox",
    "anydbm": "dbm",
    "copy_reg": "copyreg",
    "repr": "reprlib",
    "md5": "hashlib",
    "sha": "hashlib",
    "sets": "built-in set",
    "exceptions": "builtins",
    "__builtin__": "builtins",
    "new": "types",
    "UserDict": "collections.UserDict",
    "UserList": "collections.UserList",
    "UserString": "collections.UserString",
    # Removed from Python 3.12
    "imp": "importlib",
    "distutils": "setuptools / sysconfig / shutil",
    "asyncore": "asyncio",
    "asynchat": "asyncio",
    "smtpd": "aiosmtpd",
    # Removed in Python 3.13 (deprecated in 3.12)
    "cgi": "email.message / urllib.parse",
    "cgitb": "traceback",
    "pipes": "shlex",
    "crypt": "hashlib / passlib",
    "telnetlib": "telnetlib3",
    "nntplib": "a third-party client",
    "imghdr": "filetype / puremagic",
    "sndhdr": "a third-party library",
    "audioop": "a third-party library",
    "uu": "base64",
    "xdrlib": "a third-party library",
    "msilib": "a third-party library",
    "spwd": "python-pam",
    "ossaudiodev": "a third-party library",
    "nis": "a third-party library",
    "chunk": "a third-party library",
    "aifc": "a third-party library",
    "sunau": "a third-party library",
    "mailcap": "mimetypes",
}

_MOD_ALT = "|".join(sorted((re.escape(m) for m in REMOVED_MODULES), key=len, reverse=True))

STDLIB_RULES: list[Rule] = [
    Rule(
        "removed_module",
        MarkerCategory.STDLIB,
        _r(rf"^\s*(?:import\s+(?:{_MOD_ALT})(?![\w.])|from\s+(?:{_MOD_ALT})(?:\.\w+)*\s+import)"),
        "module was renamed or removed",
    ),
    Rule(
        "urllib_py2_names",
        MarkerCategory.STDLIB,
        _r(
            r"^\s*from\s+urllib\s+import\s+.*\b(?:urlencode|quote|unquote|urlopen|"
            r"quote_plus|unquote_plus|urlretrieve)\b"
        ),
        "these moved to urllib.parse / urllib.request",
    ),
    Rule(
        "urllib_py2_attr",
        MarkerCategory.STDLIB,
        _r(r"\burllib\.(?:urlencode|quote|unquote|urlopen|quote_plus|unquote_plus|urlretrieve)\b"),
        "these moved to urllib.parse / urllib.request",
    ),
]

# --------------------------------------------------------------------------- APIs
# Removed or renamed APIs with a safe mechanical replacement.

_ABC = (
    "Mapping|MutableMapping|Sequence|MutableSequence|Set|MutableSet|Iterable|Iterator|"
    "Callable|Hashable|Sized|Container|Generator|Awaitable|Coroutine|AsyncIterable|"
    "AsyncIterator|ItemsView|KeysView|ValuesView|MappingView|ByteString"
)

API_RULES: list[Rule] = [
    Rule(
        "collections_abc",
        MarkerCategory.API,
        _r(rf"\bcollections\.(?:{_ABC})\b"),
        "ABCs moved to collections.abc (removed from collections in 3.10)",
        (_r(rf"\bcollections\.({_ABC})\b"), r"collections.abc.\1"),
    ),
    Rule(
        "collections_abc_import",
        MarkerCategory.API,
        _r(rf"^\s*from\s+collections\s+import\s+.*\b(?:{_ABC})\b"),
        "import ABCs from collections.abc",
    ),
    Rule(
        "base64_encodestring",
        MarkerCategory.API,
        _r(r"\bbase64\.(?:en|de)codestring\b"),
        "use base64.encodebytes / decodebytes",
        (_r(r"\bbase64\.(en|de)codestring\b"), r"base64.\1codebytes"),
    ),
    Rule(
        "inspect_getargspec",
        MarkerCategory.API,
        _r(r"\binspect\.getargspec\b"),
        "use inspect.getfullargspec",
        (_r(r"\binspect\.getargspec\b"), "inspect.getfullargspec"),
    ),
    Rule(
        "asyncio_async",
        MarkerCategory.API,
        _r(r"\basyncio\.async\s*\("),
        "use asyncio.ensure_future",
        (_r(r"\basyncio\.async\s*\("), "asyncio.ensure_future("),
    ),
    Rule(
        "asyncio_coroutine",
        MarkerCategory.API,
        _r(r"@asyncio\.coroutine\b"),
        "generator-based coroutines were removed in 3.11; use async def",
    ),
    Rule(
        "time_clock",
        MarkerCategory.API,
        _r(r"\btime\.clock\s*\("),
        "use time.perf_counter()",
        (_r(r"\btime\.clock\s*\("), "time.perf_counter("),
    ),
    Rule(
        "cgi_escape",
        MarkerCategory.API,
        _r(r"\bcgi\.escape\s*\("),
        "use html.escape",
    ),
    Rule(
        "logging_warn",
        MarkerCategory.API,
        _r(r"\b(?:logging|logger|log|LOG|LOGGER)\.warn\s*\("),
        "use .warning()",
        (_r(r"\b(logging|logger|log|LOG|LOGGER)\.warn\s*\("), r"\1.warning("),
    ),
    Rule(
        "unittest_aliases",
        MarkerCategory.API,
        _r(
            r"\bself\.(?:assertEquals|assertNotEquals|assertItemsEqual|assertRegexpMatches|"
            r"assertNotRegexpMatches|assertRaisesRegexp|assert_|failUnless|failIf|"
            r"failUnlessEqual|failIfEqual|assertAlmostEquals|assertNotAlmostEquals)\s*\("
        ),
        "deprecated unittest aliases were removed in 3.12",
    ),
    Rule(
        "fractions_gcd",
        MarkerCategory.API,
        _r(r"\bfractions\.gcd\s*\("),
        "use math.gcd",
    ),
    Rule(
        "array_tostring",
        MarkerCategory.API,
        _r(r"\.(?:tostring|fromstring)\s*\(\s*\)"),
        "array.tostring/fromstring were removed; use tobytes/frombytes",
    ),
    Rule(
        "cElementTree",
        MarkerCategory.API,
        _r(r"\bxml\.etree\.cElementTree\b"),
        "use xml.etree.ElementTree",
        (_r(r"\bxml\.etree\.cElementTree\b"), "xml.etree.ElementTree"),
    ),
    Rule(
        "platform_dist",
        MarkerCategory.API,
        _r(r"\bplatform\.(?:linux_distribution|dist)\s*\("),
        "removed in 3.8; use the `distro` package",
    ),
    Rule(
        "os_errno",
        MarkerCategory.API,
        _r(r"\bos\.errno\b"),
        "import errno directly",
        (_r(r"\bos\.errno\b"), "errno"),
    ),
    Rule(
        "yaml_load_unsafe",
        MarkerCategory.API,
        _r(r"\byaml\.load\s*\((?![^)]*Loader)"),
        "yaml.load without Loader is an error in PyYAML 6; use yaml.safe_load",
    ),
    Rule(
        "sys_setcheckinterval",
        MarkerCategory.API,
        _r(r"\bsys\.setcheckinterval\s*\("),
        "use sys.setswitchinterval",
    ),
    Rule(
        "html_parser_unescape",
        MarkerCategory.API,
        _r(r"HTMLParser\(\)\.unescape\s*\("),
        "use html.unescape",
    ),
]

UNITTEST_ALIASES: dict[str, str] = {
    "assertEquals": "assertEqual",
    "assertNotEquals": "assertNotEqual",
    "assertItemsEqual": "assertCountEqual",
    "assertRegexpMatches": "assertRegex",
    "assertNotRegexpMatches": "assertNotRegex",
    "assertRaisesRegexp": "assertRaisesRegex",
    "assert_": "assertTrue",
    "failUnless": "assertTrue",
    "failIf": "assertFalse",
    "failUnlessEqual": "assertEqual",
    "failIfEqual": "assertNotEqual",
    "assertAlmostEquals": "assertAlmostEqual",
    "assertNotAlmostEquals": "assertNotAlmostEqual",
}

ALL_CODE_RULES: list[Rule] = SYNTAX_RULES + BUILTIN_RULES + STDLIB_RULES + API_RULES
