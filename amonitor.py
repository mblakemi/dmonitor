# -*- coding: utf-8 -*-
"""
Created on Thu Feb 07 11:48:45 2019

@author: Michael

19-04-25 Shortened Could not read error
19-05-29 signal added for alarm if can't read data
** Note, signal.SIGALRM not supported in Windows Python
2019-11-13 Add Pressure
2020-03-26 add try to sleep - sometimes crashed there if 5 read fails
2020-09-14 supports python 3 or python 2, fixed bug in creating 'data' field (added FPRESS)
"""

strNameVer = 'monitordb.py 10 05'

isXfinity = False

tKludgeSec = 5 #Use 15 for original pi and 35 for new pi

# ReadTH.py Read from 8266 /data
import urllib
import re
from datetime import datetime
import time
import math
import sys
import pickle
import os.path
import os
import pdb
import re
import sqlite3
import signal


# determine if Xfinity or Bently ip devices are used
isXfinity = False
print ('Path' + os.getcwd())
thedir = os.path.basename(os.getcwd())
if thedir == 'dmonitor':
    print ('Bentley version: dmonitor directory')
else:
    print ('Xfinity version: NOT dmonitor directory')
    isXfinity = True


sleepmin = 5 # Sampling rate in minutes (was 2)

# debug variables
debugSTOP = False # if true stop after one loop
doPrint = False
bPrintNormal = False
bPrintNoLF = False

  
#determine version
Python3 = True
(major,minor, micro, level, serial) = sys.version_info
if (major == 2):
    Python3 = False
if Python3:
    import urllib.request

else:
    import urllib

def spstr(val):
    return ' '+str(val)

bQuickerInterrupt = False
if os.path.isfile("../set.txt"):
    bQuickerInterrupt = True
    
# Global variables

#strURL40 = 'http://141.133.76.62:8484/data' #basemt
#strURL43 = 'http://141.133.76.227:8484/data' #garage

if isXfinity:
    strURL40 = 'http://10.0.0.98:8484/data' #apt - old outdoor
    strURL43 = 'http://10.0.0.96:8484/data' #garage
#strURL43 = 'http://10.0.0.123:8484/data' #garage
else:
    #Bentley addresses
    # strURL40 = 'http://141.133.76.62:8484/data' #basemt
    # strURL43 = 'http://141.133.76.227:8484/data' #garage   
    strURL40 = 'http://10.100.164.76:8484/data' #basemt
    strURL43 = 'http://10.100.164.40:8484/data' #garage   

# uncomment following line to test could not read error
#strURL43 = 'http://141.133.76.220:8484/data' #test

dbfile = 'dmonitor.db' 

class ValTime():
    def __init__(self, val, dtime):
        self.val = val
        self.dtime = dtime
    def __init__(self):
        self.val = None
        self.dtime = None
   

class CSensor():
    def __init__(self, sURL, sid):
         self.minT = ValTime()
         self.maxT = ValTime()
         self.sURL = sURL
         self.sname = ''
         self.sid = sid
         self.sMMDay = '' # first 10 char of str(datetime)
         self.sDataHour = '' # first 13 char of str(datetime) - through HOUR         
         
# ------------ Dew Point Formulas ------------
#Centigrate
def TdewC(TC, RH):
    try:
        Tdc = 243.04*(math.log(RH/100.0)+((17.625*TC)/(243.04+TC)))/(17.625-math.log(RH/100.0)-((17.625*TC)/(243.04+TC)))   
        return Tdc
    except:
        return 0.0

#Fahrenheit
def TdewF(TF, RH):
    Tdf = 32.0 + TdewC((TF-32.0)*5.0/9.0, RH) * 9.0/5.0
    return Tdf


def print_nolf(astr):
# both
    sys.stdout.write(astr)
#    python3:
#    print (astr, end='')
#    if bPrintNoLF:
#        print astr,
    return

################ Initialization -------------------
print (strNameVer)

allsensors = [CSensor(strURL40, '40'), CSensor(strURL43, '43')]

bin_read = False

def handler(signum, frame):
    print ('Signal handler called with signal', signum)
    raise IOError("Couldn't open device!")

signal.signal(signal.SIGALRM, handler)


############################
# read
# read t,h,rcount, rstring, [name]
def read_t_h_base(s_url, bAddName):
    print_nolf('+')
    
    global allsensors
    global bin_read
    bin_read = True
    temp = None
    humid = None
    rain = 0
    rainDate = ''
    sname = "Unknown"
    readCount = 0
    bRead = False
    fpress = 0.0
    dark = 0.0 

    # Try reading up to 5 times
    while (readCount < 5):
        try:
            print_nolf('.')
            # this should call signal to generate error
            # if can't open and read within 50 seconds
            signal.alarm(50)
            if Python3:
                with urllib.request.urlopen(s_url) as response:
                    print_nolf('o')
                    data = response.read()    
            else:
                f = urllib.urlopen(s_url)
                print_nolf('o')
                data = f.read()
                f.close()
            signal.alarm(0)
            print_nolf('*')
            # Decode the data
            sdata = data.decode("utf-8")

            res = re.findall('temperature\[(.*?)]', sdata)
            if len(res)> 0:
                temp = float(res[0])

            res = re.findall('humidity\[(.*?)]', sdata)
            if len(res)> 0:
                humid = float(res[0])

            res = re.findall('dark\[(.*?)]', sdata)
            if len(res)> 0:
                dark = float(res[0])
                # print ('dark read = ' + str(dark))
                
            res = re.findall('rain\[(.*?)]', sdata)
            if len(res)> 0:
                rain = float(res[0])

            res = re.findall('press\[(.*?)]', sdata)
            if len(res)> 0:
                fpress = float(res[0])
                
            res = re.findall('rainDate\[(.*?)]', sdata)
            if len(res)> 0:
                rainDate = res[0]
                
            if (bAddName):
                res = re.findall('name\[(.*?)]', sdata)
                if len(res)> 0:
                    sname = res[0]
                
            bRead = True
            break
        except:              
            readCount += 1
 
        short_url = s_url
        res = re.findall('//(.*?):8484', s_url)
        if len(res) > 0:
            short_url = res[0]
           
        sError = '\nCould not read ' + short_url 
        sError = sError + ' try ' + str(readCount) + ' at '
        sError = sError + datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        print(sError)
        time.sleep(2) # wait 5 seconds between reads
            
    if not bRead:             
        print('*** read error at *** ' + str(datetime.today()))

    print_nolf('-')

    bin_read = False
    if (bAddName):
        return (temp, humid, rain, rainDate, fpress, dark, sname)
    return (temp, humid, rain, rainDate, fpress, dark)

#def read_t_h(s_url):
#    return read_t_h_base(s_url, False)

def read_t_h_name(s_url):
    return read_t_h_base(s_url, True)


def sTimeap(dtime):
#    shms = dtime.strftime("%I:%M:%S") don't need seconds
    shms = dtime.strftime("%I:%M")
    if dtime.hour < 12:
        shms += 'a'
    else:
        shms += 'p'
    return shms  

###########################
# Set up database if it does not exist
###########################
if not os.path.isfile(dbfile):
    # must create file
    print ('Creating db ' + dbfile)
      
     # create database if it does not exist
    conn = sqlite3.connect(dbfile)
    
    # Create a cursor and use connect object
    c = conn.cursor()
    
    # Create minmax table
    c.execute('CREATE TABLE minmax (DAY datetime, ID text, MINT real, MINTIME text, MAXT real, MAXTIME text , PRIMARY KEY (DAY, ID))')

    # Create data table
    c.execute('CREATE TABLE data (DATEHOUR date, ID text, TEMP real, HUMID real, DARK real, FPRESS real, PRIMARY KEY (DATEHOUR, ID))')

    # Add current table

    c.execute('CREATE TABLE current (ID text, DATE date, TEMP real, HUMID real, FPRESS real, DARK real, PRIMARY KEY (ID))')
    
    # Save (commit) the changes
    conn.commit()
    
    conn.close()
    
############################
# Initialized min max stuff from data
############################
  # create database if it does not exist
conn = sqlite3.connect(dbfile)

# Create a cursor and use connect object
c = conn.cursor()
for asensor in allsensors:
    ## file values
    cursor = conn.execute("SELECT max(day) from minmax WHERE ID = '" + asensor.sid + "'")
    sdtmax = None
    for row in cursor:
        print (row)
        sdtmax = row[0]
    if sdtmax == None:
        print ('No Initial database file')
    else:
        if (sdtmax[:10] == str(datetime.now())[:10]):
            # if for today, save min max information so we can update it
            cursor = c.execute("SELECT day, mint, mintime, maxt, maxtime,id from minmax WHERE ID = '" + asensor.sid + "' and day = '"+ sdtmax + "'" ) 
            for row in cursor:
                print (row)
                asensor.sMMDay = row[0]
                asensor.minT.val = row[1]
                asensor.minT.dtime = row[2] # just hh:mm a or p 
                asensor.maxT.val = row[3]
                asensor.maxT.dtime = row[4]

    # get latest hour for data file
    cursor = conn.execute("SELECT max(datehour) from data WHERE ID = '" + asensor.sid + "'")
    sdtmax = None
    for row in cursor:
        print (row)
        sdtmax = row[0]  # may be None
    if sdtmax != None:
        sdtmax = (sdtmax)[:13]
        print ('sdtmax = '+str(sdtmax))
        asensor.sDataHour = sdtmax
     
# close connection
conn.close()  
   
  
############################
# Main loop
############################

 # create database if it does not exist
conn = sqlite3.connect(dbfile)

# Create a cursor and use connect object
c = conn.cursor()

curDate = str(datetime.now())[:10]

while True: 
    
    date_time = datetime.now()
    sDataHour = str(date_time)[:13]
    newDate = str(date_time)[:10]
    
    if doPrint:
        print ('date time = ' + str(date_time))
    else:
        if bPrintNormal:
            print_nolf(date_time.minute + ' ')
        
    for asensor in allsensors:
        temp = None
        if not bin_read:
            try:
                (temp, humid, rain, rainDate, fpress, dark, sname) = read_t_h_name(asensor.sURL)
                if doPrint:
                    stemp = "T=" + str(temp) + ", H=" + str(humid) + ', Pres =' +str(fpress) + ', dark = ' + str(dark) + ': ' + sname
                    print (stemp)
            except:
                print ('Error reading set no temp')
                temp = None
        else:
            print('Skipped read as bin_read True')
        
        if temp == None:
            stemp = 'No temperature available, skipped ***** ID =' + str(asensor.sid) + "  T =" + str(date_time) 
            print (stemp)
            continue

        #### save current reading
        oneTuple = [asensor.sid, date_time, temp, humid, fpress, dark]
        c.execute("INSERT OR REPLACE into current VALUES (?,?,?,?,?,?)", oneTuple)
       
        
        #### update MinMax
        sDay = str(date_time)[:10]
        
        # update min max
        bChangeMM = False
        bChangeData = False
        sCurMMtime = sTimeap(date_time)
#        print 'MM pre', asensor.sMMDay, sDay, asensor.sid, asensor.minT.val, asensor.minT.dtime, asensor.maxT.val, asensor.maxT.dtime 

        if (asensor.sMMDay != sDay or asensor.minT.val == None or asensor.minT.val > temp):
            asensor.minT.val = temp
            asensor.minT.dtime = sCurMMtime
            bChangeMM = True
        if (asensor.sMMDay != sDay or asensor.maxT.val == None or asensor.maxT.val < temp):
            asensor.maxT.val = temp
            asensor.maxT.dtime = sCurMMtime        
            bChangeMM = True
      
        # overwrite (or add) new min max values each time they change      
        if (bChangeMM):
            asensor.sMMDay = sDay
            oneTuple = [sDay, asensor.sid, asensor.minT.val, asensor.minT.dtime, asensor.maxT.val, asensor.maxT.dtime ]
            c.execute("INSERT OR REPLACE into minmax VALUES (?,?,?,?,?,?)", oneTuple)
            if bPrintNormal:
                stemp = 'MM updated' + spstr(asensor.sid) + spstr(asensor.minT.val) + spstr(asensor.minT.dtime) + spstr(asensor.maxT.val)+ spstr(asensor.maxT.dtime)
                print (stemp)
            
        #### update hourly data if hour change
        # if hour different, then add hour values to data file
        if (asensor.sDataHour == None or sDataHour != asensor.sDataHour):
            asensor.sDataHour = sDataHour
            sDataDT = str(date_time)[:19]
            oneTuple = [sDataDT, asensor.sid, temp, humid, dark,fpress]
            c.execute("INSERT OR REPLACE into data VALUES (?,?,?,?,?,?)", oneTuple)
            bChangeData = True
            if bPrintNormal:
                print ('Data written' + spstr(asensor.sid) + spstr(sDataDT) + spstr(temp) + spstr( humid) + spstr( dark))
        
        # Save (commit) the changes
##        if (bChangeMM or bChangeData):
##            conn.commit()
        conn.commit()             
        
     # Adjust time so close to sleepmin interval
    # (set at top of program) tKludgeSec = 15
    today = datetime.today()
    tsec = float(today.minute * 60) + today.second + float(today.microsecond/1000000.0)
#   print (tsec)
    dcur = math.floor(float(tsec)/(60.0 * sleepmin))
    nextSleepSec = (dcur + 1) * sleepmin * 60 - tsec + tKludgeSec
#   print('nextSleepSec', nextSleepSec)
    if (debugSTOP):
        sys.exit()
        
    if bQuickerInterrupt:
        if bPrintNormal:
            print ('Sleep = ' + str(nextSleepSec) + '  datetime=' + str(datetime.now()))
        nSpeedup = 100
        shortSleep =  nextSleepSec/nSpeedup
        for ii in range(nSpeedup):
            time.sleep(shortSleep)
    else:
        # just sleep the whole time 
        try:       
            time.sleep(nextSleepSec)
        except  IOError as er:
            print('except in SLEEP', er)

 # close connection
conn.close()    
#sys.exit()   
    
    
    
