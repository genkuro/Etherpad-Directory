#!/usr/bin/python
#
# list_etherpads.py
# 
# Queries the etherpad database (MYSQL) to gather etherpad statistics
# including name, authors, creation date, modification date, and 
# the number of edits made to the etherpad.  The stats are used to
# build four static html pages listing the etherpads sorted by
# name, creation date, modification date, and usage.
#
# usage:  list_etherpads.py <outputdir> <basename>
#
# writes four html files to <outputdir>:
#    <basename>_name.html
#    <basename>_created.html  
#    <basename>_modified.html  
#    <basename>_usage.html
#
#
# @todo parameterize all variables
# @todo harden error handling

import MySQLdb
import json
import re
import time
import sys
import os

def loads(obj):
    oddstring = 'DONT_TREAD_ME'
    p1 = re.compile('\}\s*\{')
    p2 = re.compile(oddstring)

    try:
        val = json.loads(obj)
        return True,[val]
    except TypeError:
        return False,obj
    except ValueError:
        try:
            list = []
            s = p1.sub('}' + oddstring + '{',str(obj))
            s = p2.split(s)
            for seg in s:
                list.append(json.loads(seg))
            return True,list
        except TypeError:
            return False,obj
        except ValueError:
            return False,obj

def parse_pad_meta(data):
    isjson,obj = loads(data)
    list = []
    if isjson:
        for json in obj:
            list.append((json['x']['head'],json['x']['numChatMessages']))
    return list

def parse_authors(data):
    isjson,obj = loads(data)
    list = []
    if isjson:
        for row in obj:
            for key in row:
                if key == 'name':
                    name = row[key].encode('ascii','ignore')
                    if name not in list:
                        list.append(name)
    return list


def parse_meta(data):
    nhead,nchatmessages = 0,0
    return nhead,nchatmessages


def unique_authors(pad_data):
    list = []
    for docid in pad_data:
        for author in pad_data[docid][0]:
            if author not in list:
                list.append(author)
    list.sort(key=lambda x: x.lower())
    return list
                

def get_html(object,index,name):
    maxscore = 0 
    for next in object:
        pad,authors,created,modified,head,messages = next
        if head > maxscore:
            maxscore = head
    if index == 'name':
        object.sort(key=lambda x: x[0])
    elif index == 'created':
        object.sort(key=lambda x: x[2])
        object.reverse()
    elif index == 'modified':
        object.sort(key=lambda x: x[3])
        object.reverse()
    elif index == 'usage':
        object.sort(key=lambda x: -x[4])

    s = ""
    s += "<html>\n"
    s += "<head>\n"
    s += "<style type='text/css'>\n"
    s += "th { font-family: sans-serif; font-size: 12pt; font-weight: normal; color: white; background-color: #333333; padding: 3px; }\n" 
    s += "td { font-family: sans-serif; font-size: 9pt; padding: 0px 20px 10px 0px; margin: 0px;}\n"
    s += "</style>\n"
    s += "<title>Etherpad Meeting List</title>\n"
    s += "</head>\n"
    s += "<body style='font-family:sans-serif; font-size:9px;'><center>\n"
    s += "<table>\n"
    s += "<tr><td colspan='5'>"
    s += "Sort by: &nbsp;&nbsp;&nbsp;"
    s += "<a href='%s'>Name</a>&nbsp;&nbsp;&nbsp;\n"%(name+"_name.html")
    s += "<a href='%s'>Created</a>&nbsp;&nbsp;&nbsp;\n"%(name+"_created.html")
    s += "<a href='%s'>Modified</a>&nbsp;&nbsp;&nbsp;\n"%(name+"_modified.html")
    s += "<a href='%s'>Usage</a>&nbsp;&nbsp;&nbsp;\n"%(name+"_usage.html")
    s += "</td></tr>"
    s += "<tr><th>Etherpad</th><th>Authors</th><th>Created</th><th>Modified</th><th>Usage</th></tr>\n"
    for next in object:
        pad,authors,created,modified,head,messages = next
        s += "<tr>\n"
        s += ("<td valign='top'><a href='http://etherpad.ooici.org/%s'>%s</a></td>\n"%(pad,pad))
        s += "<td valign='top'>\n"
        if len(authors) == 0:
            s += "&nbsp;"
        else:
            s += authors[0]
            for author in authors[1:]:
                s+= "<br/>\n" + author
        s += "</td>"
        s += "<td valign='top'>%s</td><td valign='top'>%s</td>\n"%(created.strftime("%b %d %Y"),modified.strftime("%b %d %Y"))
        s += "<td valign='top'><img src='blue_dot.gif' height='10px' width='%spx' alt=''></div></td>\n"%(head*100/maxscore)
        s += "</tr>\n"
        s += "<tr><td colspan='5'><hr></td></tr>\n"
    s += "<table>\n"
    s += "</body>\n"
    return s


def write_html(html,docroot,name):
    file = os.path.join(docroot,name)
    f = open(file, 'w')
    f.write(html)
    f.close()
 
def get_data():
    sql_string = "                                     \
    select                                             \
        a.ID,                                          \
        b.DATA,                                        \
        c.creationTime,                                \
        c.lastWriteTime,                               \
        d.JSON                                         \
    from                                               \
        PAD_AUTHORS_META a                             \
        JOIN PAD_AUTHORS_TEXT b on a.NUMID = b.NUMID   \
        JOIN PAD_SQLMETA c on c.ID = a.ID              \
        JOIN PAD_META d on d.ID = a.ID                 \
    order by                                           \
        c.creationTime desc                            \
    "
    
    conn = MySQLdb.connect (
            host = "localhost",
            user = "etherpad",
            passwd = "etherpad",
            db = "etherpad")
    cursor = conn.cursor ()
    cursor.execute (sql_string)
    
    pad_data = {}
    while (1):
        row = cursor.fetchone()
        if row == None:
            break
        if row[0] in pad_data:
            new_authors = parse_authors(row[1])
            old_authors = pad_data[row[0]][1]
            new_authors.extend(old_authors)
            new_set = (row[0], new_authors, row[2],row[3])
        else:
            meta = parse_pad_meta(row[4])[0]
            pad_data[row[0]] = ([row[0],parse_authors(row[1]),row[2],row[3],meta[0],meta[1]])
    conn.close ()
    return pad_data.values()
    

def main(args):
    docroot = args[0]
    name = args[1]

    data = get_data()
    for index in ['name','modified','created','usage']:
        html = get_html(data,index,name)
        write_html(html,docroot,name+'_' + index + '.html')

if __name__ == "__main__":
    main(sys.argv[1:])
