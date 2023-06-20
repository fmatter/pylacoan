class RecordAnnotator(Annotator):
    target = None

    def __init__(self, fix=False, target=None, **kwargs):
        self.fix = fix
        self.path = Path(f"{self.filename}.yaml")
        if self.path.is_file():
            self.data = load(self.path)
        else:
            self.data = {}
        if target:
            self.target = target
        self.data_setup()

    def print_record(self, record, **kwargs):
        print_record(record, **kwargs)

    def parse(self, record):
        data = self.data.get(record[self.id_key], None)
        if data is None or self.fix:
            self.print_record(record)
            data = questionary.text(self.prompt, default=data or "").ask()
            self.data[record[self.id_key]] = data
        record[self.target] = data or ""
        dump(self.data, self.path)
        return record

    def write(self):
        dump(self.data, self.path)


class WordAnnotator(Annotator):
    files = {"ignore": set(), "cache": {}, "annotated": {}, "skip": []}

    def __init__(self, fix=False, interactive=True, parse_col="obj", **kwargs):
        self.data_setup(**kwargs)
        self.parse_col = parse_col
        self.fix = fix
        self.interactive = interactive

    def identify(self, values):
        """A method for generating word identifiers"""
        return values[0] + ":" + values[1]

    def cache_suggestion(self, value):
        if value in self.cache:
            return favorite(self.cache[value])
        return ""

    def is_target(self, s):
        if s in self.ignore:
            return False
        return True

    def suggestion(self, wf):
        """A method for filling in some information into the prompt field"""
        return ""

    def find_suggestion(self, value, rec):
        return self.cache_suggestion(value) or self.suggestion(rec)

    def prompt_at_position(self, ex, pos, prompt, pre_fill=""):
        print_record(ex, highlight_pos=pos)
        # for i in range(0, pos):
        #     lines = [len(line[i]) for key, line in ex.items() if key in ["obj", "gls", "pos", "grm"]]
        #     padding += " " * max(lines) + " "
        # res = input(padding + prompt)
        res = questionary.text(prompt, default=pre_fill).ask()
        return res

    def prompt_at_position_old(self, ex, pos, prompt):
        print_record(ex, highlight_pos=pos)
        padding = ""
        for i in range(0, pos):
            lines = [
                len(line[i])
                for key, line in ex.items()
                if key in ["obj", "gls", "pos", "grm"]
            ]
            padding += " " * max(lines) + " "
        res = input(padding + prompt)
        return res

    def parse(self, rec):
        self.annotated.setdefault(rec[self.id_key], {})
        rec[self.output_col] = ["" for x in range(0, len(rec[self.parse_col]))]
        for i, values in enumerate(zip(*rec.values())):
            wf_id = self.identify(values)
            if wf_id in self.ignore:
                rec[self.output_col][i] = ""
                continue
            retrieved = False
            if i in self.annotated[rec[self.id_key]]:
                if wf_id in self.annotated[rec[self.id_key]][i]:
                    print(f"oh hello i just found {wf_id} in my annotations!")
                    answer = self.annotated[rec[self.id_key]][i][wf_id]
                    rec[self.output_col][i] = answer
                    retrieved = True
                    if self.fix:
                        answer = self.prompt_at_position(
                            rec, i, prompt=f"Annotate?", pre_fill=answer
                        )
            if not retrieved:
                if self.is_target(wf_id):
                    answer = self.prompt_at_position(
                        rec,
                        i,
                        prompt=f"Annotate?",
                        pre_fill=self.find_suggestion(wf_id, rec),
                    )
                    if answer == "ignore":  # annotate nothing and never ask again
                        self.ignore.add(wf_id)
                    if answer not in ["ignore", "skip"]:
                        self.cache.setdefault(wf_id, [])
                        self.cache[wf_id].append(answer)
                        self.annotated[rec[self.id_key]][i].setdefault({})
                        self.annotated[rec[self.id_key]][i][wf_id] = answer
                        rec[self.output_col][i] = answer
                    else:
                        rec[self.output_col][i] = ""
        dump(self.annotated, self.annotated_path)  # keep updates
        dump(self.cache, self.cache_path)  # keep updates
        dump(list(self.ignore), self.ignore_path)  # keep updates
        return rec
