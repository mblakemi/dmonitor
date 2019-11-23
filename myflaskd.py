#!/usr/bin/python

from flask import Flask, render_template
import sqlite3
from datetime import datetime, timedelta
import math

#17-04-22 Use '/' for ReadThr html files
#19-03-07 Added Source option to view Garage values (until Home is used)
#19-03-09 Added Source option to plots so source is changed but date
# is not changed
#19-11-16 1.01 Support for pressure and delta pressure
#19-11-18 removed Rain column, added Dark option

print 'Version 1.02'

app = Flask(__name__, static_url_path='/static')

#pi ip address is:http://192.168.0.105/
#pi can use localhost instead of ip address

btest = False #True # Run test and not flask

nRestarts = 0
g_timeString="none"

g_nPrev = 0
g_sSource = 0
g_bPressure = 0 # 1 for pressure 2 for Dark



################## htmlOut routines

nMinMaxLines = 31    

dbfile = 'dmonitor.db' 

## Output File names
sHTMLname = './templates/maxmin.html'
sFilePlot = './templates/plot.html'
sFileDataOut = './templates/data%s.html'

#format to convert str(datetime) to datetime
dth_format = '%Y-%m-%d %H:%M:%S'

doPrint = False

#### Classes ##################

class CSensorInfo():
    def __init__(self, sid, sName):
         self.sname = sName
         self.sid = sid

# should really be in dmonitor.db
allSensorInfo = [CSensorInfo('40', 'Outside'), CSensorInfo('43', 'Garage') ]
         
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

########################################################################
### --------- HTML max min routines
########################################################################
    
sprefix = """<!DOCTYPE HTML>
<html>
<head>
<title>T RH data R</title>
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0-beta/css/bootstrap.min.css" integrity="sha384-/Y6pD6FV/Vv2HJnA6t+vslU6fwYXjCFtcEpHbNJ0lyAFsXTsjBbfaDjzALeQsN6M" crossorigin="anonymous">
</head>
<nav class="navbar navbar-dark bg-dark">
  <a class="navbar-brand" href="#">Temperature Dashboard: %s</a>
  <form class="form-inline">
    <a class="btn btn-outline-primary align-right" href="../thrplot">Plot</a>
  </form>
  <form class="form-inline">
    <a class="btn btn-outline-primary align-right" href="../source">Source</a>
  </form>
</nav>
<br>
<div class="container-fluid">
"""
spostfix = """
    </tbody>
  </table>
</div>
</html>
"""

stemphumid = """
<br><font size='16' color='#CC6058'><b>%s</b>:</font>&nbsp;&nbsp;<font size='16' color='red'>%.1f&deg;</font>&nbsp;&nbsp;
<font size='16' color='#145699'>%.1f%% rh</font>&nbsp;&nbsp;
<font size='16' color='black'>dp=%.1f&deg;</font><font size='14' color='black'>
"""

smmline = """
<tr>
    <td>%s</td>
    <td><font size='16' color='#ff4444'>%s&deg </font>(%s)</td>
    <td><font size='16' color='#4285F4'>%s&deg </font>(%s)</td>
</tr>
"""

def MMfromFile(s_id, conn):
    stemp = ''
    dtDate = datetime.now() - timedelta(days = nMinMaxLines)
    sdate = str(dtDate)[:10]
    
    squery = "SELECT day, mint, mintime, maxt, maxtime from minmax WHERE ID = '" + s_id + "' AND day > '" + sdate + "'"+ " ORDER BY day DESC"
    cursor = conn.execute(squery)
    for row in cursor:
        if doPrint:
            print row
#        _parsed = datetime.strptime(str(_now),"%Y-%m-%d %H:%M:%S.%f")
        dtfromDate = datetime.strptime(row[0],"%Y-%m-%d")
        dayDate = dtfromDate.strftime('%a %b %d' )

        mint = str(row[1])
        mintime = row[2]
        maxt = str(row[3])
        maxtime = row[4]
        stemp += smmline % (dayDate, maxt, maxtime, mint, mintime)
    return stemp


infoCardStart = """
<div style="font-size: x-large;" class="col-6 col-sm-4 placeholder">
    <div style="border-color:%s" class="card">
      <div style="background-color:%s" class="card-header">
        <h4 class="card-title text-white">%s</h4>
      </div>
      <div class="card-body">
        <h1 class="card-subtitle mb-2">%.1f&deg;</h1>
        <h5 class="text-muted">Relative Humidity: %.1f%%</h5>
        <h5 class='text-muted'>Dew Point: %.1f&deg;</h5>
"""

infoCardEnd = """
      </div>
    </div>
  </div>
"""

################ Get change in pressure from 2 hours ago in inHg/hr
def getPressDelta(conn, fpress):
    dDate = datetime.now() - timedelta(hours = 2)
    dDateLow = dDate - timedelta(hours = 1)
    dDateHi = dDate + timedelta(hours = 1)
    
    squery = "SELECT datehour, pressure FROM data WHERE ID = '43' AND datehour > '" + str(dDateLow) +"' AND datehour < '"+str(dDateHi) + "'"
#    print ('test query =', squery)
    cursor = conn.execute(squery)
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
#            print dsec, press, dsum
        elif dsec < 1 and dsec >= 0:
            dcoef = 1 - dsec
            dsum += dcoef * press
            dsumcoef += dcoef
 #           print dsec, press, dsum
    #print 'dsum = ', dsum, ', dsumcoef=', dsumcoef
    if dsumcoef == 0:
        return ''
    if dsumcoef > 0 and dsumcoef < .999:
        dsumnew = dsum/dsumcoef
        #print 'Corrected = ', dsumnew
    deltapHour = (fpress - dsum)/2.0
    sret = "%.2f/hr" % (deltapHour)
    if deltapHour > 0:
        sret = '+' + sret
    #print 'sret =', sret
    return sret
    
    
## write all current ID at top and then sid max min
def writehtml(isensor):
    # create database if it does not exist
    conn = sqlite3.connect(dbfile)
    
    shtml = ""
    bWriteHeader = True
    for i, asensor in enumerate(allSensorInfo):
        temp = 0
        humid = 0
        fpress = 0
        dark = 0
        squery = "SELECT date, temp, humid, fpress, dark from current WHERE ID = '"+ asensor.sid + "'"
        cursor = conn.execute(squery)
        for row in cursor:
            (date, temp, humid, fpress, dark) = row
            
        if (bWriteHeader):
            # Use date of data read for header line
            bWriteHeader = False
            dtlast = datetime.strptime(date,"%Y-%m-%d %H:%M:%S.%f")
            shtml =  sprefix % (dtlast.strftime('%I:%M:%S %p'))
            shtml += """<section class="row text-center placeholders">"""
            colors = ['#ff4444', '#aa66cc', '#4285F4', 'rgba(0,0,0,.03)']           
        
        tdewf = TdewF(temp, humid)
        color = colors[min(i, len(colors) - 1)]
        temphtml = infoCardStart % (color, color, asensor.sname, temp, humid, tdewf)
        # add Pressure if non-zero
        if (fpress != 0.0):
            sRise = getPressDelta(conn, fpress)
            sPress = "<h5 class='text-muted'>Pressure: %.2f %s;</h5>" % (fpress, sRise)
            temphtml += sPress
        # add rain if non-zero
        if (dark > 0):
            # print('dark = ' + str(asensor.mm.dark))
            sDark = "<h5 class='text-muted'>Dark: %.0f<h5/>" % dark
            temphtml += sDark
        shtml += temphtml + infoCardEnd

    # End card section
    shtml += "</section><br>"

    # Add data to HTML
    tableHeader1 = "<h2>History: %s</h2>" % allSensorInfo[isensor].sname
    tableHeader2 = """
<div class="table-responsive">
  <table class="table table-striped" style="font-size: xx-large;">
    <thead>
      <tr>
        <th>Date</th>
        <th>Max</th>
        <th>Min</th>
      </tr>
    </thead>
    <tbody>
    """
    shtml += tableHeader1 + tableHeader2

    # Add max, min values
   
    shtml += MMfromFile(allSensorInfo[isensor].sid, conn)

    shtml += spostfix
        
    with open(sHTMLname,'w') as file:
        file.write(shtml)
        
    conn.close()


########################################################################
### --------- HTML plot routines
########################################################################

stplotHeader = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
	<title>Temperature Graph</title>
	<link href="static/examples.css" rel="stylesheet" type="text/css">
	<!--[if lte IE 8]><script language="javascript" type="text/javascript" src="../../excanvas.min.js"></script><![endif]-->
	<script language="javascript" type="text/javascript" src="static/flot/jquery.js"></script>
	<script language="javascript" type="text/javascript" src="static/flot/jquery.flot.js"></script>
	<script type="text/javascript">

	$(function() {

		var tval = [
"""
stplotFooter1 = """		];

		var plot = $.plot("#placeholder", [
			{ data: tval, label: "T"}
		], {
			series: {
				lines: {
					show: true
				},
				points: {
					show: true
				}
			},
			grid: {
				hoverable: true,
				clickable: true
			},
			//yaxis: {
			//	min: -1.2,
			//	max: 1.2
			//}
		});

		$("<div id='tooltip'></div>").css({
			position: "absolute",
			display: "none",
			border: "1px solid #fdd",
			padding: "2px",
			"background-color": "#fee",
			opacity: 0.80
		}).appendTo("body");

		$("#placeholder").bind("plothover", function (event, pos, item) {

			if ($("#enablePosition:checked").length > 0) {
				var x=(pos.x + 24)%24;
				var ampm = "a";
				if (x >= 12) {
					ampm = "p";
				}
				x = x % 12;
				var xh = Math.floor(x);
				var xm = (x - xh)*60;
				if (xh == 0)
					xh=12;
				var str = "( at " + xh.toFixed(0) +":" + xm.toFixed(0)+ ampm + ", T=" + pos.y.toFixed(2) + "*F)";
				$("#hoverdata").text(str);
			}

			if (item) {
				var x = item.datapoint[0],
					y = item.datapoint[1].toFixed(2);
				x = (x+24) % 24;
				var ampm = "a";
				if (x >= 12) {
					ampm = "p";
				}
				x = x % 12;
				if (x >= 0 && x < 1.0) {
                                           x += 12;
                                }
				x = x.toFixed(2) + ampm;
				$("#tooltip").html(item.series.label + " at " + x + " = " + y + " *F")
					.css({top: item.pageY+5, left: item.pageX+5})
					.fadeIn(200);
			}
		});

		$("#placeholder").bind("plotclick", function (event, pos, item) {
			if (item) {
				$("#clickdata").text(" - click point " + item.dataIndex + " in " + item.series.label);
				plot.highlight(item.series, item.datapoint);
			}
		});
	});

	</script>
</head>
<body>
"""

stplotFooter1pressure = """		];

		var plot = $.plot("#placeholder", [
			{ data: tval, label: "T"}
		], {
			series: {
				lines: {
					show: true
				},
				points: {
					show: true
				}
			},
			grid: {
				hoverable: true,
				clickable: true
			},
			//yaxis: {
			//	min: -1.2,
			//	max: 1.2
			//}
		});

		$("<div id='tooltip'></div>").css({
			position: "absolute",
			display: "none",
			border: "1px solid #fdd",
			padding: "2px",
			"background-color": "#fee",
			opacity: 0.80
		}).appendTo("body");

		$("#placeholder").bind("plothover", function (event, pos, item) {

			if ($("#enablePosition:checked").length > 0) {
				var x=(pos.x + 24)%24;
				var ampm = "a";
				if (x >= 12) {
					ampm = "p";
				}
				x = x % 12;
				var xh = Math.floor(x);
				var xm = (x - xh)*60;
				if (xh == 0)
					xh=12;
				var str = "( at " + xh.toFixed(0) +":" + xm.toFixed(0)+ ampm + ", T=" + pos.y.toFixed(2) + "*F)";
				$("#hoverdata").text(str);
			}

			if (item) {
				var x = item.datapoint[0],
					y = item.datapoint[1].toFixed(2);
				x = (x+24) % 24;
				var ampm = "a";
				if (x >= 12) {
					ampm = "p";
				}
				x = x % 12;
				if (x >= 0 && x < 1.0) {
                                           x += 12;
                                }
				x = x.toFixed(2) + ampm;
				$("#tooltip").html(item.series.label + " at " + x + " = " + y + " inHg")
					.css({top: item.pageY+5, left: item.pageX+5})
					.fadeIn(200);
			}
		});

		$("#placeholder").bind("plotclick", function (event, pos, item) {
			if (item) {
				$("#clickdata").text(" - click point " + item.dataIndex + " in " + item.series.label);
				plot.highlight(item.series, item.datapoint);
			}
		});
	});

	</script>
</head>
<body>
"""

stplotTitle = """
	<div id="header">
		<h2>Hourly Temperature Plot: %s</h2>
	</div>
 """  
 
stplotPressureTitle = """
	<div id="header">
		<h2>Hourly Pressure Plot</h2>
	</div>
 """ 

stplotDarkTitle = """
	<div id="header">
		<h2>Hourly Dark Plot</h2>
	</div>
 """ 
  
stplotFooter2 = """
	<div id="content">

		<div class="demo-container">
			<div id="placeholder" class="demo-placeholder"></div>
		</div>

		<p>Try pointing and clicking on the points.</p>

		<p>
			<label><input id="enablePosition" type="checkbox" checked="checked"></input>Show mouse position</label>
			<span id="hoverdata"></span>
			<span id="clickdata"></span>
		</p>
	</div>
</body>
</html>
"""

def write_thplot(isensor, nDaysBack, bPressure):
 
    sID = allSensorInfo[isensor].sid
    
    # create database if it does not exist
    conn = sqlite3.connect(dbfile)
    
    # Create a cursor and use connect object
    c = conn.cursor()
    cursor = c.execute("SELECT min(datehour), max(datehour) from data WHERE id = '" + sID + "'")
    for row in cursor:
        if doPrint:
            print row
        dtfirst = datetime.strptime(row[0], dth_format)
        dtlast = datetime.strptime(row[1], dth_format)
        if doPrint:
            print dtfirst, dtlast
        # go at least one day back
        dtstart = dtlast - timedelta(days = max(nDaysBack, 1))
        dtstart = dtstart.replace(hour = 0)       
        if (nDaysBack == 0):
            dtend = dtlast
        else:
            dtend = dtstart + timedelta(hours = 24)           
        if doPrint:
            print dtstart, dtend
    
    squery =  "SELECT datehour, temp, ID FROM data WHERE ID = '" + sID + "' AND datehour BETWEEN '" + str(dtstart) + "' AND '" + str(dtend) + "'"    
    if bPressure == 1:
        squery =  "SELECT datehour, pressure, ID FROM data WHERE ID = '43' AND datehour BETWEEN '" + str(dtstart) + "' AND '" + str(dtend) + "'"  
    if bPressure == 2:
        squery =  "SELECT datehour, dark, ID FROM data WHERE ID = '40' AND datehour BETWEEN '" + str(dtstart) + "' AND '" + str(dtend) + "'"  

    cursor = c.execute(squery)
    if doPrint:
        print 'squery = ', squery
    
    stplotText = ""
    for row in cursor:
        if doPrint:
            print row,
        dtcur = datetime.strptime(row[0], dth_format)
        stemp = row[1]
        if stemp != None:
            hr = dtcur.hour
            if (dtcur.day != dtstart.day):
                hr = hr + 24
            stplotText = '[' + str(hr) + ',' + str(stemp) + '], ' + stplotText
            if doPrint:
                print dtcur, 'hr = ', hr
               
    strDate = dtstart.strftime('%b %d %Y')
    
    if bPressure == 1:
        splothtml = stplotHeader + stplotText + stplotFooter1pressure 
        splothtml += stplotPressureTitle
    elif bPressure == 2:
        splothtml = stplotHeader + stplotText + stplotFooter1pressure 
        splothtml += stplotDarkTitle
    else:
        splothtml = stplotHeader + stplotText + stplotFooter1 
        splothtml += stplotTitle % allSensorInfo[isensor].sname

    if bPressure == 0:
        splothtml += '<a href="sourcep">Source</a>  '
        splothtml += '<a href="darkp">Dark</a> ' 
        splothtml += '<a href="pressurep">Pressure</a>'        
    if bPressure == 1:
        splothtml += '<a href="darkp">Dark</a> ' 
        splothtml += '<a href="tempp">Temperature</a>'
    elif bPressure == 2:
        splothtml += '<a href="pressurep">Pressure</a> '  
        splothtml += '<a href="tempp">Temperature</a>'
       
    splothtml = splothtml + "<h3>" + strDate + "   "
    splothtml = splothtml + '<a href="prev">Prev</a>  <a href="inoutr">Home</a>'
    if nDaysBack > 0:
        splothtml = splothtml + '   <a href="next">Next</a>'
    splothtml += "</h3>" 
    splothtml += stplotFooter2
    with open(sFilePlot,'w') as file:
        file.write(splothtml)        
    # close connection
    conn.close() 
    
########################################################################
### --------- raw houry data
######################################################################## 


nRestarts = 0
g_timeString="none"

g_nPrev = 0

sprefixHour = """<!DOCTYPE HTML>
<html>
<head>
<title>Sensor %s data: %s</title>
</head>
<h2>Sensor %s data: %s</h2>
"""
spostfix = """
</html>
"""
def hourly_html(isensor, nDaysBack):
    #Get last 10 lines
    sID = allSensorInfo[isensor].sid
    
    # create database if it does not exist
    conn = sqlite3.connect(dbfile)
    # Create a cursor and use connect object
    c = conn.cursor()
    
    cursor = c.execute("SELECT min(datehour), max(datehour) from data WHERE id = '" + sID + "'")
    for row in cursor:
        if doPrint:
            print row
        dtfirst = datetime.strptime(row[0], dth_format)
        dtlast = datetime.strptime(row[1], dth_format)
        if doPrint:
            print dtfirst, dtlast
        # go at least one day back
        dtstart = dtlast - timedelta(days = max(nDaysBack, 1))
        dtstart = dtstart.replace(hour = 0)       
        if (nDaysBack == 0):
            dtend = dtlast
        else:
            dtend = dtstart + timedelta(hours = 24)           
        if doPrint:
            print dtstart, dtend
 

    squery =  "SELECT datehour, temp, humid, dark, id FROM data WHERE ID = '" + sID
    squery += "' AND datehour BETWEEN '" + str(dtstart) + "' AND '" + str(dtend) + "'"
    squery += " ORDER BY datehour DESC"
    cursor = c.execute(squery)
    
    shtmlText = ""
    for row in cursor:
        if doPrint:
            print row
        (datehour, temp, humid, dark, sidtemp) = row
        dtcur = datetime.strptime(row[0], dth_format)
        if doPrint:
            print 'dtcur=', str(dtcur)
        dayDate = dtcur.strftime('%a %b %d: %H' )
        
        scur = dayDate +"    T="+ str(temp)+ "    H="+ str(humid)+ "    Dark="+ str(dark) + "<BR>\n"
        shtmlText += scur

#   Create HTML code
    sname = allSensorInfo[isensor].sname
    spre_adj = sprefixHour % (sID, sname ,sID, sname)
    shtml = spre_adj + shtmlText + spostfix
    sFileHtml = sFileDataOut % sID
    with open(sFileHtml,'w') as file:
        file.write(shtml)
        # close connection
    conn.close()  
        
  

########################################################################
### --------- flask routines
######################################################################## 

@app.route("/d40")
def data40():
    hourly_html(0, 0)
    return render_template('data40.html')


@app.route("/d43")
def data43():
    hourly_html(1, 0)
    return render_template('data43.html')

@app.route("/info")
def hello():
    now = datetime.now()
    timeString = now.strftime("%I:%M:%S %p %a %b %d %Y" )
    templateData = {
        'date' : timeString
    }
    try:
        return render_template('info.html', **templateData)
    except:
        return render_template('retry.html', **templateData)

def doMinMax():
    global g_sSource
    now = datetime.now()
    timeString = now.strftime("%I:%M:%S %p %a %b %d %Y" )
    templateData = {
        'date' : timeString
    }
    try:
        writehtml(g_sSource)
        return render_template('maxmin.html', **templateData)
    except:
        return render_template('retry.html', **templateData)    

@app.route("/inout")
def inout():
    global g_sSource
    global g_bPressure
    g_bPressure = 0
    g_sSource = 0
    return doMinMax()

@app.route("/")
def inoutr_root():
    global g_sSource
    g_sSource = 0
    return doMinMax()

@app.route("/inoutr")
def inoutr():
    global g_sSource
    global g_bPressure
    g_bPressure = 0
    g_sSource = 0    
    return doMinMax()

@app.route("/source")
def source():
    global g_sSource
    g_sSource += 1
    if (g_sSource >= len(allSensorInfo)):
        g_sSource = 0
    return doMinMax()

    
@app.route("/tplot")
def tplot():
    global g_sSource
    global g_bPressure
    g_bPressure = 0
    write_thplot(g_sSource, 0, 0)
    try:
        return render_template('plot.html')
    except:
        now = datetime.now()
        timeString = now.strftime("%I:%M:%S %p %a %b %d %Y" )
        templateData = {
            'date' : timeString
        }
        return render_template('retry.html', **templateData)

@app.route("/thplot")
def thplot():
    try:
        return render_template('thplot.html')
    except:
        now = datetime.now()
        timeString = now.strftime("%I:%M:%S %p %a %b %d %Y" )
        templateData = {
            'date' : timeString
        }
        return render_template('retry.html', **templateData)


@app.route("/stats")
def thrstats():
    cur_timeString = datetime.now().strftime("%I:%M:%S %p %a %b %d %Y" )
    return "At:{}<br><br>Restarts = {} since {}".format(cur_timeString, nRestarts, g_timeString)


@app.route("/thrplot")
def thrplot():
    global g_nPrev
    global g_sSource
    try:
        g_nPrev = 0
        write_thplot(g_sSource, g_nPrev, g_bPressure)
        return render_template('plot.html')
    except:
        now = datetime.now()
        timeString = now.strftime("%I:%M:%S %p %a %b %d %Y" )
        templateData = {
            'date' : timeString
        }
        return render_template('retry.html', **templateData)

@app.route("/sourcep")
def sourcep():
    global g_nPrev
    global g_sSource
    g_sSource += 1
    if (g_sSource >= len(allSensorInfo)):
        g_sSource = 0
    write_thplot(g_sSource, g_nPrev, g_bPressure)
    return render_template('plot.html')

@app.route("/tempp")
def tempp():
    global g_nPrev
    global g_sSource
    global g_bPressure
    g_bPressure = 0
    
    write_thplot(g_sSource, g_nPrev, g_bPressure)
    return render_template('plot.html')

@app.route("/pressurep")
def pressurep():
    global g_nPrev
    global g_sSource
    global g_bPressure
    g_bPressure = 1
    
    write_thplot(g_sSource, g_nPrev, g_bPressure)
    return render_template('plot.html')

@app.route("/darkp")
def darkp():
    global g_nPrev
    global g_sSource
    global g_bPressure
    g_bPressure = 2
    
    write_thplot(g_sSource, g_nPrev, g_bPressure)
    return render_template('plot.html')

@app.route("/prev")
def dataprev():
    global g_nPrev
    global g_sSource
    global g_bPressure
    g_nPrev += 1
    write_thplot(g_sSource, g_nPrev, g_bPressure)
    return render_template('plot.html')

@app.route("/next")
def datanext():
    global g_nPrev
    global g_sSource
    global g_bPressure
    g_nPrev -= 1
    if g_nPrev < 0:
        g_nPrev = 0
    write_thplot(g_sSource, g_nPrev, g_bPressure)
    return render_template('plot.html')


if __name__ == "__main__":
    now = datetime.now()
    if btest:
        writehtml(g_sSource) #min max
        nDaysBack = 2
        mPressure = 2
        write_thplot(g_sSource, nDaysBack, mPressure)
        
        print 'test done'
    else:
        g_timeString = now.strftime("%I:%M:%S %p %a %b %d %Y" )
        for itry in range(1000):
            try:
                app.run(host='0.0.0.0',port=80,debug=True)
            except IOError:
                nRestarts += 1
                print 'IOError *** Restarts ***:', nRestarts
            else:
                print 'Error not handled'
                exit()

        
        
    