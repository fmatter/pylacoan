import logging
import re
from itertools import groupby
from pathlib import Path
import pandas as pd
import questionary
from attrs import define
from clldutils import jsonlib
from segments import Profile
from segments import Tokenizer
from uniparser_morph import Analyzer
from pylacoan.helpers import ortho_strip
import sys

log = logging.getLogger(__name__)


def pad_ex(obj, gloss, tuple=False, as_list=False):
    out_obj = []
    out_gloss = []
    if not as_list:
        zipp = zip(obj.split(" "), gloss.split(" "))
    else:
        zipp = zip(obj, gloss)
    for o, g in zipp:
        diff = len(o) - len(g)
        if diff < 0:
            o += " " * -diff
        else:
            g += " " * diff
        out_obj.append(o)
        out_gloss.append(g)
    if tuple:
        return "  ".join(out_obj).strip(" "), "  ".join(out_gloss).strip(" ")
    else:
        return "  ".join(out_obj).strip(" ") + "\n" + "  ".join(out_gloss).strip(" ")


OUTPUT_DIR = Path("output")
INPUT_DIR = Path("input")
IDX_COL = "ID"

def define_file_path(file, base_dir):
    if "/" in file:
        return [Path(file)]
    elif file == "all":
        return [Path(x) for x in base_dir.iterdir() if x.is_file()]
    else:
        return [Path(base_dir, file)]


def run_pipeline(parser_list, in_f, out_f):
    file_paths = define_file_path(in_f, INPUT_DIR)
    out_path = OUTPUT_DIR / out_f
    for file in file_paths:
        if ".csv" in file:
            df = pd.read_csv(file, index_col=IDX_COL, keep_default_na=False)
            for parser in parser_list:
                output = []
                for record in df.to_dict(orient="records"):
                    output.append(parser.parse(record))
                df = pd.DataFrame.from_dict(output)
                parser.write()
    df.to_csv(out_path, index=False)

def reparse(parser_list, out_f, record_id):
    df = pd.read_csv(OUTPUT_DIR / out_f, index_col=IDX_COL, keep_default_na=False)
    if record_id not in df.index:
        log.error(f"No record with the ID {record_id} found in {out_f}")
        sys.exit(1)
    record = df.loc[record_id]
    for parser in parser_list:
        df.loc[record.name] = parser.parse(record)
    df.to_csv(OUTPUT_DIR / out_f)

@define
class Writer:
    file: str = None

    def __attrs_post_init__(self):
        if not self.file:
            self.file = "parse_output.txt"

    def write(self, data):
        with open(self.file, "w") as file_w:
            file_w.write(data)


class PandasWriter:
    def write(self, data):
        data.to_csv(self.file, index=False)


class FieldExistsException(Exception):
    pass


@define
class Annotator:

    approved: dict = {}
    name: str = "unnamed_parser"
    approved_path: str = None
    out_file: str = None
    writer = None
    interactive: bool = True

    def define_out_file(self):
        if not self.out_file:
            self.out_file = Path("output", f"{self.name}_output.csv")

    def define_approved(self):
        if not self.approved_path:
            self.approved_path = self.name + "_approved.json"
        self.approved_path = Path(self.approved_path)
        if self.approved_path.is_file():
            self.approved = jsonlib.load(self.approved_path)

    def __attrs_post_init__(self):
        self.define_approved()

    def clear(self, record_id):
        if record_id in self.approved:
            del self.approved[record_id]


    def parse(self, input):
        return input

    def write(self):
        if self.interactive and self.approved != {}:
            jsonlib.dump(self.approved, self.approved_path)
        pass

    def parse_csv(self, file):
        df = pd.read_csv(file, keep_default_na=False)
        for i, row in df.iterrows():
            self.parse(row)


@define
class Segmentizer(Annotator):
    segments: list = []
    tokenize: bool = True
    ignore: list = []
    delete: list = []
    profile: Profile = None
    profile_col: str = "IPA"
    tokenizer: Tokenizer = None
    word_sep: str = " "
    input_col: str = "Orthographic"
    output_col: str = "IPA"
    complain: bool = True

    def __attrs_post_init__(self):
        self.profile = Profile(
            *self.segments
            + [{"Grapheme": ig, self.profile_col: ig} for ig in self.ignore]
            + [{"Grapheme": de, self.profile_col: ""} for de in self.delete]
        )
        self.tokenizer = Tokenizer(self.profile)

    def parse(self, record):
        record[self.output_col] = self.parse_string(record[self.input_col])
        return record

    def parse_string(self, input_str):
        if self.tokenize:
            return re.sub(" +", " ", self.tokenizer(input_str, column=self.profile_col))
        else:
            res = self.tokenizer(
                input_str,
                column=self.profile_col,
                segment_separator="",
                separator=self.word_sep,
            )
            if self.complain and "�" in res:
                log.warning(f"Could not convert {input_str}: {res}")
            return res


@define
class UniParser(Annotator):

    prefer: str = "any"
    analyzer: str = "."
    word_sep: str = " "
    parse_col: str = "Sentence"
    trans: str = "Translated_Text"
    uniparser_fields: dict = {
        "Analyzed_Word": "wfGlossed",
        "Gloss": "gloss",
        "Lemmata": "lemma",
        "Gramm": "gramm",
    }
    obj: str = "Analyzed_Word"
    gloss: str = "Gloss"
    gramm: str = "Gramm"
    overwrite_fields: bool = False
    unparsable_path: str = None
    unparsable: list = []
    punctuation: list = ['"', ","]
    lexFile: str = None
    paradigmFile: str = None
    delAnaFile: str = None

    def _get_field(self, wf, field):
        field_dic = {
            "wf": wf.wf,
            "wfGlossed": wf.wfGlossed,
            "gloss": wf.gloss,
            "lemma": wf.lemma,
            "gramm": wf.gramm,
        }
        if field not in field_dic:
            for f, v in wf.otherData:
                if f == field:
                    return v
            return ""
        else:
            return field_dic[field]

    def _define_unparsable(self):
        if not self.unparsable_path:
            self.unparsable_path = self.name + "_unparsable.txt"

    def __attrs_post_init__(self):
        self.define_approved()
        self._define_unparsable()
        if isinstance(self.analyzer, str):
            ana_path = self.analyzer
            self.analyzer = Analyzer()
            if not self.lexFile:
                self.analyzer.lexFile = Path(ana_path, "lexemes.txt")
            else:
                self.analyzer.lexFile = self.lexFile
            if not self.paradigmFile:
                self.analyzer.paradigmFile = Path(ana_path, "paradigms.txt")
            else:
                self.analyzer.paradigmFile = self.paradigmFile
            if not self.delAnaFile:
                self.analyzer.delAnaFile = Path(ana_path, "bad_analyses.txt")
            else:
                self.analyzer.delAnaFile = self.delAnaFile
            clitic_path = Path(ana_path, "clitics.txt")
            if clitic_path.is_file():
                self.analyzer.cliticFile = clitic_path
            self.analyzer.load_grammar()

    def parse_word(self, word, **kwargs):
        return self.analyzer.analyze_words(word, **kwargs)

    def write(self):
        unparsable_counts = [
            (i, len(list(c))) for i, c in groupby(sorted(self.unparsable))
        ]
        unparsable_counts = sorted(unparsable_counts, key=lambda x: x[1], reverse=True)
        self.unparsable = [x for x, y in unparsable_counts]
        with open(f"{self.unparsable_path}", "w") as f:
            f.write("\n".join(self.unparsable))
        if self.interactive:
            jsonlib.dump(obj=self.approved, path=self.approved_path)

    def parse(self, record):
        log.info(f"""Parsing {record[self.parse_col]} ({record.name})""")
        if self.trans not in record:
            log.info(f"No column {self.trans}, adding...")
            record[self.trans] = "Missing_Translation"
        if not self.overwrite_fields:
            for field_name in self.uniparser_fields.keys():
                if field_name in record:
                    log.error(f"Field '{field_name}' already exists")
                    raise FieldExistsException
        added_fields = {}
        for field_name in self.uniparser_fields.values():
            added_fields[field_name] = []
        unparsable = []
        gained_approval = False
        all_analyses = self.parse_word(
            ortho_strip(record[self.parse_col])
            .strip(self.word_sep)
            .split(self.word_sep)
        )
        for wf_analysis in all_analyses:
            if len(wf_analysis) > 1:
                found_past = False
                obj_choices = []
                gloss_choices = []
                for potential_analysis in wf_analysis:
                    potential_obj = added_fields["wfGlossed"] + [
                        potential_analysis.wfGlossed
                    ]
                    potential_gloss = added_fields["gloss"] + [potential_analysis.gloss]
                    obj_choices.append(potential_obj)
                    gloss_choices.append(potential_gloss)
                    if record.name in self.approved:
                        if (
                            self.word_sep.join(potential_gloss)
                            in self.approved[record.name][self.gloss]
                        ):
                            log.info(
                                f"""Using past analysis '{potential_analysis.gloss}' for *{potential_analysis.wf}* in {record.name}"""
                            )
                            analysis = potential_analysis
                            found_past = True
                if not found_past:
                    if self.interactive:
                        answers = []
                        for i, (obj, gloss) in enumerate(
                            zip(obj_choices, gloss_choices)
                        ):
                            pad_obj, pad_gloss = pad_ex(
                                obj, gloss, as_list=True, tuple=True
                            )
                            answers.append(
                                f"({i+1}) " + pad_obj + "\n       " + pad_gloss
                            )
                        andic = {answer: i for i, answer in enumerate(answers)}
                        choice = questionary.select(
                            f""
                            f"{record.name}: ambiguity while parsing *{wf_analysis[0].wf}*. Choose correct analysis for\n{record[self.parse_col]}\n'{record[self.trans]}'"
                            "",
                            choices=answers,
                        ).ask()
                        analysis = wf_analysis[
                            andic[choice]
                        ]  # pylint: disable=unsubscriptable-object
                        gained_approval = True
                    else:
                        analysis = wf_analysis[
                            0
                        ]  # pylint: disable=unsubscriptable-object
            else:
                analysis = wf_analysis[0]  # pylint: disable=unsubscriptable-object
            if analysis.wfGlossed == "":
                unparsable.append(analysis.wf)
                for field_name in self.uniparser_fields.values():
                    if field_name == "wfGlossed":
                        added_fields[field_name].append(analysis.wf)
                    else:
                        added_fields[field_name].append("***")
            else:
                for field_name in self.uniparser_fields.values():
                    added_fields[field_name].append(
                        self._get_field(analysis, field_name)
                    )
        pretty_record = (
            pad_ex(" ".join(added_fields["wfGlossed"]), " ".join(added_fields["gloss"]))
            + "\n"
            + "‘"
            + record[self.trans]
            + "’"
        )
        if len(unparsable) > 0:
            log.warning(
                f"Unparsable: {', '.join(unparsable)} in {record.name}:\n{pretty_record}"
            )
            self.unparsable.extend(unparsable)
        else:
            log.info(f"\n{pretty_record}")
        for output_name, field_name in self.uniparser_fields.items():
            record[output_name] = self.word_sep.join(added_fields[field_name])
        if self.interactive and gained_approval:
            self.approved[record.name] = {key: value for key, value in dict(record).items() if key in [self.gloss, self.obj, self.gramm]}
            jsonlib.dump(
                self.approved, self.approved_path, indent=4, ensure_ascii=False
            )
        return record
