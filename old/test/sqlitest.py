import sqlite3
import json
dbfile = "test.db"
conn = sqlite3.connect(dbfile)
print ("Opened database successfully")
rows = conn.execute("SELECT * from images")
print ("load database successfully")


#sql回傳
# for row in rows:
#     for field in row:
#         print("{}\t".format(field), end="")
#json回傳
rv=rows.fetchall()
row_headers=[x[0] for x in rows.description]
json_data=[]
for result in rv:
    json_data.append(dict(zip(row_headers,result)))
print( json.dumps(json_data))


conn.close()