import logging
import re
import pandas as pd
import pygraid
from writio import load
import sys
from pyscl import parse
from writio import dump
from tqdm import tqdm
import jinja2


log = logging.getLogger(__name__)

record_level = ["rec", "spk", "txt"]
graidcols = ["type", "syn", "anim", "ref", "pred", "form", "func"]
cldf_dict = {
    "Analyzed_Word": "obj",
    "Primary_Text": "ort",
    "Gloss": "gls",
    "Lexeme_IDs": "lex",
    "Gramm": "grm",
    "Morpheme_IDs": "mid",
    "Part_Of_Speech": "pos",
    "GRAID": "graid",
    "Wordform_ID": "wid",
    "Tokenized": "srf",
    "ID": "rec",
    "Speaker_ID": "spk",
    "Text_ID": "txt",
    "Translated_Text": "ftr",
}


def search_word(word, query_dict):
    hits = [re.findall(q, word.get(k, "")) for k, q in query_dict.items()]
    if all([bool(value) if len(value) == 1 else False for value in hits]):
        return True
    return False


def empty_object(ann):
    if ann.get("ref", "np") == "0":
        return True
    return False


class CorpusFrame(pd.DataFrame):
    searchcol = "Object"
    annotated_cols = ["refind"]
    search_cols = []
    clause_list = []
    graid = None
    current_clause = None
    aligned_cols = [
        "obj",
        "gls",
        "pos",
        "grm",
        "lex",
        "mid",
        "wid",
        "graid",
        "refind",
    ]

    def __init__(
        self, data, resolve_graid_p_word=None, separate_clitics=True, **kwargs
    ):
        if isinstance(data, str):
            data = self.read_csv(data)
        self.aligned_cols = [x for x in self.aligned_cols if x in data.columns]
        if "graid" not in data.columns:
            self.search_cols = self.aligned_cols
        else:
            self.search_cols = self.aligned_cols + self.annotated_cols + graidcols
        if not separate_clitics:
            self.aligned_cols.append("srf")

        for col in self.aligned_cols:
            if not separate_clitics:
                data[col] = data[col].apply(lambda x: x.split("\t"))
            else:
                # data[col] = data[col].apply(lambda x: x.replace("=", "=WORTHIT"))
                data[col] = data[col].apply(lambda x: re.split("\t|=", x))
                # data[col] = data[col].apply(lambda x: [y.replace("WORTHIT", "=") for y in x])
        if resolve_graid_p_word:
            self.resolve_graid_p_word = resolve_graid_p_word
        # if "graid" in data.columns:
        #     # print(data[["refind", "graid"]])
        #     graid_data = pd.DataFrame.from_dict(
        #         self.get_graid_recs(data.to_dict("records"))
        #     ).fillna("")
        #     graid_data = self.add_clause_ids(graid_data.to_dict("records"))
        #     graid_data = self.get_information_status(graid_data)
        #     graid_data = pd.DataFrame.from_dict(graid_data).fillna("")
        #     self.graid = graid_data
        super().__init__(data, **kwargs)

    def read_csv(self, csv_file):
        df = load(csv_file)
        if "Analyzed_Word" in df.columns:
            df.rename(columns=cldf_dict, inplace=True, errors="ignore")
        else:
            log.error("Cannot interpret column names (Analyzed_Word?)")
            print(df)
            sys.exit()
        return df

    def get_information_status(self, rec_list):
        # topic persistence: how many reps in next 10 clauses?
        # referential distance: how many clauses since last mention?
        # come up with better informatoin status
        res = []
        found = []
        for rec in rec_list:
            if "refind" in rec and rec["refind"]:
                if rec["refind"] not in found:
                    found.append(rec["refind"])
                    rec["info"] = "new"
                else:
                    rec["info"] = "old"
            res.append(rec)
        return res

    def resolve_graid_p_word(self, word, graid, refind=[]):
        # print(word)
        res = []
        seps = ["-", "="]
        obj_items = re.split(rf"{'|'.join(seps)}", word["obj"])
        gls_items = re.split(rf"{'|'.join(seps)}", word["gls"])
        for obj, gls, ann in zip(obj_items, gls_items, graid):
            # print(obj, gls, ann)
            if "ref" in ann:
                ann["refind"] = refind.pop(0)
            res.append({**word, **{"obj": obj, "gls": gls}, **ann})
        return res

    def add_clause_ids(self, rec_list):
        clause_counters = {"main": 0, "subr": 0}
        res = []
        subrs = []
        for rec in rec_list:
            if rec["type"] == "main_clause":
                clause_counters["main"] += 1
                if subrs:
                    subrs.pop()
            elif rec["type"] == "subr_clause":
                clause_counters["subr"] += 1
                subrs.append(clause_counters["subr"])
                rec["subr_clause"] = clause_counters["subr"]
            elif rec["type"] == "subr_end":
                rec["subr_clause"] = subrs.pop()
            elif subrs:
                rec["subr_clause"] = subrs[-1]
            rec["clause"] = clause_counters["main"]
            res.append(rec)
        return res

    def add_record_param(self, item, rec):
        for k in record_level:
            item[k] = rec[k]
        return item

    def get_graid_recs(self, rec_list):
        graid_recs = []
        for rec in rec_list:
            graid_data = rec["graid"]
            word_idx = 0
            while word_idx < len(graid_data):
                ann_data = pygraid.parse_annotation(
                    graid_data[word_idx], mode="structured"
                ) or [[{}]]
                if "refind" in rec and rec["refind"]:
                    refind_data = rec["refind"][word_idx].split(" ")
                else:
                    refind_data = [""] * len(rec["srf"])
                # print("orig", rec["refind"], "pos", word_idx, "current", refind_data)
                for pre in ann_data["pre"]:
                    if "syn" in pre and refind_data:
                        pre["refind"] = refind_data.pop(0)
                    self.add_record_param(pre, rec)
                    graid_recs.append(pre)
                word_dict = {col: rec[col][word_idx] for col in self.aligned_cols}
                self.add_record_param(word_dict, rec)
                if len(ann_data["data"]) == 1:
                    graid_dict = ann_data["data"][0]
                    if "ref" in graid_dict:
                        word_dict["refind"] = refind_data.pop(0)
                    graid_recs.append({**word_dict, **graid_dict})
                else:
                    graid_recs.extend(
                        self.resolve_graid_p_word(
                            word=word_dict, graid=ann_data["data"], refind=refind_data
                        )
                    )
                for post in ann_data["post"]:
                    if "syn" in post and refind_data:
                        post["refind"] = refind_data.pop(0)
                    self.add_record_param(post, rec)
                    graid_recs.append(post)
                word_idx += 1
            if len(refind_data) > 0 and refind_data != [""]:
                log.warning(f"Leftover refind annotation(s): {refind_data}")
        return graid_recs

    def _tooltip(self, record, i, printcol):
        content = "&#013".join([f"{k}: {record[k][i]}" for k in self.aligned_cols])
        return f"""<span class="content show-tooltip" style="white-space: pre-line;" data-html="true" data-toggle="tooltip" data-placement="top" title="{content}">{record[printcol][i]}</span>"""

    def build_conc_line(
        self, record, start, end, context=5, printcol="obj", mode="rich"
    ):
        prefrom = start - context
        if prefrom < 0:
            prefrom = 0
        pre = slice(prefrom, start)
        postto = end + 1 + context
        if postto > len(record[printcol]):
            postto = len(record[printcol])
        post = slice(end + 1, postto)
        if mode == "rich":
            conc_dict = {
                "Record": f"""<a href="http://localhost:6543/sentences/{record["rec"]}">{record["rec"]}</a>""",
                # "Record": record["rec"],
                "Pre": " ".join(
                    [self._tooltip(record, i, printcol) for i in range(prefrom, start)]
                ),
                "Hit": "<b>"
                + " ".join(
                    [self._tooltip(record, x, printcol) for x in range(start, end + 1)]
                )
                + "</b>",
                "Post": " ".join(
                    [self._tooltip(record, i, printcol) for i in range(end + 1, postto)]
                ),
                "Translation": record["ftr"],
            }
        elif mode == "bare":
            conc_dict = {
                "Record": record["rec"],
                "Pre": " ".join([x for x in record[printcol][pre]]),
                "Hit": " ".join([x for x in record[printcol][start:end+1]]),
                "Post": " ".join([x for x in record[printcol][post]]),
                "Translation": record["ftr"],
            }
        return conc_dict

    def parse_graid_rec(self, rec, mode="full"):
        if "graid" not in rec:
            return rec
        for gcol in graidcols:
            rec[gcol] = []
        wi = 0
        while wi < len(rec[self.search_cols[0]]):  # p-word index
            ann = rec["graid"][wi]
            # print(wi, ann, rec["graid"])
            if ann == "":
                for gcol in graidcols:
                    rec[gcol].append("")
            else:
                annotations = pygraid.parse_annotation(ann)
                for annotation_group in annotations:
                    if mode == "words":
                        annotation_group = annotation_group[0:1]  # todo fix this
                    for ann_dict in annotation_group:
                        # print(ann_dict)
                        if ann_dict["type"] in ["boundary"]:
                            if not self.current_clause:
                                self.current_clause = 1
                            else:
                                self.current_clause += 1
                        ann_dict["clause"] = self.current_clause
                        if empty_object(ann_dict):
                            for wcol in self.aligned_cols + ["graid"]:
                                if wcol == "obj":
                                    rec[wcol].insert(wi, "0")
                                elif wcol != "refind":
                                    rec[wcol].insert(wi, "")
                        for gcol in graidcols:
                            rec[gcol].append(ann_dict.get(gcol, ""))
            wi += 1
        return rec

    def pprint(self, dic):
        from terminaltables import AsciiTable

        singles = []
        lists = [[dic.get("ID", dic.get("id", "field")), "value"]]
        for k, v in dic.items():
            if not isinstance(v, list):
                singles.append(f"{k}: {v} ({len(v)})")
        for col in self.aligned_cols:
            lists.append([col, *dic[col]])
        lists[0].extend([" "] * (len(lists[1]) - 1))
        table = AsciiTable(lists)
        print(table.table)

    def iter_words(self, rec, cols):
        # print(rec["grm"], rec["pos"], sep="\n")
        # self.pprint(rec)
        cols = [x for x in cols if x in rec]
        assert len(rec["grm"]) == len(rec["pos"])
        for idx in range(0, len(rec[cols[0]])):
            yield idx, {k: rec[k][idx] for k in cols}

    def query(
        self,
        query_string,
        full_context=False,
        name=None,
        print_concordance=True,
        mode="pandas",
        **kwargs,
    ):
        tokens = parse(query_string)
        print(tokens)
        alternatives = [f'[obj="{query_string}"]']
        i = 0
        while not tokens:
            query_string = alternatives[i]
            tokens = parse(query_string)
            i += 1
            if i >= len(alternatives):
                return f"Invalid query: '{query_string}'"
        rec_dics = {}
        for i, rec in tqdm(enumerate(self.to_dict("records"))):
            rec_dics[i] = []
            for idx, dic in self.iter_words(rec, self.aligned_cols):
                rec_dics[i].append({**dic, **{"idx": idx, "i": i}})

        kwics = []
        bare_kwics = []
        for rec_idx, word_dics in rec_dics.items():
            start = None
            i = 0
            j = 0
            while i < len(word_dics) and j < len(
                tokens
            ):  # iterating through words in record and tokens
                # print(f"comparing record {rec_idx}:{i} with token {j}")
                if tokens[j].match(word_dics[i]):  # a (partial) hit
                    # print(f"token {j} matches {rec_idx}:{i}")
                    if start is None:
                        start = i
                        # print(f"Searching from {rec_idx}:{start}")
                    if j == len(tokens) - 1:
                        # print(self.iloc[rec_idx])
                        # print(f"Hit at {rec_idx}:{start}-{i} ({j})")
                        kwics.append(
                            self.build_conc_line(self.iloc[rec_idx], start=start, end=i)
                        )
                        bare_kwics.append(
                            self.build_conc_line(
                                self.iloc[rec_idx], start=start, end=i, mode="bare"
                            )
                        )
                        j = 0
                        start = None
                    else:
                        j += 1
                else:
                    # print("no hit")
                    j = 0
                    start = None
                i += 1
        if kwics:
            kwics = pd.DataFrame(kwics)
            if print_concordance and name:
                loader = jinja2.FileSystemLoader(searchpath="concserve/templates/")
                env = jinja2.Environment(loader=loader)
                template = env.get_template("view.j2")
                res = template.render(
                    {
                        "content": kwics.to_html(index=False, escape=False),
                        "legend": f"Search results for {query_string}",
                    }
                )
                dump(res, f"concordances/{name}.html")
        if bare_kwics:
            dump(bare_kwics, f"concordances/{name}.csv")
        if len(kwics) > 0 and mode == "html":
            return kwics.to_html(index=False, escape=False)
        return f"No results for '{query_string}'"
