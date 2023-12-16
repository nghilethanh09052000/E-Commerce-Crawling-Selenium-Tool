* Introduction to Protobuf *

Steps to Create a protobuf

1. Requirements

```bash
sudo snap install protobuf
sudo apt  install protobuf-compile
```

2. Create File Object , Example app/models/proto_files/webpage.proto

3. Parse the Object by running the below script which will product  app/models/webpage_pb2.py

```bash
protoc -I=app/models/proto --python_out=app/models/proto app/models/proto/webpage.proto

protoc -I=app/models/proto --python_out=app/models/proto app/models/proto/logpage.proto
```

4. To Format a Binary Protobuf class you can do

```bash
from google.protobuf.json_format import MessageToJson
```

json_obj = MessageToJson(protobuff_binary)

5. To Parse Json to protobuf you can do

```bash
from app.models.webpage_pb2 import Webpage
message = Parse(json.dumps(response), Webpage())
serialized_message = message.SerializeToString()
```

5. To Parse From Binary to Protobuf Class

```bash
from app.models.webpage_pb2 import Webpage
message = WEBPAGE_OBJ.ParseFromString(<string>)
```
