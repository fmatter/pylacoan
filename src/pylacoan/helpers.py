from pyigt import IGT
import logging

log = logging.getLogger(__name__)


def get_morph_id(id_list, id_dic, obj, gloss=""):
    """Identifies which ID belongs to a given morph.
    
    :param id_list: a list of ID strings, one of which is thought to belong to the morph
    :type id_list: list
    :param id_dic: a dict mapping ID strings to strings of the format <obj:morph>
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
    for id in id_list:
        log.debug(f"testing id {id}")
        if id not in id_dic:
            raise ValueError(f"ID {id} not found in id_dic")
        if id_dic[id] == test_str:
            return id
    return None


def sort_uniparser_ids(id_list, obj, gloss, id_dic):
    """Used for sorting the unsorted ID annotations by `uniparser <https://uniparser-morph.readthedocs.io/en/latest/paradigms.html#morpheme-ids>`_.
    There will be a glossed word form with segmented object and gloss lines, as well as an unordered list of IDs.
    This method uses a dictionary matching IDs to <"form:gloss"> strings to sort this ID list, based on the segmented object and glossing lines.

    """
    igt = IGT(phrase=obj, gloss=gloss)
    sorted_ids = []
    for w in igt.glossed_words:
        for m in w.glossed_morphemes:
            sorted_ids.append(get_morph_id(id_list, id_dic, m.morpheme, m.gloss))
    log.debug(sorted_ids)
    return sorted_ids
