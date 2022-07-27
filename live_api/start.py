from flask import Flask,request,jsonify
from flask import render_template
from flask_cors import CORS
import json
import random
import os
app= Flask(__name__)
app.config["DEBUG"]=False
app.config["JSON_AS_ASCII"]=True
CORS(app)


@app.route("/alllive",methods=["GET"])
def get_alllive():
    with open("live.json","r",encoding="utf-8") as f:
        data=json.load(f)
    return data


@app.route("/add_live",methods=["GET"])
def add_live():
    with open("setting.json","r",encoding="utf-8")as f:
        data=json.load(f)
        

    if "name" in request.args:
        name = request.args["name"]
    else:
        return "unfind data:name"
    if "Company" in request.args:
        Company = request.args["Company"]
    else:
        return "unfind data:Company"
    if "url" in request.args:
        url = request.args["url"]
    else:
        return "unfind data:url"
    if "country" in request.args:
        country = request.args["country"]
    else:
        return "unfind data:country"


    if not str(name) in data:
        data[name]={}
        data[name]["name"]=name
        data[name]["company"]=Company
        data[name]["url"]=url
        data[name]["country"]=country
        with open('setting.json', 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return "do right thing"
    else:
        return "data again lol"


@app.route('/live', methods=['GET'])
def live():
    with open("live.json", "r",encoding="utf-8") as jsonFile: 
        data = json.load(jsonFile)
    results = []
    if 'name' in request.args:
        name = request.args['name']
        for daname in data:
            if daname == name:
                results.append(data[daname])


        return jsonify(results)
    if 'company' in request.args:
        company = request.args['company']
        for daname in data:
            daname=str(daname)
            try:
                if data[daname]["company"] == company:
                    results.append(data[daname])
            except Exception as e:
                print(e)

        return jsonify(results)
    if 'country' in request.args:
        country = request.args['country']
        for daname in data:
            daname=str(daname)
            try:
                if data[daname]["country"] == country:
                    results.append(data[daname])
            except Exception as e:
                print(e)

        return jsonify(results)

@app.route('/allname', methods=['GET'])
def allname():
    with open("setting.json", "r",encoding="utf-8",errors='ignore') as jsonFile: 
        data = json.load(jsonFile)
    results = []
    for daname in data:
        results.append(daname)

    return jsonify(results)

@app.route('/ping', methods=['GET'])
def ping():
    return "pong"
    



#image---------------------------------------------------------


# @app.route("/image",methods=["GET"])
# def get_neko():
#     mainfloor=os.listdir("C:/xampp/htdocs/api")
#     if 'tag' in request.args:
#         tag = request.args['tag']
#     else:
#         return "no tag"
        
#     if tag in mainfloor:
#         imagepath=os.listdir(f"C:/xampp/htdocs/api/{tag}")
#         sample = random.sample(imagepath, 1)
#         web=f"http://www.phillychi3.tk:6464/api/{tag}/{sample[0]}"
#         return web
    
#     else:
#         return "no floor"
    
    
    
# @app.route("/addimage",methods=["GET"])
# def addimage():
#     if 'tag' in request.args:
#         tag = request.args['tag']
#     else:
#         return "no tag"
#     if 'data' in request.args:
#         data = request.args['data']
#     else:
#         return "no data"        
        
#     with open(f"image_data/{tag}.txt","r") as f:
#         loaddata=f.read()
#     loaddata=loaddata+","+data
#     with open(f"image_data/{tag}.txt","w") as f:
#         f.write(loaddata)
#     return "ok"    
        
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)