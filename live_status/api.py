from flask import Flask,request,jsonify
from flask_cors import CORS
import json
app= Flask(__name__)
app.config["DEBUG"]=False
app.config["JSON_AS_ASCII"]=True
CORS(app)


@app.route("/alllive",methods=["GET"])
def get_alllive():
    ...

@app.route('/live', methods=['GET'])
def live():
    ...

@app.route('/allvtuber', methods=['GET'])
def allvtuber():
    ...

@app.route('/ping', methods=['GET'])
def ping():
    return "pong"

def start():
    return app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)