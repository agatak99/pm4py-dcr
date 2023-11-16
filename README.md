# A DCR Exentionsion for pm4py
Welcome to the pm4py extension for pm4py, that has been developed for pm4py.

This exentionsion currently supports the discovery of DCR Graphs, conformance checking, and import export of dcr graph using xml for possible cross platform usage and visualization of dcr graph.

## Documentation
The documentation has been autogenerated by using sphinx Visit [https://www.sphinx-doc.org/en/master/](https://www.sphinx-doc.org/en/master/)

The documentation can be found in the docs/build/html.
main html
documentation has been created in a docs folder, with provided html files in docs/build/html, contains the documentation of the implementation from the simplified interface functions for users, as well for the implementation behind these functions. Currently implemented functionality for process discovery and conformance checking

## usage
For usage, import the pm4py library, call the function
```
import pm4py #currently pm4py, maybe update to match if we create new name

# to discover dcr graph
path_to_log = pm4py.discover_dcr

#write dcr graph to xml(optinal to import to dcr_portal)
pm4py.write_dcr_xml
```
For more indepth tutorial look at tutorial in  
## Requirements
Contains the same requirements for installation as provided in [(PM4Py-core)
Usage](https://github.com/pm4py/pm4py-core/tree/release)

## Installation
create a a virtual environment in python and
```
pip install -r requirements.text
```

## License
licensed under GPL
