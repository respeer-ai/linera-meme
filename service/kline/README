pip3 install --upgrade pip
pip3 install -r requirements.txt
pip3 install -e .

pip3 uninstall websocket
pip3 uninstall websocket-client
pip3 install websocket-client

python3 src/kline.py
python3 tests/websocket_test.py
curl -X POST http://localhost:25080/run/ticker
