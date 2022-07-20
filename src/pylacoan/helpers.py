import logging
from pyigt import IGT


log = logging.getLogger(__name__)

ud_pos = ["v"]


def get_pos(tagset, mode="UD", sep=",", pos_list=None):
    if isinstance(tagset, str):
        tagset = tagset.split(sep)
    if not pos_list:
        if mode == "UD":
            pos_list = ud_pos
        else:
            pos_list = []
    for tag in tagset:
        if tag in pos_list:
            return tag
    return ""


def get_morph_id(id_list, id_dic, obj, gloss="", mode="morphs"):
    """Identifies which ID belongs to a given morph.

    :param id_list: a list of ID strings, one of which is thought to
    belong to the morph
    :type id_list: list
    :param id_dic: a dict mapping ID strings to strings of
    the format <obj:morph>
    :type id_dic: dict
    :param obj: the string representation of the morph's form
    :type obj: str
    :param gloss: the string representation of the morph's gloss
    :type gloss: str
    ...
    :raises [ErrorType]: [ErrorDescription]
    ...
    :return: [ReturnDescription]
    :rtype: [ReturnType]
    """
    test_str = f"{obj}:{gloss}".strip(":")
    log.debug(f"searching {test_str} with {id_list}")
    for m_id in id_list:
        log.debug(f"testing id {m_id}")
        if m_id not in id_dic:
            raise ValueError(f"ID {m_id} not found in id_dic")
        if test_str in id_dic[m_id]:
            if mode == "morphs":
                return id_dic[m_id][test_str]
            if mode == "morphemes":
                return m_id
            raise ValueError(f"Invalid mode '{mode}'")
    return None


def sort_uniparser_ids(id_list, obj, gloss, id_dic, mode="morphs"):
    """Used for sorting the unsorted ID annotations by`uniparser
    <https://uniparser-morph.readthedocs.io/en/latest/paradigms.html#morpheme-ids>`_.
    There will be a glossed word form with segmented object and gloss lines, as
    well as an unordered list of IDs.
    This method uses a dictionary matching IDs to <"form:gloss"> strings to
    sort this ID list, based on the segmented object and glossing lines.

    """
    igt = IGT(phrase=obj, gloss=gloss)
    sorted_ids = []
    for w in igt.glossed_words:
        for m in w.glossed_morphemes:
            try:
                sorted_ids.append(
                    get_morph_id(id_list, id_dic, m.morpheme, m.gloss, mode)
                )
            except ValueError as e:
                log.error(e)
                log.error(id_list)
                log.error(f"{obj} '{gloss}'")
    log.debug(sorted_ids)
    return sorted_ids


punctuation = [",", ".", ":", ";", "!", "-", "?", "“", "”", "’", "‘", '"', "¡"]


def pprint_uniparser(wf):
    return f"""{wf.wfGlossed}
{wf.gloss}

lemma: {wf.lemma}
gramm: {wf.gramm}
ids: {dict(wf.otherData).get("id", None)}"""


def ortho_strip(ortho_str, exceptions=None, additions=None):
    if exceptions is None:
        exceptions = []
    if additions is None:
        additions = []
    punct = [x for x in punctuation + additions if x not in exceptions]
    for p in punct:
        ortho_str = ortho_str.replace(p, "")
    return ortho_str.lower()
