# Amulet-web-backend
*testing  
*unofficial


## Install
```shell
python3 -m pip install requirements.txt
```

## Run
```shell
python3 main.py [--port 8080] [--host 0.0.0.0]
```

## Method
### Get Info 
GET `http://127.0.0.1:8080/info`
```json
{
  "app_version": "1.0.0/230623",
  "amulet_version": "1.9.15",
  "runningProcessCount": 1,
  "runningProcesses": [
    {
      "processor": "AmuletChunkCopyProcess",
      "info": {
        "path": "test",
        "sourceClass": "World",
        "sourceDimension": "minecraft:overworld",
        "sourceSelectionMin": [-2, 0, -2],
        "sourceSelectionMax": [2, 2, 2],
        "targetClass": "SpongeSchemFormatWrapper",
        "targetDimension": "main"
      }
    }
  ],
  "openFileCount": 1
}
```

### Convert request
POST `http://127.0.0.1:8080/convert?PARAMS`

| param          | value example            | comment                       |
|:---------------|:-------------------------|:------------------------------|
| source         | in.mcstructure           | input file path               | 
| sourceFormat   | *(reserve)*              | input format name *(reserve)* |
| target         | out.schem                | output file path              |
| targetFormat   | SpongeSchemFormatWrapper | output format name            |
| targetVersion  | 2                        | output format version         |
| targetPlatform | java                     | platform: `bedrock` or `java` |

※ Format list: [Amulet Core docs](https://amulet-core.readthedocs.io/en/stable/api_reference/level.formats/index.html)