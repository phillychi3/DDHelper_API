from flask import Flask, request, jsonify,make_response
import json
import sqlite3
import uuid
import random
import discord
from discord_webhook import DiscordWebhook, DiscordEmbed
import logging

FORMAT = '[DDhelper image] %(asctime)s %(levelname)s: %(message)s'
logger = logging.getLogger('DDhelperiapi')
logger.setLevel(logging.INFO)

handler = logging.FileHandler('ddhelperiapi.log')
handler.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(handler)

hdr = logging.StreamHandler()
hdr.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(hdr)


app = Flask(__name__)
#app.config["DEBUG"] = True
app.config["JSON_AS_ASCII"] = False

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'JPG', 'PNG', 'gif', 'GIF'])
imagepath = "./images/"


def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/getimage/<isnsfw>', methods=['GET'])
def getimage(isnsfw):



    if 'tags' in request.args:
        tags = request.args.get('tags')
    else:
        tags = None

    conn = sqlite3.connect('images_data.db')
    c = conn.cursor()
    if tags == None:

        c.execute('SELECT * FROM images WHERE verify = "True"')
    else:
        if isnsfw == "nsfw":
            c.execute('SELECT * FROM images WHERE tags LIKE "%' +
                      tags + '%" AND "nsfw" = True AND verify = "True"')
        else:
            c.execute('SELECT * FROM images WHERE tags LIKE "%' + tags + '%" AND nsfw = "False" AND verify = "True"')

    data = c.fetchall()
    conn.close()
    return jsonify(data)

@app.route("/image/<isnsfw>", methods=["GET"])
def image(isnsfw):

    if 'tags' in request.args:
        tags = request.args.get('tags')
    else:
        tags = None

    conn = sqlite3.connect('images_data.db')
    c = conn.cursor()
    if tags == None:
        if isnsfw == "nsfw":
            c.execute('SELECT * FROM images WHERE nsfw = "True" AND verify = "True"')
        else:
            c.execute('SELECT * FROM images WHERE nsfw = "False" AND verify = "True"')
            
        
    else:
        if isnsfw == "nsfw":
            c.execute(f'SELECT * FROM images WHERE tags LIKE "%{tags}%" AND nsfw = "True" AND verify = "True"')
        else:
            c.execute(f'SELECT * FROM images WHERE tags LIKE "%{tags}%" AND nsfw = "False" AND verify = "True"')

    data = c.fetchall()
    conn.close()
    if len(data) == 0:
        return jsonify({"error": "no images in gat"})
    rand = random.randint(0, len(data)-1)
    print(data[rand][4])
    print(data)
    id = data[rand][1] + '.' + data[rand][4]

    if isnsfw == "nsfw":
        try:
            if data[rand][4] == "jpg":
                head="jpeg"
            elif data[rand][4] == "png":
                head="png"
            elif data[rand][4] == "gif":
                head="gif"
            else:
                head="png"

            image_data = open(f"images/nsfw/{id}", "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = f'image/{head}'
            return response
        except:
            return jsonify({"error": "image not found"})
    else:
        try:
            if data[rand][4] == "jpg":
                head="jpeg"
            elif data[rand][4] == "png":
                head="png"
            elif data[rand][4] == "gif":
                head="gif"
            else:
                head="png"
            image_data = open(f"images/sfw/{id}", "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = f'image/{head}'
            return response
        except:
            return jsonify({"error": "image not found"})


@app.route('/showimage/<isnsfw>/<id>', methods=['GET'])
def showimage(isnsfw, id):
    if isnsfw == "nsfw":
        try:
            ext = id.rsplit('.', 1)[1]
            if ext == "jpg":
                head="jpeg"
            elif ext == "png":
                head="png"
            elif ext == "gif":
                head="gif"
            else:
                head="png"  
            image_data = open(f"images/nsfw/{id}", "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = f'image/{head}'
            response.headers['cross-origin-resource-policy'] = 'cross-origin'
            response.headers['access-control-allow-origin'] = '*'
            return response
        except:
            return jsonify({"error": "image not found"})
    elif isnsfw == "sfw":
        try:
            ext = id.rsplit('.', 1)[1]
            if ext == "jpg":
                head="jpeg"
            elif ext == "png":
                head="png"
            elif ext == "gif":
                head="gif"
            else:
                head="png"              
            image_data = open(f"images/sfw/{id}", "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = f'image/{head}'
            response.headers['cross-origin-resource-policy'] = 'cross-origin'
            response.headers['access-control-allow-origin'] = '*'

            return response
        except:
            return jsonify({"error": "image not found"})
    else:
        return jsonify({"error": "Invalid image type"})

@app.route('/addimage', methods=['post'],strict_slashes=False)
def addimage():

    img = request.files.get('photo')
    tag = request.form.get("tag")
    nsfw = request.form.get("isnsfw")
    selftag = request.form.get('selftag')
    print(img)
    
    print(nsfw)
    print(selftag)
    tags=[]
    tags.append(tag) 
    if selftag != '':
        tags.append(selftag) 
    print(tags)
    if img == None:
        return jsonify({"error": 87, "msg": "檔案都沒了"})
    if allowed_file(img.filename):

        imgname = (str(uuid.uuid4()))[36:-13:-1]
        ext = img.filename.rsplit('.', 1)[1]

        if nsfw == "True":
            img.save(imagepath +"nsfw/" +imgname + "."+ext)
        else:
            img.save(imagepath +"sfw/" +imgname + "."+ext)
        
        if nsfw != "True":
            nsfw = "False"
            
        conn = sqlite3.connect('images_data.db')
        c = conn.cursor()
        c.execute('INSERT INTO images (name, tags, nsfw,ext) VALUES ( ?, ?, ?, ?)',(imgname, str(tags), nsfw,ext))
        conn.commit()
        conn.close()

        if nsfw == "True":
            webhook = DiscordWebhook(url='https://discord.com/api/webhooks/947585191432568873/TW9YqZDT7QjQ4YcYoo20xlSPExvv_rNjN9iGDh53Rtqybh9R83cfUvGeQkcVTtfXC1Gy')
            with open(f"images/nsfw/{imgname}.{ext}", "rb") as f:
                webhook.add_file(file=f.read(), filename=f'nsfw.{ext}')
            webhook.execute()
        else:
            webhook = DiscordWebhook(url='https://discord.com/api/webhooks/947585038789263400/7NLtwfUuD_GUp6EUK7hUiMYpVIA7TQGSv7pumZc883Jtrs6nBp389ZJeNOJYwkH-Z3UC')
            with open(f"images/sfw/{imgname}.{ext}", "rb") as f:
                webhook.add_file(file=f.read(), filename=f'sfw.{ext}')
            webhook.execute()

        return jsonify({"success": 0, "msg": "上傳成功"})
    else:
        return jsonify({"error": 87, "msg": "檔案格式不符"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=443,ssl_context=('certificate.crt', 'private.key'))
    #app.run(host='0.0.0.0', port=5500)
