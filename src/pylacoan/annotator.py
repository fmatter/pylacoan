from attrs import define
from uniparser_morph import Analyzer
import pandas as pd
from pathlib import Path
from clldutils import jsonlib
import questionary
import logging
from segments import Tokenizer, Profile
import re


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


OUTPUT_DIR = "output"
INPUT_DIR = "input"


def define_file_path(file, base_dir):
    if "/" in file:
        return Path(file)
    else:
        return Path(base_dir, file)


def run_pipeline(file_dict):
    for file, file_conf in file_dict.items():
        file_path = define_file_path(file, INPUT_DIR)
        out_path = define_file_path(file_conf["output_file"], OUTPUT_DIR)
        if ".csv" in file:
            df = pd.read_csv(file_path, keep_default_na=False)
            for parser in file_conf["parsers"]:
                output = []
                for record in df.to_dict(orient="records"):
                    output.append(parser.parse(record))
                df = pd.DataFrame.from_dict(output)
                parser.write()
        df.to_csv(out_path, index=False)


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

    id_s = "ID"
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

    def parse_string(self, str):
        if self.tokenize:
            return re.sub(" +", " ", self.tokenizer(str, column=self.profile_col))
        else:
            return self.tokenizer(
                str,
                column=self.profile_col,
                segment_separator="",
                separator=self.word_sep,
            )


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
                if f==field:
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

    def parse_word(self, word):
        return self.analyzer.analyze_words(word)

    def write(self):
        with open(f"{self.unparsable_path}", "w") as f:
            f.write("\n".join(set(self.unparsable)))
        if self.interactive:
            jsonlib.dump(obj=self.approved, path=self.approved_path)

    def parse(self, record):
        log.info(f"""Parsing {record[self.parse_col]} ({record[self.id_s]})""")
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
        for word in record[self.parse_col].split(self.word_sep):
            word = word.strip("".join(self.punctuation))
            if word.strip() == "":
                continue
            analyses = self.parse_word(word)
            if len(analyses) > 1:
                found_past = False
                obj_choices = []
                gloss_choices = []
                for potential_analysis in analyses:
                    potential_obj = added_fields["wfGlossed"] + [potential_analysis.wfGlossed]
                    potential_gloss = added_fields["gloss"] + [potential_analysis.gloss]
                    obj_choices.append(potential_obj)
                    gloss_choices.append(potential_gloss)
                    if record[self.id_s] in self.approved:
                        if (
                            self.word_sep.join(potential_gloss)
                            in self.approved[record["ID"]][self.gloss]
                        ):
                            log.info(
                                f"""Using past analysis '{potential_analysis.gloss}' for *{potential_analysis.wf}* in {record["ID"]}"""
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
                            f"Ambiguity while parsing *{word}*. Choose correct analysis for '{record[self.trans]}'"
                            "",
                            choices=answers,
                        ).ask()
                        analysis = analyses[andic[choice]]
                        gained_approval = True
                    else:
                        analysis = analyses[0]
            else:
                analysis = analyses[0]
            if analysis.wfGlossed == "":
                unparsable.append(analysis.wf)
                for field_name in self.uniparser_fields.values():
                    added_fields[field_name].append("***")
            else:
                for field_name in self.uniparser_fields.values():
                    added_fields[field_name].append(self._get_field(analysis, field_name))
        pretty_record = (
            pad_ex(" ".join(added_fields["wfGlossed"]), " ".join(added_fields["gloss"]))
            + "\n"
            + "‘"
            + record[self.trans]
            + "’"
        )
        if len(unparsable) > 1:
            log.warning(
                f"Unparsable: {', '.join(unparsable)} in {record['ID']}:\n{pretty_record}"
            )
        else:
            log.info("\n" + pretty_record)
        for output_name, field_name in self.uniparser_fields.items():
            record[output_name] = self.word_sep.join(added_fields[field_name])
        if self.interactive and gained_approval:
            self.approved[record[self.id_s]] = dict(record)
            jsonlib.dump(self.approved, self.approved_path)
        return record
