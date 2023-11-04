from pathlib import Path

from uniparser_yawarana import YawaranaAnalyzer, pos_list
from writio import load
from yawarana_helpers import pos_list

from pylacoan import Cleaner, Tokenizer, UniParser

conf = load("conf.yaml")
label = conf["mode"]
conf = conf[label]

morpho = UniParser(
    analyzer=YawaranaAnalyzer(cache=True),
    parse_col="srf",
    mask_ambiguity=conf.get("hide", False),
)


cleaner = Cleaner(
    replace={"¿ ": "¿", "¡ ": "¡"},
    strip=["#", "%", "¿", "¡", '"']
    # strip=[",", ".", ":", ";", "!", "-", "?", "“", "”", "’", "‘", '"', "¡"],
)
tokenizer = Tokenizer()

pipeline = [
    {"lvl": "precord", "label": "Speaker_ID", "key": "spk"},
    {
        "label": "Primary_Text",
        "lvl": "precord",
        "edit": True,
        "file": "transcriptions.yaml",
        "key": "ort",
    },
    {"lvl": "record", "label": "Text_ID", "hide": True, "key": "txt"},
    {
        "file": "translations.yaml",
        "label": "Translated_Text",
        "lvl": "translations",
        "edit": True,
        "key": "ftr",
    },
    {
        "file": "comments.yaml",
        "label": "Comment",
        "lvl": "record",
        "edit": True,
        "key": "cmt",
    },
    {"label": "Original_Translation", "lvl": "translations", "key": "oft"},
    cleaner,
    tokenizer,
    morpho,
    {"lvl": "word", "key": "ann", "label": "Annotations"},
    {"lvl": "word", "label": "Tokenized", "hide": True, "key": "srf"},
    {"label": "Analyzed_Word", "lvl": "word", "key": "obj"},
    {"label": "Gloss", "lvl": "word", "key": "gls"},
    {"label": "Part_Of_Speech", "lvl": "word", "key": "pos"},
    {"label": "Wordform_ID", "lvl": "word", "key": "wid", "hide": True},
    {"label": "Gramm", "lvl": "word", "key": "grm", "hide": True},
    {"lvl": "word", "label": "Morpheme_IDs", "hide": True, "key": "mid"},
    {"lvl": "word", "label": "Lexeme_IDs", "hide": True, "key": "lex"},
]

if conf.get("graid"):
    pipeline.append(
        {
            "file": "graid.yaml",
            "label": "GRAID",
            "ref": "srf",
            "lvl": "word",
            "edit": True,
            "key": "graid",
        }
    )
    pipeline.append(
        {
            "file": "refind.yaml",
            "label": "refind",
            "ref": "graid",
            "lvl": "word",
            "key": "refind",
            "split": True,
        },
    )

concordance = {"list_cols": ["mid", "grm"]}

if conf.get("graid"):
    concordance["file"] = "output/graid.csv"
else:
    concordance["file"] = "output/unsupervised_all.csv"

REC_LINK = "http://localhost:6543/sentences/{rec_id}"
INPUT_FILE = "all"
OUTPUT_FILE = f"{label}.csv"
FILTER = conf.get("filters", {})
AUDIO_PATH = Path("/home/florianm/Dropbox/research/cariban/yawarana/corpus/audio")
