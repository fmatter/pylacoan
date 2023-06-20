import logging
from pathlib import Path
import pandas as pd
import pygraid
from conf import pipeline
from conf import pos_list
from flask import Flask
from flask import render_template
from flask import request
from flask import send_from_directory
from writio import dump
from pylacoan.annotator import UniParser
from pylacoan.helpers import add_wid
from pylacoan.helpers import get_pos
from pylacoan.helpers import insert_pos_rec
from pylacoan.helpers import load_annotations, printdict
from pylacoan.helpers import load_data
from pylacoan.helpers import render_graid
from pylacoan.helpers import run_pipeline


log = logging.getLogger(__name__)

AUDIO_PATH = Path(
    "/home/florianm/Dropbox/research/cariban/yawarana/yawarana_corpus/audio"
)

app = Flask(__name__, static_url_path="/static")
wlog = logging.getLogger("werkzeug")
wlog.setLevel(logging.ERROR)

fields = {x["key"]: x for x in pipeline if isinstance(x, dict)}

data = load_data(
    rename={
        "Primary_Text": "ort",
        "Translated_Text": "oft",
        "Speaker_ID": "spk",
        "Text_ID": "txt",
    }
)

uniparser = None
for p in pipeline:
    if isinstance(p, UniParser):
        uniparser = p

annotations = {}
data = run_pipeline(data, annotations, pipeline, pos_list)
data.index = data["ID"]
audios = []
for x in AUDIO_PATH.iterdir():
    audios.append(x.stem)
data["audio"] = data["ID"].apply(lambda x: x in audios)
splitcols = [
    "obj",
    "gls",
    # "grm",
    "graid",
    # "refind",
    # "lex",
    # "mid",
    "pos",
    # "wid",
    # "ana",
    # "anas",
    "srf",
]
aligned_fields = [x for x in splitcols if x not in []]


def parse_graid(df, target="all"):
    open_clause = False
    clause_initial = []
    current_main = ""
    current_subr = ""
    for i, (r_id, ex) in enumerate(df.iterrows()):
        if ex["graid"] == "" or ex["graid"] is None:
            ex["graid"] = ["##"] + ([""] * (len(ex["srf"]) - 1))
        if "refind" in ex:
            if ex["refind"] == "" or ex["refind"] is None:
                ex["refind"] = [""] * (len(ex["srf"]))
        if "graid" in ex and ex["graid"]:
            x = 0
            while ex["graid"][x] is None:
                x += 1
            if ex["graid"][x].startswith("##"):
                clause_initial.append(i)
    for i, (r_id, ex) in enumerate(df.iterrows()):
        if (
            i + 1 in clause_initial
            or i + 1 >= len(df)
            or df.iloc[i + 1]["txt"] != ex["txt"]
        ):
            initial = True
        else:
            initial = False
        if target != "all" and target != r_id:
            continue
        ex = render_graid(
            ex,
            initial=initial,
            aligned_fields=aligned_fields,
            empty=None,
            special_empty={"anas": {}},
            open_clause=open_clause,
            current_main=current_main,
            current_subr=current_subr,
        )
        yield ex


text_dic = {}
if "graid" in data.columns:
    data = pd.DataFrame.from_dict(parse_graid(data))
for text_id, textdata in data.groupby("txt"):
    text_dic[text_id] = list(textdata.index)


def save():
    for key, field in fields.items():
        if "file" not in field:
            continue
        dump(annotations[key], field["file"])


def defill(rec):
    for target in splitcols:
        if target not in rec or not rec[target]:
            continue
        rec[target] = [x for x in rec[target] if x is not None]
    return rec


def reparse(ex_id, target):
    print("Reparsing", ex_id)
    if target == "ort":
        for parser in pipeline:
            if isinstance(parser, dict):
                continue
            data.loc[ex_id] = parser.parse(data.loc[ex_id])
        data.loc[ex_id] = insert_pos_rec(data.loc[ex_id], pos_list=pos_list)
        data.loc[ex_id] = add_wid(data.loc[ex_id])
        load_annotations(key="graid", field=fields["graid"], data=data, rec_id=ex_id)
    if target in ["ort", "graid"]:
        res = list(parse_graid(data, target=ex_id))
        return res[0]
    return data.loc[ex_id]


@app.route("/example")
def example():
    exid = request.args.get("id")
    ex = data.loc[exid]
    field_data = {"precord": {}, "record": {}, "word": {}, "translations": {}}
    for key, field in fields.items():
        if key not in ex:
            continue
        field_data.setdefault(field["lvl"], {})
        field_data[field["lvl"]][key] = field
    return render_template("record.html", ex=ex, fields=field_data, top_align="ann")


@app.route("/graid")
def graid_string():
    return pygraid.to_string(request.args.get("annotation"))


@app.route("/audio/<path:filename>")
def audio(filename):
    return send_from_directory(AUDIO_PATH, filename)


@app.route("/texts")
def texts():
    return list(text_dic.keys())


@app.route("/textrecords")
def textrecords():
    text_id = request.args.get("textID")
    return text_dic[text_id]


@app.route("/export")
def export():
    defilled_data = data.apply(defill, axis=1)
    defilled_data.drop(columns=["ann", "audio", "ana", "anas"], inplace=True)
    for col in splitcols:
        if col in defilled_data.columns:
            if isinstance(defilled_data[col].iloc[0][0], list):
                defilled_data[col] = defilled_data[col].apply(
                    lambda x: [",".join(y) for y in x]
                )
            defilled_data[col] = defilled_data[col].apply(lambda x: "\t".join(x))
    for key, field_data in fields.items():
        if key in defilled_data.columns and "label" in field_data:
            defilled_data.rename(columns={key: field_data["label"]}, inplace=True)
    defilled_data.to_csv("output/test.csv", index=False)
    return {}


def set_up_choice(rec, orig_pos, shifted_pos, choice):
    print(rec)
    print("orig", orig_pos)
    print("shifted", shifted_pos)
    if rec["anas"][int(orig_pos)][choice] != "?":
        for field in ["obj", "gls", "lex", "grm", "mid"]:
            rec[field][int(orig_pos)] = rec["anas"][int(orig_pos)][choice].get(field, "")
        rec["pos"][int(orig_pos)] = get_pos(rec["grm"][int(orig_pos)], pos_list)
        uniparser.register_choice(
            rec["ID"], orig_pos, rec["anas"][int(orig_pos)][choice]["srf"], choice
        )
    else:
        for field in ["gls", "lex", "grm", "mid", "pos"]:
            rec[field][int(orig_pos)] = "?"
        uniparser.discard_choice(rec["ID"], orig_pos)
    rec["ana"][int(orig_pos)] = choice


@app.route("/pick")
def pick():
    choice = request.args.get("choice")
    target = request.args.get("target")
    values = target.split("_")
    r_id, key, orig_pos, shifted_pos = values
    # print("Picking", choice, r_id, key, orig_pos, shifted_pos)
    set_up_choice(data.loc[r_id], orig_pos, shifted_pos, choice)
    ex = data.loc[r_id]
    field_data = {}
    for key, field in fields.items():
        if key not in ex:
            continue
        field_data.setdefault(field["lvl"], {})
        field_data[field["lvl"]][key] = field
    return render_template("record.html", ex=ex, fields=field_data, top_align="ann")


@app.route("/update")
def update():
    value = request.args.get("value")
    target = request.args.get("target")
    values = target.split("_")
    if len(values) == 1:
        raise ValueError(target)
    elif len(values) == 2:
        # print("updating", value, target, values)
        r_id, key = values
        data.at[r_id, key] = value
        if value:
            # print("setting", key, "annotation for", r_id, "to", value)
            annotations[key][r_id] = value
        elif r_id in annotations[key]:
            # print("empty value, deleting", key, "for", r_id)
            del annotations[key][r_id]
        else:
            print(r_id, "is not in", annotations[key])
            raise ValueError(r_id)
        data.loc[r_id] = defill(data.loc[r_id])
        data.loc[r_id] = reparse(r_id, target=key)
    elif len(values) == 3:
        r_id, key, pos = values
        pos = int(pos)
        data.loc[r_id] = defill(data.loc[r_id])
        data.at[r_id, key][pos] = value
        if value:
            ref_value = data.at[r_id, fields[key]["ref"]][pos]
            annotations[key].setdefault(r_id, {})
            annotations[key][r_id].setdefault(pos, {})
            annotations[key][r_id][pos][ref_value] = value
        elif key in annotations and pos in annotations[key][r_id]:
            del annotations[key][r_id][pos]
        data.loc[r_id] = reparse(r_id, target=key)
    save()
    return {"updated": r_id}


def build_example_div(ex_ids, audio=None):
    ex = data.loc[ex_ids]
    field_data = {}
    for key, field in fields.items():
        if key not in ex:
            continue
        field_data.setdefault(field["lvl"], {})
        field_data[field["lvl"]][key] = field
    return render_template(
        "index.html", exes=ex.to_dict("records"), fields=field_data, top_align="ann"
    )


@app.route("/")
def index():
    return render_template(
        "index.html", example_ids=[f"ctorat-{i+1}" for i in range(46)]
    )
    return render_template(
        "index.html", example_ids=[f"convrisamaj-{i+1}" for i in range(53)]
    )
    return render_template(
        "index.html", example_ids=[f"histanfo-{i+1}" for i in range(55)]
    )
    return render_template(
        "index.html", example_ids=[f"convsuenmaj-{i+1}" for i in range(135)]
    )


def run_server():
    app.run(debug=False, port=5001)
