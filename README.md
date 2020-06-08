## trajectory-prediction

## Acknowledgements

This work has been supported by the EU H2020 project CLASS, contract #780622.


# Project structure

```
trajectory-prediction
|-- cfgfiles
|-- stubs
|-- tp
|   |-- dataclayObjectManager.py
|   |-- fileBasedObjectManager.py
|   |-- __init__.py
|   |-- mytrace.py
|   `-- v3TP.py
|-- __main__.py
|-- pywrenRunner.py
|-- README.md
|-- test-dataclay.py
|-- test-file.py
|-- python
|   `-- v3
|       |-- data2
|       |   |-- 0.txt
|       |   ...
|       |-- README.md
|       `-- TPv3.py
```

# Testing

To run it using local files from project root directory run:
```
python test-file.py
```

To test it with Dataclay, update stubs and cfgfiles folders with relevant files and run:
```
python test-dataclay.py
``` 

To use it with pywren, create pywren runtime, update your .pywren_config and run:
```
python pywrenRunner.py
``` 


# Openwhisk

Build pywren base image and register an Openwhisk docker action by:
```
zip -r classAction.zip __main__.py .pywren_config cfgfiles/ stubs/ pywrenRunner.py tp trace.py

wsk action update classAction --docker kpavel/pywren_dc:38 --timeout 300000 classAction.zip
```
