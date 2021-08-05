# DicomAnonymizer

**Current Fork Notes**

Hi, this fork is breaking original project functionality, providing updated one instead.   

I have added batch-anonymization. It is working with nested folders of dicom-files or with a single folder.
In short, you can give a source and destination root directories, source should contain (possibly nested) directories
with dicom files (but no dicom files in the root folder itself). The tool will find all folders inside the root, anonymize dicom-files and save anonymized data under
the destination root, preserving the original directories structure.

Here is the use example:
- `git clone git@github.com:ademyanchuk/dicom-anonymizer.git`
- `pip install .` after `cd` into the project directory
- you can now  run `dicom-anonymizer path/to/source path/to/destination`
- run `dicom-anonymizer --help` for more options

TODO: Add a Changelog and describe changes made since forking the project

**End of Current Fork Note**

Python package to anonymize DICOM files.
This project provide a CLI tool for de-identification of dicom-files' headers as required by DICOM-standard basic de-identification profile. More information about dicom fields for anonymization can be found [here](http://dicom.nema.org/dicom/2013/output/chtml/part15/chapter_E.html#table_E.1-1).

The default behaviour of this package is to anonymize DICOM fields referenced in [dicomfields](dicomanonymizer/dicomfields.py).

Dicom fields are separated into different groups. Each groups will be anonymized in a different way.

| Group | Action | Action definition |
| --- | --- | --- |
| D_TAGS | replace | Replace with a non-zero length value that may be a dummy value and consistent with the VR** |
| Z_TAGS | empty | Replace with a zero length value, or a non-zero length value that may be a dummy value and consistent with the VR** |
| X_TAGS | delete | Completely remove the tag |
| U_TAGS | replace_UID | Replace all UID's number with a random one in order to keep consistent. Same UID will have the same replaced value |
| Z_D_TAGS | empty_or_replace | Replace with a non-zero length value that may be a dummy value and consistent with the VR** |
| X_Z_TAGS | delete_or_empty | Replace with a zero length value, or a non-zero length value that may be a dummy value and consistent with the VR** |
| X_D_TAGS | delete_or_replace | Replace with a non-zero length value that may be a dummy value and consistent with the VR** |
| X_Z_D_TAGS | delete_or_empty_or_replace | Replace with a non-zero length value that may be a dummy value and consistent with the VR** |
| X_Z_U_STAR_TAGS | delete_or_empty_or_replace_UID | If it's a UID, then all numbers are randomly replaced. Else, replace with a zero length value, or a non-zero length value that may be a dummy value and consistent with the VR**|


# How to install it?
Here is install example:
- `git clone git@github.com:ademyanchuk/dicom-anonymizer.git`
- `pip install .` after `cd` into the project directory

TODO: Provide as Pypi package

Installing this package will also install an executable named `dicom-anonymizer`. In order to use it, please refer to the next section.



# How to use it ?

This package allows to anonymize a selection of DICOM field (defined or overrided).
The way on how the DICOM fields are anonymized can also be overrided.

- **[required]** `src` - full path to a folder which contains dicom files or folder contained nested folders with dicom files
- **[required]** `dst` - full path to the anonymized DICOM image or to a folder. This folder will be created if not exist. If folder with a nested structure was provided as a `src`, the structure will be recreated at `dst`
- [optional] `--type` - either `batch` for nested collection of folder with dicom files or `folder` for single folder with dicom files, default is `batch`
- [optional] `--no-extra` - only use a rules from DICOM-standard basic de-id profile
- [optional] `--extra-rules` - Path to json file defining extra rules for additional tags. Defalult [extra_rules.json](dicomanonymizer\resources\extra_rules.json) (see below)



## Default behaviour

You can use the default anonymization behaviour describe above. This will assume the provided `src` is a nested collection of folders containing dicom files, will anonymize and save into `dst` recreating original folder structure. Anonymization will be done by processing the fields defiened in the DICOM-standard basic de-id profile and tags in the [extra_rules.json](dicomanonymizer\resources\extra_rules.json). As was mentioned, add `--no-extra` flag to not use additional rules.

```python
dicom-anonymizer src dst
```

Run `dicom-anonymizer --help` for help.

## Private tags

Default behavior of the dicom anonymizer is to delete private tags.
TODO: Add an option to save private tags
## Custom rules with dictionary file

For advanced use cases you can create your own dictionary by creating a json file `extra_rules.json`, here is a default example from project [extra_rules.json](dicomanonymizer\resources\extra_rules.json):
```json
{
    "delete": [
        [
            "0x0008",
            "0x0012"
        ],
        [
            "0x0008",
            "0x0013"
        ],
        [
            "0x0018",
            "0x1012"
        ],
        [
            "0x0018",
            "0x1014"
        ]
    ]
}
```
See all valid action names in the [actions list](#actions-list).

Then run:
```python
dicom-anonymizer src dst --extra-rules dictionary.json
```
## Anonymize dicom tags without dicom file

If for some reason, you need to anonymize dicom fields without initial dicom file (extracted from a database for example). Here is how you can do it:
```python
from dicomanonymizer import anonymize_dataset

def main():

  # Create a list of tags object that should contains id, type and value
  fields = [
    { # Replaced by Anonymized
      'id': (0x0040, 0xA123),
      'type': 'LO',
      'value': 'Annie de la Fontaine',
    },
    { # Replaced with empty value
      'id': (0x0008, 0x0050),
      'type': 'TM',
      'value': 'bar',
    },
    { # Deleted
      'id': (0x0018, 0x4000),
      'type': 'VR',
      'value': 'foo',
    }
  ]

  # Create a readable dataset for pydicom
  data = pydicom.Dataset()

  # Add each field into the dataset
  for field in fields:
    data.add_new(field['id'], field['type'], field['value'])

  anonymize_dataset(data)

if __name__ == "__main__":
    main()
```
For more information about the pydicom's Dataset, please refer [here](https://github.com/pydicom/pydicom/blob/995ac6493188313f6a2e6355477baba9f543447b/pydicom/dataset.py).
You can also add a dictionnary as previously :
```python
    dictionary = {}

    def newMethod(dataset, tag):
        element = dataset.get(tag)
        if element is not None:
            element.value = element.value + '- generated with new method'

    dictionary[(0x0008, 0x103E)] = newMethod
    anonymize_dataset(data, dictionary)
```

# Actions list

| Action | Action definition |
| --- | --- |
| empty | Replace with a zero length value, or a non-zero length value that may be a dummy value and consistent with the VR** |
| delete | Completely remove the tag |
| keep | Do nothing on the tag |
| clean | Don't use it for now. **This is not implemented!** |
| replace_UID | Replace all UID's number with a random one in order to keep consistent. Same UID will have the same replaced value |
| empty_or_replace | Replace with a non-zero length value that may be a dummy value and consistent with the VR** |
| delete_or_empty | Replace with a zero length value, or a non-zero length value that may be a dummy value and consistent with the VR** |
| delete_or_replace | Replace with a non-zero length value that may be a dummy value and consistent with the VR** |
| delete_or_empty_or_replace | Replace with a non-zero length value that may be a dummy value and consistent with the VR** |
| delete_or_empty_or_replace_UID | If it's a UID, then all numbers are randomly replaced. Else, replace with a zero length value, or a non-zero length value that may be a dummy value and consistent with the VR** |


** VR: Value Representation

Work originally done by Edern Haumont
