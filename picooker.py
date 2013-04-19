#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
PiCooker: a small examples on how to use a yocto-termocouple usb module
"""
#import stadard functions
import sys,os,threading,json
import smtplib
import socket
import urllib2
import urlparse
from optparse import OptionParser
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import urlparse
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
import posixpath
import SimpleHTTPServer
import SocketServer

# import Yoctopuce Pyhton library (installed form PyPI)
from yoctopuce.yocto_api import *
from yoctopuce.yocto_temperature import *
import matplotlib
#force matplotlib do not use any Xwindow backend
matplotlib.use('Agg')
import matplotlib.pyplot as plt

Options=None
MyIP=""
AllSensors ={}


def SendEmail(strFrom,strTo,msgRoot):
    if Options.verbose:
        print "Send email from %s to %s with SMPT infos: %s:%d (%s:%s)" % (strFrom,strTo,Options.mail_host ,Options.mail_port, Options.mail_user ,Options.mail_pass)
    mailServer = smtplib.SMTP(Options.mail_host,Options.mail_port)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    if Options.mail_user!="":
        mailServer.login(Options.mail_user, Options.mail_pass)
    mailServer.sendmail(strFrom, strTo, msgRoot.as_string())
    mailServer.close()
    if Options.verbose:
        print "Email succesfully sent."


class TempRecorder (threading.Thread):
    def __init__(self, sensor,defaultEmail):
        threading.Thread.__init__(self)
        self._lock = threading.Lock()
        self.daemon = True
        self._temp_sensor=sensor;
        self._recording=False
        self._lastValue =YTemperature.CURRENTVALUE_INVALID
        self._email =defaultEmail
        self._target=50
        self._graphResolution=1
        self._last_plot_size=-1
        self._recording_data_x = []
        self._recording_data_y = []
        self._plotfile="http_stuff/plot.%s.png" % self._temp_sensor.get_hardwareId()

    def getName(self):
        return self._temp_sensor.get_friendlyName()

    def getID(self):
        return self._temp_sensor.get_hardwareId()

    def setTargetTemp(self,target_temp):
        if target_temp != self._target:
            print("%s set target to %s"%(self.getName(),target_temp))
        self._target=target_temp

    def setEmail(self,email):
        if email != self._email:
            print("%s set email to %s"%(self.getName(),email))
        self._email=email

    def startRecord(self):
        if self._recording:
            return
        msg="%s Start recording"%self.getName()
        print msg
        self._targetReached=False
        plt.clf()
        self._recording_data_x = []
        self._recording_data_y = []
        self._recording_starttime = datetime.datetime.today()
        self._lastRecorded = datetime.datetime.today()
        self._graphResolution =5 
        self._recording = True
        self.plotGraph()
        self.sendResult(msg,self._lastValue)

    def stopRecord(self):
        if not self._recording:
            return
        msg ="Stop temperature recording for %s"%self.getName()
        print(msg)
        self.plotGraph()
        self.sendResult(msg,self._lastValue)
        self._recording = False

    def addValue(self,temp,force=False):
        global Options
        now = datetime.datetime.today()
        delta = now -self._lastRecorded;
        if delta.total_seconds() > self._graphResolution or force :
            if Options.verbose:
                print("%s add new value (%d)"%(self.getName(),temp))
            from_start_time =  now - self._recording_starttime
            from_start_minutes = from_start_time.total_seconds()/60
            self._recording_data_y.append(temp)
            self._recording_data_x.append(from_start_minutes)
            self._lastRecorded=now;
            if len(self._recording_data_y)==300:
                newres= self._graphResolution*2;
                if Options.verbose:
                    print("%s increase graph interval (%d to %d)"%(self.getName(),self._graphResolution,newres))
                new_x=[]
                new_y=[]
                for i in range(0,len(self._recording_data_y),2):
                    y=(self._recording_data_y[i]+self._recording_data_y[i+1])/2
                    x=(self._recording_data_x[i]+self._recording_data_x[i+1])/2
                    new_x.append(x)
                    new_y.append(y)
                plt.clf()
                self._recording_data_x = new_x
                self._recording_data_y = new_y
                self._graphResolution = newres

    def getStatus(self):
        return {
            'temp':self._lastValue,
            'target': self._target,
            'email': self._email,
            'recording': self._recording,
        }    

    def plotGraph(self):
        global Options
        self._lock.acquire()
        if self._last_plot_size == len(self._recording_data_y):
            self._lock.release()
            return
        start = datetime.datetime.today()
        self._last_plot_size=len(self._recording_data_y)
        plt.plot(self._recording_data_x,self._recording_data_y,color="red")
        plt.ylabel("Temperature")
        plt.xlabel("Time (minutes)")
        plt.savefig(self._plotfile)
        if Options.verbose:
            delta = datetime.datetime.today() -start
            print("%s: graph rendering took %d seconds for %d points"%(self.getName(),delta.total_seconds(),self._last_plot_size))
        self._lock.release()

    def readGraph(self, out_file):
        f = open(self._plotfile)
        out_file.write(f.read())
        f.close()


    def sendResult(self,title,temp):
        # me == my email address
        global Options
        global MyIP
        if self._email=="":
            return
        # Define these once; use them twice!
        strFrom = self._email
        strTo = self._email
        # Create the body of the message (a plain-text and an HTML version).
        baselink = "http://%s:%d" % (MyIP, Options.http_port)
        link = baselink +"/"
        text = "Hi!\n%s\n\nYou can see the cooking graph with the folowing link\n%s" % (title, link)
        f = open("http_stuff/mail.html")
        html=f.read()
        html = html.replace("YYYMSGYYY",title)
        html = html.replace("YYYSERVERYYY",baselink)
        html = html.replace("YY000YY","current value is %2.1f" % temp)
        f.close()
        # Create the root message and fill in the from, to, and subject headers
        msgRoot = MIMEMultipart('related')
        msgRoot['Subject'] = "Pi Cooker: " + title
        msgRoot['From'] = strFrom
        msgRoot['To'] = strTo
        msgRoot.preamble = 'This is a multi-part message in MIME format.'

        # Encapsulate the plain and HTML versions of the message body in an
        # 'alternative' part, so message agents can decide which they want to display.
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)

        msgText = MIMEText(text)
        msgAlternative.attach(msgText)

        # We reference the image in the IMG SRC attribute by the ID we give it below
        msgText = MIMEText(html, 'html')
        msgAlternative.attach(msgText)

        # This example assumes the image is in the current directory
        fp = open(self._plotfile, 'rb')
        img=fp.read()
        print("img size= %d"%len(img))
        msgImage = MIMEImage(img)
        fp.close()

        # Define the image's ID as referenced above
        msgImage.add_header('Content-ID', '<image1>')
        msgRoot.attach(msgImage)
        SendEmail(strFrom,strTo,msgRoot)

    def run(self):
        global Options
        while True :
            if not self._temp_sensor.isOnline():
                self.sendResult('Module %s has been disconnected'%self._temp_sensor.get_friendlyName(),0)
                print "Thread had no found temp_sensor"
                return
            self._lastValue = self._temp_sensor.get_currentValue()
            if Options.verbose : print "%s: temperature is %2.1f c" % (self._temp_sensor.get_friendlyName(),self._lastValue)
            if(self._recording):                    
                if not self._targetReached and self._lastValue>= self._target:
                    self.addValue(self._lastValue,True)
                    msg = "Temperature of %sc for  %s has been reached"%(self._target,self.getName())
                    self._targetReached=True
                    self.plotGraph()
                    self.sendResult(msg,self._lastValue)
                else:
                    self.addValue(self._lastValue)
            YAPI.Sleep(1000)


class MyHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        return

    def do_GET(self):
        global AllSensors
        global Options
        if self.path.startswith("/status.json"):
            arg = urlparse.parse_qs(urlparse.urlparse(self.path)[4])
            #by default use the first detected sensor
            recorder = AllSensors.itervalues().next()
            if arg.has_key("sens"):
                sens = str(arg.get("sens")[0])
                recorder = AllSensors[sens]
            if arg.has_key("target"):
                target_temp = float(arg.get("target")[0])
                recorder.setTargetTemp(target_temp)
            if arg.has_key("email"):
                tmp = str(arg.get("email")[0])
                if tmp!="":
                    recorder.setEmail(tmp)
            if arg.has_key("recording"):
                onoff = str(arg.get("recording")[0])
                if onoff =='true':
                    recorder.startRecord()
                elif onoff=='false':
                    recorder.stopRecord()
            self.send_response(200)
            self.send_header('Content-type',    'application/json')
            self.end_headers()
            response =json.dumps(recorder.getStatus())
            self.wfile.write(response)
        elif self.path.startswith("/list.json"):
            res = []
            for sid in AllSensors:
                sensor = AllSensors[sid]
                res.append({"id":sensor.getID(),"name":sensor.getName()})
            self.send_response(200)
            self.send_header('Content-type',    'application/json')
            self.end_headers()
            response =json.dumps(res)
            self.wfile.write(response)
        elif self.path.startswith("/detail.html"):
            arg = urlparse.parse_qs(urlparse.urlparse(self.path)[4])
            #by default use the first detected sensor
            recorder = AllSensors.itervalues().next()
            if arg.has_key("sens"):
                sens = str(arg.get("sens")[0])
                recorder = AllSensors[sens]
            try:
                f = open("http_stuff/detail.html") #self.path has /XXXX.XXX
                self.send_response(200)
                self.send_header('Content-type',    'text/html')
                self.end_headers()
                page=f.read().decode("latin-1")
                page = page.replace("YYYY_HARDWAREID_YYYY",recorder.getID())
                self.wfile.write(page.encode("latin-1"))
                f.close()
            except IOError:
                self.send_error(404,'File Not Found: %s' % self.path)
        elif self.path.startswith("/plot.png"):
            arg = urlparse.parse_qs(urlparse.urlparse(self.path)[4])
            #by default use the first detected sensor
            recorder = AllSensors.itervalues().next()
            if arg.has_key("sens"):
                sens = str(arg.get("sens")[0])
                recorder = AllSensors[sens]
            recorder.plotGraph()
            self.send_response(200)
            self.send_header('Content-type',    ' image/png')
            self.end_headers()
            try:
                recorder.readGraph(self.wfile)
            except IOError:
                self.send_error(404,'File Not Found: %s' % self.path)
        else:
            SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)


    def translate_path(self, path):
        """translate path given routes"""
        # set default root to cwd
        root = os.getcwd()
        root += "/http_stuff"
        #print("tranlate path %s to %s"%(path,root))
        # normalize path and prepend root directory
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib2.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = root
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir):
                continue
            path = os.path.join(path, word)
        return path



def main():
    """ Main function, deals with arguments and launch program"""
    # Usual verifications and warnings
    global Options
    global MyIP
    sys.stdout.write('PiCooker v1.2 started\n')
    parser = OptionParser()
    parser.add_option("-v", "--verbose", action="store_true",
        help="Write output informations (not only errors).",
        default=False)
    parser.add_option("-p", "--port",
        action="store", type="int", dest="http_port",
        default="8888", help="The port used by the http server"),
    parser.add_option("--email",
        action="store", type="string", dest="email",
        default="", help="The default email where to send result"),
    parser.add_option("--smtp_host",
        action="store", type="string", dest="mail_host",
        default="localhost", help="smtp server host name"),
    parser.add_option( "--smtp_port",
        action="store", type="int", dest="mail_port",
        default="25", help="smtp server port number"),
    parser.add_option("--smtp_user",
        action="store", type="string", dest="mail_user",
        default="", help="Username for smtp authentification"),
    parser.add_option( "--smtp_password",
        action="store", type="string", dest="mail_pass",
        default="", help="Password for smtp authentification"),
    (Options, args) = parser.parse_args()
    # THE program :-)
    if Options.verbose:
        print "SMPT Server infos: %s:%d (%s:%s)" % (Options.mail_host ,Options.mail_port, Options.mail_user ,Options.mail_pass)
        # Setup the API to use local USB devices

    print('Find public IP...')
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("gmail.com",80))
    MyIP = s.getsockname()[0]
    s.close()
    print(' Done (%s)'%MyIP)

    if Options.email!="":
        # Create the body of the message (a plain-text and an HTML version).
        baselink = "http://%s:%d" % (MyIP, Options.http_port)
        link = baselink +"/"
        text = "Hi!\n The PiCooker v1.2 has been started\n\nYou can start the cooking with the folowing link\n%s" % ( link)
        f = open("http_stuff/welcomemail.html")
        html=f.read()
        html = html.replace("YYYSERVERYYY",baselink)
        f.close()
        # Create the root message and fill in the from, to, and subject headers
        msgRoot = MIMEMultipart('related')
        msgRoot['Subject'] = "Pi Cooker Started "
        msgRoot.preamble = 'This is a multi-part message in MIME format.'
        # Encapsulate the plain and HTML versions of the message body in an
        # 'alternative' part, so message agents can decide which they want to display.
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)
        msgText = MIMEText(text)
        msgAlternative.attach(msgText)
        # We reference the image in the IMG SRC attribute by the ID we give it below
        msgText = MIMEText(html, 'html')
        msgAlternative.attach(msgText)
        SendEmail(Options.email,Options.email,msgRoot)
    else:
        print("No default email configured (skip email configuration test)")
   
    errmsg=YRefParam()
    print('List All Yoctopuce temerature Sensors.')
    # Setup the API to use local USB devices
    if YAPI.RegisterHub("usb", errmsg)!= YAPI.SUCCESS:
        sys.exit("init error"+str(errmsg))
    print('...')

    sensor = YTemperature.FirstTemperature()
    while sensor is not None:
        print('- %s'%sensor.get_friendlyName())
        trec =TempRecorder(sensor,Options.email)
        trec.start()
        AllSensors[sensor.get_hardwareId()]=trec;
        sensor = sensor.nextTemperature()
    server=None
    if len(AllSensors)==0:
        sys.exit("No Yocto-Thermocouple detected")        
    try:
        print('Starting HTTP server...')
        SocketServer.TCPServer.allow_reuse_address = True
        server = SocketServer.TCPServer(("", Options.http_port), MyHandler)
        print 'HTTP         server started.'
        server.serve_forever()
        print '---http server stoped'
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()

if __name__ == '__main__':
    main()
