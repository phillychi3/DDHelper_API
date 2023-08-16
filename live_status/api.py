from flask import Flask,request,jsonify
from flask_cors import CORS
from database import db
app= Flask(__name__)
app.config["DEBUG"]=True
app.config["JSON_AS_ASCII"]=True
CORS(app)


@app.route('/live', methods=['GET'])
def live():
    statuslist = ["LIVE","READY_TO_LIVE"]
    status = request.args.get('status')
    if status == None:
        status = "LIVE"
    if status not in statuslist:
        return {"error":"status is not correct"},400
    livedata = list(db.getlivefromstatus(status))
    for page in range(len(livedata)):
        livedata[page] = {k:v for k, v in livedata[page].items() if k != '_id'}
    return jsonify(livedata)

@app.route('/allvtuber', methods=['GET'])
def allvtuber():
    allvtuber = db.get_channels()
    return jsonify(allvtuber)

@app.route('/ping', methods=['GET'])
def ping():
    return "pong"

def start():
    return app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)