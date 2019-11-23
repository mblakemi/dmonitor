# -*- coding: utf-8 -*-
"""
Created on Fri Feb 08 20:03:41 2019

@author: Michael
"""


import sqlite3
# import os, sys
from datetime import datetime, timedelta

sid = '40'
sdate = '2019-02-08'
sdateh = '2019-02-09 00'
bUseNow = True
NowItems = 4

bTestCode = False
bShowTables = False
bChangeMinMax = False
bAddPressure = False
cdate = '2019-02-09'

bAddcurrent = False


dbfile = 'dmonitor.db' 
dth_format = '%Y-%m-%d %H:%M:%S'

if bUseNow:
    dtDateh = datetime.now() - timedelta(hours = NowItems)
    sdateh = str(dtDateh)[:13]
    dtDate = datetime.now() - timedelta(days = NowItems)
    sdate = str(dtDate)[:10]

def showqueryresults(squery):
    print ('squery = '+squery)
    cursor = c.execute(squery)
    icount = 0
    for row in cursor:
        icount += 1
        if icount > 100:
            break
        print (row)
        
   
# create database if it does not exist
conn = sqlite3.connect(dbfile)

# Create a cursor and use connect object
c = conn.cursor()

#call test code here
if bTestCode:
#################### TEST CASE #######################
    dDate = datetime.now() - timedelta(hours = 0)
    dDateLow = dDate - timedelta(hours = 1)
    dDateHi = dDate + timedelta(hours = 1)
    
    #squery = "SELECT datehour, pressure FROM data WHERE ID = '43' AND datehour > '" + str(dDateLow) +"'"
    squery = "SELECT datehour, pressure FROM data WHERE ID = '43' AND datehour > '" + str(dDateLow) +"' AND datehour < '"+str(dDateHi) + "'"

    print ('test query =', squery)
    cursor = c.execute(squery)
    dsum = 0
    dsumcoef = 0
    for row in cursor:
        (dts, press) = row
        dt = datetime.strptime(dts,"%Y-%m-%d %H:%M:%S")
        delta = dDate - dt
        dsec = delta.total_seconds()/3600
        if dsec > -1 and dsec < 0:
            dcoef = 1 + dsec
            dsum += dcoef * press
            dsumcoef += dcoef
            print dsec, press, dsum
        elif dsec < 1 and dsec >= 0:
            dcoef = 1 - dsec
            dsum += dcoef * press
            dsumcoef += dcoef
            print dsec, press, dsum
    print 'dsum = ', dsum, ', dsumcoef=', dsumcoef
    if dsumcoef > 0 and dsumcoef < .999:
        dsumnew = dsum/dsumcoef
        print 'Corrected = ', dsumnew
        

    print 'test done' 

#show recent data
squery = "SELECT datehour, temp, ID FROM data WHERE ID = '" + sid + "' AND datehour > '2019-02-05'"
squery = "SELECT * FROM data WHERE ID = '" + sid + "' AND datehour > '2019-02-05 17'"
squery = "SELECT * FROM data WHERE datehour > '" + sdateh + "'"

if not bTestCode:
    if not bChangeMinMax:
        showqueryresults(squery)

# show recent minmax
squery = "SELECT * FROM minmax WHERE ID = '" + sid + "' AND day > '2019-02-04'"
squery = "SELECT * FROM minmax WHERE day > '" + sdate + "'"
if not bTestCode:
    showqueryresults(squery)

# show current data
if not bTestCode:
    showqueryresults("SELECT * FROM current")


if bChangeMinMax:
    csid = '40'
    squery = "SELECT * FROM minmax WHERE ID = '" + csid + "' AND day = '" + cdate + "'"
    showqueryresults(squery)
    
    # now change
    maxT = 32.2
    maxTime = '02:00p'
    minT = 22.8
    minTime = '06:32a'
    oneTuple = [cdate, csid, minT, minTime, maxT, maxTime]
    c.execute("INSERT OR REPLACE into minmax VALUES (?,?,?,?,?,?)", oneTuple)

    showqueryresults(squery)

    conn.commit()

if bAddcurrent:
    bFound = False
 #   cursor = c.execute("DROP TABLE current")
 
    cursor = c.execute("SELECT name from sqlite_master WHERE type='table' AND name = 'current'")
    for row in cursor:
        bFound = True
        print row
    if not bFound:
        # Add current table
        c.execute('CREATE TABLE current (ID text, DATE date, TEMP real, HUMID real, FPRESS real, DARK real, PRIMARY KEY (ID))')
        conn.commit() 
        print ' Table current added'
    else:
        print 'Table current exists'   

if 0:
    #'CREATE TABLE minmax (DAY datetime, ID text, MINT real, MINTIME text, MAXT real, MAXTIME text , PRIMAR
    s_id = '40'
          
    squery = "SELECT day, id, mint, mintime, maxt, maxtime FROM minmax WHERE id='" + s_id +"' AND day > '" + sdate + "'" + " ORDER BY day DESC"
    showqueryresults(squery)
    
if bAddPressure:
    print 'info data='
    c.execute("PRAGMA table_info(data)")
    print c.fetchall()
    
    # add column
    addColumn = "ALTER TABLE data ADD COLUMN PRESSURE real"
    c.execute(addColumn)

    print 'new data='
    c.execute("PRAGMA table_info(data)")
    print c.fetchall()

if bShowTables:
    print 'new data='
    c.execute("PRAGMA table_info(data)")
    print c.fetchall()    
# close connection
conn.close() 
   
