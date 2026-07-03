from flask import Flask, request
import pickle, os
app = Flask(__name__)

@app.route('/load', methods=['POST'])
def load():
    blob = request.data
    obj = pickle.loads(blob)
    return str(obj)

@app.route('/ping')
def ping():
    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
