from attrs import define
from uniparser_morph import Analyzer
import pandas as pd
from pathlib import Path
from clldutils import jsonlib
import questionary
import sys
from pyigt import IGT
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
        pass

    def parse_csv(self, file):
        df = pd.read_csv(file, keep_default_na=False)
        for i, row in df.iterrows():
            self.parse(row)
        jsonlib.dump(self.approved, self.approved_path)

@define
class Segmentizer(Annotator):
    segments: list = []
    tokenize: bool = True
    ignore: list = []
    delete: list = []
    col: str = "IPA"
    profile: Profile = None
    tokenizer: Tokenizer = None
    word_sep: str = " "
    input_col: str = "Orthographic"
    output_col: str = "IPA"

    def __attrs_post_init__(self):
        self.profile = Profile(*self.segments + [{"Grapheme": ig, self.col: ig} for ig in self.ignore] + [{"Grapheme": de, self.col: ""} for de in self.delete])
        self.tokenizer = Tokenizer(self.profile)

    def parse(self, record):
        if self.tokenize:
            record[self.output_col] = re.sub(' +', ' ', self.tokenizer(record, column=self.col))
        else:
            record[self.output_col] = self.tokenizer(record[self.input_col], column=self.col, segment_separator="", separator=self.word_sep)
        return record
@define
class UniParser(Annotator):

    interactive: bool = True
    prefer: str = "any"
    analyzer: str = "."
    word_sep: str = " "
    parse_col: str = "Sentence"
    trans: str = "Translated_Text"
    obj: str = "Analyzed_Word"
    gloss: str = "Gloss"
    overwrite_fields: bool = False
    unparsable: list = []
    punctuation: list = ['"', ","]

    def __attrs_post_init__(self):
        self.define_approved()
        if isinstance(self.analyzer, str):
            ana_path = self.analyzer
            self.analyzer = Analyzer()
            self.analyzer.lexFile = Path(ana_path, "lexemes.txt")
            self.analyzer.paradigmFile = Path(ana_path, "paradigms.txt")
            clitic_path = Path(ana_path, "clitics.txt")
            if clitic_path.is_file():
                self.analyzer.cliticFile = clitic_path
            self.analyzer.load_grammar()

    def parse_word(self, word):
        return self.analyzer.analyze_words(word)

    def write(self):
        with open(f"{self.name}_unparsable.txt", "w") as f:
            f.write("\n".join(set(self.unparsable)))
        jsonlib.dump(obj=self.approved, path=self.approved_path)

    def parse(self, record):
        log.info(f"""Parsing *{record[self.parse_col]}* ({record[self.id_s]})""")
        if self.trans not in record:
            log.info(f"No column {self.trans}, adding...")
            record[self.trans] = "Missing_Translation"
        if not self.overwrite_fields:
            for field_name in [self.obj, self.gloss]:
                if field_name in record:
                    log.error(f"Field '{field_name}' already exists")
                    raise FieldExistsException
        objs = []
        glosses = []
        for word in record[self.parse_col].split(self.word_sep):
            word = word.strip("".join(self.punctuation))
            if word.strip() == "":
                continue
            analyses = self.parse_word(word)
            if len(analyses) > 1 and self.interactive:
                found_past = False
                obj_choices = []
                gloss_choices = []
                for analysis in analyses:
                    potential_obj = objs + [analysis.wfGlossed]
                    potential_gloss = glosses + [analysis.gloss]
                    obj_choices.append(potential_obj)
                    gloss_choices.append(potential_gloss)
                    if record[self.id_s] in self.approved:
                        if (
                            word_sep.join(potential_gloss)
                            in self.approved[record][gloss_col]
                        ):
                            log.info(
                                f"""Using past analysis '{analysis.gloss}' for *{analysis.wf}* in {record["ID"]}"""
                            )
                            objs.append(analysis.wfGlossed)
                            glosses.append(analysis.gloss)
                            found_past = True
                if not found_past:
                    answers = []
                    for i, (obj, gloss) in enumerate(zip(obj_choices, gloss_choices)):
                        pad_obj, pad_gloss = pad_ex(
                            obj, gloss, as_list=True, tuple=True
                        )
                        answers.append(f"({i+1}) " + pad_obj + "\n       " + pad_gloss)
                    andic = {answer: i for i, answer in enumerate(answers)}
                    choice = questionary.select(
                        f""
                        f"Ambiguity while parsing *{word}*. Choose correct analysis for '{record[self.trans]}'"
                        "",
                        choices=answers,
                    ).ask()
                    analysis = analyses[andic[choice]]
                    objs.append(analysis.wfGlossed)
                    glosses.append(analysis.gloss)
            else:
                analysis = analyses[0]
                if analysis.wfGlossed == "":
                    log.warning(f"Unparsable: {analysis.wf}")
                    objs.append(analysis.wf)
                    glosses.append("***")
                    self.unparsable.append(analysis.wf)
                else:
                    objs.append(analysis.wfGlossed)
                    glosses.append(analysis.gloss)
        print(
            pad_ex(" ".join(objs), " ".join(glosses)),
            "‘" + record[self.trans] + "’",
            sep="\n",
        )
        record[self.obj] = self.word_sep.join(objs)
        record[self.gloss] = self.word_sep.join(glosses)
        if self.interactive:
            self.approved[record[self.id_s]] = dict(record)
        return record
