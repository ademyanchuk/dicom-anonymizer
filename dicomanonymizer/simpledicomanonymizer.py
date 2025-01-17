import logging
import logging.config
import re
from random import randint
from typing import Callable, Dict, List, Optional, Tuple

import pydicom
from pydicom.errors import InvalidDicomError

from .dicomfields import ACTION_TO_TAG_LIST
from .format_tag import tag_to_hex_strings
from .utils import ActionsDict, Path_Str, TagList, TagTuple

dictionary = {}

# setup logging
logger = logging.getLogger(__name__)

# Regexp function


def regexp(options: dict):
    """
    Apply a regexp method to the dataset

    :param options: contains two values:
        - find: which string should be find
        - replace: string that will replace the find string
    """

    def apply_regexp(dataset, tag):
        """
        Apply a regexp to the dataset
        """
        element = dataset.get(tag)
        if element is not None:
            element.value = re.sub(
                options["find"], options["replace"], str(element.value)
            )

    return apply_regexp


# Default anonymization functions


def replace_element_UID(element: pydicom.DataElement):
    """
    Keep char value but replace char number with random number
    The replaced value is kept in a dictionary link to the initial element.value in order to automatically
    apply the same replaced value if we have an other UID with the same value
    """
    if element.value not in dictionary:
        new_chars = [
            str(randint(0, 9)) if char.isalnum() else char for char in element.value
        ]
        dictionary[element.value] = "".join(new_chars)
    element.value = dictionary.get(element.value)


def replace_element_date(element: pydicom.DataElement):
    """
    Replace date element's value with '00010101'
    """
    element.value = "00010101"


def replace_element_date_time(element: pydicom.DataElement):
    """
    Replace date time element's value with '00010101010101.000000+0000'
    """
    element.value = "00010101010101.000000+0000"


def replace_element_IS(element: pydicom.DataElement):
    """Elements with VR == IS can have either single value
    or multivalue (see Pixel Aspect Ratio tag for example)
    Multiple values like [1, 1] will be replaced as [0, 0]
    and not as just 0

    Args:
        element (pydicom.DataElement): data element
    """
    if isinstance(element.value, pydicom.multival.MultiValue):
        for i, _ in enumerate(element.value):
            element.value[i] = "0"
    else:
        element.value = "0"


def replace_element(element):
    """
    Replace element's value according to it's VR:
    - DA: cf replace_element_date
    - TM: replace with '000000.00'
    - LO, SH, PN, CS: replace with 'Anonymized'
    - UI: cf replace_element_UID
    - IS: replace with '0'
    - FD, FL, SS, US: replace with 0
    - ST: replace with ''
    - SQ: call replace_element for all sub elements
    - DT: cf replace_element_date_time
    """
    if element.VR == "DA":
        replace_element_date(element)
    elif element.VR == "TM":
        element.value = "000000.00"
    elif element.VR in ("LO", "SH", "PN", "CS"):
        element.value = "Anonymized"
    elif element.VR == "UI":
        replace_element_UID(element)
    elif element.VR == "UL":
        pass
    elif element.VR == "IS":
        replace_element_IS(element)
    elif element.VR in ("FD", "FL", "SS", "US"):
        element.value = 0
    elif element.VR == "ST":
        element.value = ""
    elif element.VR == "SQ":
        for sub_dataset in element.value:
            for sub_element in sub_dataset.elements():
                replace_element(sub_element)
    elif element.VR == "DT":
        replace_element_date_time(element)
    else:
        raise NotImplementedError(
            "Not anonymized. VR {} not yet implemented.".format(element.VR)
        )


# NOTE: In case user want to add a tag from `file_meta` to de-id rules, we need to
# try get tag from `file_meta` as well and only then to give up


def replace(dataset: pydicom.Dataset, tag: Tuple[int, int]):
    """D - replace with a non-zero length value that may be a dummy value
    and consistent with the VR

    Args:
        dataset (pydicom.Dataset): pydicom dataset to get `tag` element from
        tag (Tuple[int, int]): tag is represented as a tuple of ints in hex notation
    """
    element = dataset.get(tag)
    if element is None and hasattr(dataset, "file_meta"):
        element = dataset.file_meta.get(tag)

    if element is not None:
        replace_element(element)


def empty_element(element: pydicom.DataElement):
    """
    Clean element according to the element's VR:
    - SH, PN, UI, LO, CS: value will be set to ''
    - DA: value will be replaced by '00010101'
    - TM: value will be replaced by '000000.00'
    - UL: value will be replaced by 0
    - SQ: all subelement will be called with "empty_element"
    """
    if element.VR in ("SH", "PN", "UI", "LO", "CS"):
        element.value = ""
    elif element.VR == "DA":
        replace_element_date(element)
    elif element.VR == "TM":
        element.value = "000000.00"
    elif element.VR == "UL":
        element.value = 0
    elif element.VR == "SQ":
        for sub_dataset in element.value:
            for sub_element in sub_dataset.elements():
                empty_element(sub_element)
    else:
        raise NotImplementedError(
            "Not anonymized. VR {} not yet implemented.".format(element.VR)
        )


def empty(dataset: pydicom.Dataset, tag: Tuple[int, int]):
    """Z - replace with a zero length value, or a non-zero length
    value that may be a dummy value and consistent with the VR

    Args:
        dataset (pydicom.Dataset): pydicom dataset to get `tag` element from
        tag (Tuple[int, int]): tag is represented as a tuple of ints in hex notation
    """
    element = dataset.get(tag)
    if element is None and hasattr(dataset, "file_meta"):
        element = dataset.file_meta.get(tag)
    if element is not None:
        empty_element(element)


def delete_element(dataset: pydicom.Dataset, element: pydicom.DataElement):
    """Delete the element from the dataset.
    If VR's element is a date, then it will be replaced by 00010101

    Args:
        dataset (pydicom.Dataset): dataset to work with
        element (pydicom.DataElement): dataelement to work with
    """
    if element.VR == "DA":
        replace_element_date(element)
    elif element.VR == "SQ" and isinstance(element.value, pydicom.Sequence):
        for sub_dataset in element.value:
            for sub_element in sub_dataset.elements():
                delete_element(sub_dataset, sub_element)
    else:
        # in case the tag is from file_meta
        if hasattr(dataset, "file_meta") and element.tag in dataset.file_meta:
            del dataset.file_meta[element.tag]
        # in the rest of the header
        else:
            del dataset[element.tag]


def delete(dataset: pydicom.Dataset, tag: Tuple[int, int]):
    """X - remove

    Args:
        dataset (pydicom.Dataset): dataset to work with
        tag (Tuple[int, int]): tag is represented as a tuple of ints in hex notation
    """
    element = dataset.get(tag)
    if element is None and hasattr(dataset, "file_meta"):
        element = dataset.file_meta.get(tag)
    if element is not None:
        delete_element(dataset, element)  # element.tag is not the same type as tag.


def keep(dataset, tag):
    """K - keep (unchanged for non-sequence attributes, cleaned for sequences)"""
    pass


def clean(dataset: pydicom.Dataset, tag: Tuple[int, int]):
    """C - clean, that is replace with values of similar meaning known
    not to contain identifying information and consistent with the VR

    Args:
        dataset (pydicom.Dataset): pydicom dataset to get `tag` element from
        tag (Tuple[int, int]): tag is represented as a tuple of ints in hex notation

    Raises:
        NotImplementedError: basic de-id profile of DICOM-standard does not require
        cleaning of any tag. NOTE: might be implemented in the future
    """
    element = dataset.get(tag)
    if element is None and hasattr(dataset, "file_meta"):
        element = dataset.file_meta.get(tag)
    if element is not None:
        raise NotImplementedError("Tag not anonymized. Not yet implemented.")


def replace_UID(dataset: pydicom.Dataset, tag: Tuple[int, int]):
    """U - replace with a non-zero length UID that is internally consistent
    within a set of Instances
    Lazy solution : Replace with empty string

    Args:
        dataset (pydicom.Dataset): dataset to work with
        tag (Tuple[int, int]): tag in hex notation
    """
    element = dataset.get(tag)
    if element is None and hasattr(dataset, "file_meta"):
        element = dataset.file_meta.get(tag)
    if element is not None:
        replace_element_UID(element)


def empty_or_replace(dataset, tag):
    """Z/D - Z unless D is required to maintain IOD conformance (Type 2 versus Type 1)"""
    replace(dataset, tag)


def delete_or_empty(dataset, tag):
    """X/Z - X unless Z is required to maintain IOD conformance (Type 3 versus Type 2)"""
    empty(dataset, tag)


def delete_or_replace(dataset, tag):
    """X/D - X unless D is required to maintain IOD conformance (Type 3 versus Type 1)"""
    replace(dataset, tag)


def delete_or_empty_or_replace(dataset, tag):
    """
    X/Z/D - X unless Z or D is required to maintain IOD conformance (Type 3 versus Type 2 versus
    Type 1)
    """
    replace(dataset, tag)


def delete_or_empty_or_replace_UID(dataset: pydicom.Dataset, tag: Tuple[int, int]):
    """X/Z/U* - X unless Z or replacement of contained instance UIDs (U) is required
    to maintain IOD conformance (Type 3 versus Type 2 versus Type 1 sequences
    containing UID references)

    Args:
        dataset (pydicom.Dataset): dataset to work with
        tag (Tuple[int, int]): tag in hex notation
    """
    element = dataset.get(tag)
    if element is None and hasattr(dataset, "file_meta"):
        element = dataset.file_meta.get(tag)

    if element is not None:
        if element.VR == "UI":
            replace_element_UID(element)
        else:
            empty_element(element)


# Generation functions

ACTIONS_MAP_NAME_FUNCTIONS = {
    "replace": replace,
    "empty": empty,
    "delete": delete,
    "replace_UID": replace_UID,
    "empty_or_replace": empty_or_replace,
    "delete_or_empty": delete_or_empty,
    "delete_or_replace": delete_or_replace,
    "delete_or_empty_or_replace": delete_or_empty_or_replace,
    "delete_or_empty_or_replace_UID": delete_or_empty_or_replace_UID,
    "keep": keep,
}


def generate_actions(tag_list: TagList, action: str) -> ActionsDict:
    """Generate a dictionary using list values as tag and assign
    the same value to all

    Args:
        tag_list (TagList): List of tags to apply action
        action (str): action type

    Returns:
        ActionsDict: mapping of tag -> required action callable
    """
    assert isinstance(action, str) and action in ACTIONS_MAP_NAME_FUNCTIONS
    final_action = ACTIONS_MAP_NAME_FUNCTIONS[action]
    return {tag: final_action for tag in tag_list}


def initialize_actions(
    act_to_tag_list_map: Dict[str, TagList] = ACTION_TO_TAG_LIST
) -> ActionsDict:
    """Initialize a mapping of tag -> action func. Default is as required by
    DICOM-standard basic de-identification profile

    Args:
        act_to_tag_list_map (Dict[str, TagList], optional): mapping of action
        (as a str) -> list of tags. Defaults to ACTION_TO_TAG_LIST.

    Returns:
        ActionsDict: mapping of tag -> action function
    """
    anonymization_actions = {}
    for act, tag_list in act_to_tag_list_map.items():
        _dict = generate_actions(tag_list, act)
        anonymization_actions.update(_dict)
    return anonymization_actions


def anonymize_dicom_file(
    in_file: Path_Str,
    out_file: Path_Str,
    extra_anonymization_rules: Optional[ActionsDict] = None,
    delete_private_tags: bool = True,
    ds_callback: Optional[Callable[[pydicom.Dataset], None]] = None,
) -> None:
    """Anonymize a DICOM file by modifying personal tags

    Conforms to DICOM standard except for customer specificities.

    Args:
        in_file (Path_Str): path to the original file
        out_file (Path_Str): path to anonymized version of `in_file` to be saved
        extra_anonymization_rules (dict, optional): User-provided custom anonymization rules. Defaults to None.
        delete_private_tags (bool, optional): if private tags to be deleted. Defaults to True.
        ds_callback (Optional[Callable[[pydicom.Dataset], None]], optional): optional way to access a dataset
        before anonymization. Defaults to None.
    """
    try:
        dataset = pydicom.dcmread(in_file)
    except InvalidDicomError:
        logger.error(f"Invalid dicom file: {in_file}, skipping")
        return

    # dataset callback goes here:
    if ds_callback is not None:
        ds_callback(dataset)
    # It is possible to have a broken dicom file, which will be opened without error
    # by dcmread, but then you try to access an opened Dataset it will throw the error
    # like this: NotImplementedError: Unknown Value Representation '0x01 0xbc'
    # This dataset (explored manually) have empty `dir`
    try:
        anonymize_dataset(dataset, extra_anonymization_rules, delete_private_tags)
    except NotImplementedError as e:
        logger.error(f"error in file: {in_file}, see below")
        logger.exception(e)
        return
    # Store modified image
    dataset.save_as(out_file)


def get_private_tag(dataset, tag):
    """
    Get the creator and element from tag

    :param dataset: Dicom dataset
    :param tag: Tag from which we want to extract private information
    :return dictionary with creator of the tag and tag element (which contains element + offset)
    """
    element = dataset.get(tag)

    element_value = element.value
    tag_group = element.tag.group
    # The element is a private creator
    if element_value in dataset.private_creators(tag_group):
        creator = {"tagGroup": tag_group, "creatorName": element.value}
        private_element = None
    # The element is a private element with an associated private creator
    else:
        # Shift the element tag in order to get the create_tag
        # 0x1009 >> 8 will give 0x0010
        create_tag_element = element.tag.element >> 8
        create_tag = pydicom.tag.Tag(tag_group, create_tag_element)
        create_dataset = dataset.get(create_tag)
        creator = {"tagGroup": tag_group, "creatorName": create_dataset.value}
        # Define which offset should be applied to the creator to find
        # this element
        # 0x0010 << 8 will give 0x1000
        offset_from_creator = element.tag.element - (create_tag_element << 8)
        private_element = {"element": element, "offset": offset_from_creator}

    return {"creator": creator, "element": private_element}


def get_private_tags(
    anonymization_actions: dict, dataset: pydicom.Dataset
) -> List[dict]:
    """
    Extract private tag as a list of object with creator and element

    :param anonymization_actions: list of tags associated to an action
    :param dataset: Dicom dataset which will be anonymize and contains all private tags
    :return Array of object
    """
    private_tags = []
    for tag in anonymization_actions:
        element = None
        try:
            element = dataset.get(tag)
        except Exception as e:
            logger.error("Cannot get element from tag: ", tag_to_hex_strings(tag))
            logger.exception(e)

        if element and element.tag.is_private:
            private_tags.append(get_private_tag(dataset, tag))

    return private_tags


def anonymize_dataset(
    dataset: pydicom.Dataset,
    extra_anonymization_rules: Optional[ActionsDict] = None,
    delete_private_tags: bool = True,
) -> None:
    """Anonymize a pydicom Dataset by using anonymization rules which links an action to a tag

    Args:
        dataset (pydicom.Dataset): dicom dataset
        extra_anonymization_rules (dict, optional): user-defined rules. Defaults to None.
        delete_private_tags (bool, optional): if delete private tags. Defaults to True.

    Raises:
        Exception: will raise Exception if `dataset.get(tag)` fails
    """
    current_anonymization_actions = initialize_actions()

    if extra_anonymization_rules is not None:
        current_anonymization_actions.update(extra_anonymization_rules)

    private_tags = []

    for tag, action in current_anonymization_actions.items():

        def range_callback(dataset, data_element):
            # repeating group condition
            is_repeating_group = (
                data_element.tag.group & tag[2] == tag[0]
                and data_element.tag.element & tag[3] == tag[1]
            )
            if is_repeating_group:
                # puting tag of 4 elements here will trigger the error with dataset.get
                action(dataset, (tag[0], tag[1]))

        element = None

        # We are in a repeating group
        if len(tag) > 2:
            dataset.walk(range_callback)
        # Individual Tags
        else:
            action(dataset, tag)
            try:
                element = dataset.get(tag)
            except Exception as e:
                print("Cannot get element from tag: ", tag_to_hex_strings(tag))
                raise e

            # Get private tag to restore it later
            if element and element.tag.is_private:
                private_tags.append(get_private_tag(dataset, tag))

    # X - Private tags = (0xgggg, 0xeeee) where 0xgggg is odd
    if delete_private_tags:
        dataset.remove_private_tags()

        # Adding back private tags if specified in dictionary
        for privateTag in private_tags:
            creator = privateTag["creator"]
            element = privateTag["element"]
            block = dataset.private_block(
                creator["tagGroup"], creator["creatorName"], create=True
            )
            if element is not None:
                block.add_new(
                    element["offset"], element["element"].VR, element["element"].value
                )
