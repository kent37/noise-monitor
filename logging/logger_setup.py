# Citizens noise monitor setup
# 2015, Rene Vega
# 2015-10-01, 1.1 - Clarify setup instructions. Add account maintenance logic.
# 2015-10-01, 1.2 - Ensure message is generated when WiFi dongle is not present
# 2015-11-25, 1.3 - Switch to one button update. Add auth token field.
# 2015-12-25, 1.4 - Cleanup
# 2016-01-23, 1.5 - Update to 'jessie'
# 2016-01-24, 1.6 - Add telephone field

from Tkinter import *
import ttk
import subprocess

import time
import logging
import json
import ssl
import requests
import os
import datetime
import sys
import syslog

Version = '1.6'
Path = os.path.dirname(os.path.realpath(sys.argv[0]))+ '/'

# Set up the window
root = Tk(className ="Noise Monitor Setup " + Version)

# Link status
CurrWlanIPA = '!'
LastWlanIPA = '!!'
LastWlanDB = -999;

# server connection
URL = 'https://skyote.com/nl/nl-serverj.php'
PK  = '569gksxi4e7883,r60etgv-10d'
RefID = ''

# Raspbian linux has a somewhat broken SSL that is going to be fixed soon,
# so in the meantime, disable the warning messages
logging.captureWarnings(True)

# The requests package will maintain keep-alive connections for a session,
# vastly speeds up HTTP accesses.
S = requests.Session()
        
# Log status message both on the applet's status line and in the system log.
def Log(msg):
   global lstatus
   lstatus.config(text=msg)
   syslog.syslog(msg)

# Get the serial number of the Raspberry PI
def GetSerial():
   serial = ''
   f = open('/proc/cpuinfo', 'r')
   for l in f:
      if l[0:6] == 'Serial': serial = l[10:26]
   f.close()
   return serial

# Get the status/IP address of an interface (eth0, wlan0,...)
# Return the IP address or an empty string or '!' when the interfce is not present.
def GetIP(interface):
   try:
      ipa = subprocess.check_output(['ip','-f','inet','addr','show',interface], stderr=subprocess.STDOUT)
      n1 = ipa.find('inet ') + 5
      n2 = ipa.find('/', n1)
      return ipa[n1:n2]
   except:
      return '!'

def GetWifiDB():
   wdb = os.popen('cat /proc/net/wireless | grep wlan').readline()
   wdb += '-127 -127 -127 -127'
   wdbl = wdb.split()
   wdb = wdbl[3];
   return wdb


# This function is called by the tkinter state engine after one second
# It performs various time based housekeeping tasks.
def TimedCallback():
    global S
    global CurrWlanIPA
    global LastWlanIPA
    global LastWlanDB
    CurrWlanIPA = GetIP('wlan0')
    currwlandb = GetWifiDB();
    root.after(1000, TimedCallback)

    # Call the WLAN related functions only when there
    # is a change to the WLAN status.
    if (CurrWlanIPA == LastWlanIPA) and (currwlandb == LastWlanDB): return
    LastWlanDB = currwlandb

    # Update status when the connection status changes
    if CurrWlanIPA != LastWlanIPA:
        LastWlanIPA = CurrWlanIPA
        if CurrWlanIPA == '' or CurrWlanIPA == '!':
            Log('WIFI connection dropped')
        else:
            Log('WIFI connection enabled')
            S = requests.Session()
            RegisterLogger()
            GetLoggerSettings()
            GetAccountSettings()

    BuildWlanStatus()

def BuildWlanStatus():
   global CurrWlanIPA
   global LastWlanDB
   global lintro
   global Serial
   global b1
   global b2

   # Get the WIFI status
   ipa = CurrWlanIPA
   if ipa == '!':
      intro =("Welcome to the citizens noise monitoring system.\n" +
            "The WIFI adapter is not present. Please plug it in to proceed.\n")
      b1.config(state=DISABLED)
      b2.config(state=DISABLED)
   elif ipa != '':
      intro =("Welcome to the citizens noise monitoring system.\n" +
            "Connected via WIFI at IP address " + str(ipa) + "\n" +
            "Signal strength " + LastWlanDB + "dB\n" +
            "Serial #" + Serial)
      b1.config(state=NORMAL)
      b2.config(state=NORMAL)
   else:
      intro =("Welcome to the citizens noise monitoring system. " +
            "To get this unit running start by connecting it to your WIFI access point. " +
            "Follow these steps:\n" +
            "1. Click on the Wifi button, top of the screen to the left of the speaker icon;\n" +
            "2. Click on your access point name;\n" +
            "3. Enter your access point passphrase in the little request window;\n" +
            "In about a minute your WiFi connecttion will be enabled. Once that happens, fill in  the account and address fields.\n")
      b1.config(state=DISABLED)
      b2.config(state=DISABLED)

   lintro.config(text=intro)

def RegisterLogger():
    global Version
    global Path
    global S
    global URL
    global PK
    global RefID
    global CurrWlanIPA
    global Serial

    # Get the settings when the link is up
    if CurrWlanIPA == '' or CurrWlanIPA == '!': return

    # Register using the serial number of the RPI
    # This needs to be done at least once to create a device entry
    RefID = ''
    query_args = { 'Action':'register', 'Serial':Serial, 'PassKey':PK }
    response = S.post(URL, data=json.dumps(query_args))
    #Log(response.content)
    return

def Login():
    global Version
    global Path
    global S
    global URL
    global PK
    global RefID
    global CurrWlanIPA
    global Serial

    # Get the settings when the link is up
    if CurrWlanIPA == '' or CurrWlanIPA == '!': return

    if RefID == '':
        # Log in using the Raspberry PI's serial number. A reference ID is returned
        query_args = { 'Action':'data-login', 'Serial':Serial, 'PassKey':PK }
        response = S.post(URL, data=json.dumps(query_args))
        if response.status_code == 200:
            jresp = json.loads(response.content)
            if jresp['Status'] == 'OK':
                #Log(response.content)
                RefID = jresp['Ref_ID']
            else:
                Log("Login error: " + response.content)
        else:
            Log("Login error: " + str(response.status_code))
    return

def GetLoggerSettings():
    global Version
    global Path
    global S
    global URL
    global PK
    global RefID
    global CurrWlanIPA
    global Serial

    # Get the settings when the link is up
    if CurrWlanIPA == '' or CurrWlanIPA == '!': return
    Login()

    if RefID != '':
        # Get the settings
        query_args = {'Action':'get-data-info', 'Ref_ID':RefID, 'PassKey':PK }
        response = S.post(URL, data=json.dumps(query_args))
        #Log(response.content)
        if response.status_code == 200:
            # Fill in the data fields
            jresp = json.loads(response.content)
            if jresp['Status'] == 'OK':
                #Log(response.content)
                DisplayLoggerSettings(jresp)

def UpdateLoggerSettings():
    global Version
    global Path
    global S
    global URL
    global PK
    global RefID
    global CurrWlanIPA
    global Serial
    global sstreet
    global scity
    global sstate
    global szip
    global sauth

    # Get the settings when the link is up
    if CurrWlanIPA == '' or CurrWlanIPA == '!': return
    Login()

    if RefID != '':
        Log('')
        # Get the settings
        query_args = {'Action':'update-data-info', 'Ref_ID':RefID, 'PassKey':PK,
                      'Address':str(sstreet.get()), 'City':str(scity.get()),
                      'State':str(sstate.get()), 'PostalCode':str(szip.get()),
                      'Auth':str(sauth.get())}
        response = S.post(URL, data=json.dumps(query_args))
        #Log(response.content)
        if response.status_code == 200:
            Log('Monitor settings updated')
        else:
            GetLoggerSettings()
            Log('Update failed: '+ response.content)
    return

def GetAccountSettings():
    global Version
    global Path
    global S
    global URL
    global PK
    global RefID
    global CurrWlanIPA
    global Serial

    # Get the settings when the link is up
    if CurrWlanIPA == '' or CurrWlanIPA == '!': return

    if RefID == '':
        # Log in using the Raspberry PI's serial number. A reference ID is returned
        query_args = { 'Action':'data-login', 'Serial':Serial, 'PassKey':PK }
        response = S.post(URL, data=json.dumps(query_args))
        if response.status_code == 200:
            jresp = json.loads(response.content)
            if jresp['Status'] == 'OK':
                #Log(response.content)
                RefID = jresp['Ref_ID']

    if RefID != '':
        # Get the settings
        query_args = {'Action':'get-account-info', 'Ref_ID':RefID, 'PassKey':PK }
        response = S.post(URL, data=json.dumps(query_args))
        #Log(response.content)
        if response.status_code == 200:
            # Fill in the data fields
            jresp = json.loads(response.content)
            DisplayAccountSettings(jresp)
            #if jresp['Status'] == 'OK':
                #Log(response.content)
    return

def UpdateAccountSettings():
    global Version
    global Path
    global S
    global URL
    global PK
    global RefID
    global CurrWlanIPA
    global Serial
    global sname
    global semail
    global spassword
    global sphone

    # Get the settings when the link is up
    if CurrWlanIPA == '' or CurrWlanIPA == '!': return
    Log('')
    Login()

    if RefID != '':
        # Update the settings
        query_args = {'Action':'update-account-info', 'Ref_ID':RefID, 'Serial':Serial, 'PassKey':PK,
                      'Name':str(sname.get()), 'Email':str(semail.get()),
                      'Password':str(spassword.get()), 'Phone':str(sphone.get())}
        response = S.post(URL, data=json.dumps(query_args))
        #Log(response.content)
        if response.status_code == 200:
            jresp = json.loads(response.content)
            if jresp['Status'] == 'OK':
                Log('Account settings updated')
            elif jresp['Status'] == 'Duplicate':
                Log('Someone else is using this account name')
            elif jresp['Status'] == 'Need Password':
                Log('Password must not be blank')
            elif jresp['Status'] == 'Need Name':
                Log('Name must not be blank')
        else:
            GetLoggerSettings()
            Log('Update failed: '+ response.content)
    return

def DisplayLoggerSettings(jresp):
    global estreet
    global ecity
    global estate
    global ezip

    global sstreet
    global scity
    global sstate
    global szip
    global sauth

    sstreet = StringVar()
    scity = StringVar()
    sstate = StringVar()
    szip = StringVar()
    sauth = StringVar()

    try:
        sstreet.set(jresp['Address'])
        scity.set(jresp['City'])
        sstate.set(jresp['State'])
        szip.set(jresp['PostalCode'])
        sauth.set(jresp['Auth'])
    except:
        pass

    estreet.config(textvariable=sstreet)
    ecity.config(textvariable=scity)
    estate.config(textvariable=sstate)
    ezip.config(textvariable=szip)
    eauth.config(textvariable=sauth)

def DisplayAccountSettings(jresp):
    global ename
    global eemail
    global epassword
    global ephone

    global sname
    global semail
    global spassword
    global sphone

    sname = StringVar()
    semail = StringVar()
    spassword = StringVar()
    sphone = StringVar()

    try:
        sname.set(jresp['Name'])
        semail.set(jresp['Email'])
        sphone.set(jresp['Phone'])
    except:
        pass
    spassword.set('')

    ename.config(textvariable=sname)
    eemail.config(textvariable=semail)
    epassword.config(textvariable=spassword)
    ephone.config(textvariable=sphone)

def UpdateAllSettings():
    UpdateLoggerSettings()
    UpdateAccountSettings()

# -------------------------------
Serial = GetSerial()

lintro = Label(root,
    wraplength=500,
    justify=LEFT,
    text="Initializing, please wait..."
    )
lintro.pack()

lstatus = Label(root,
    wraplength=500,
    justify=LEFT,
    text=''
    )
lstatus.pack()

f1 = Frame(root, relief=SUNKEN, bd="5p")
f1.pack()

f2 = Frame(root, relief=SUNKEN, bd="5p")
f2.pack()

if CurrWlanIPA != '' and CurrWlanIPA != '!': entry_state = "readonly"
else: entry_state = NORMAL

if entry_state == NORMAL:
    l = Label(f1,
        wraplength=400,
        justify=LEFT,
        padx="5p", pady="5p",
        text="Please fill in your primary account information. This permits you to access " +
              "the private data associated with your noise monitor " +
              "at the WEB site.")
    l.pack()
    l = LabelFrame(f1, text="Name", width=380)
    l.pack()
    ename = Entry(l, justify=LEFT, state=entry_state, width=40) # adds a textarea widget
    ename.pack()
    l = LabelFrame(f1, text="Email Address", width=380)
    l.pack()
    eemail = Entry(l, state=entry_state, width=40)
    eemail.pack()
    l = LabelFrame(f1, text="Password", width=380)
    l.pack()
    epassword = Entry(l, state=entry_state, width=40)
    epassword.pack()
    l = LabelFrame(f1, text="Telephone", width=380)
    l.pack()
    ephone = Entry(l, state=entry_state, width=40)
    ephone.pack()

    l = Label(f2,
        wraplength=400,
        justify=LEFT,
        padx="5p", pady="5p",
        text="Please fill in your monitor's location. This information will be saved in " +
             "the server associated with your noise monitor. This is important as the noise " +
             "data has to be associated to where it is taking place."
        )
    l.pack()
    l = LabelFrame(f2, text="Street Address", width=380)
    l.pack()
    estreet = Entry(l, justify=LEFT, state=entry_state, width=40)
    estreet.pack()
    l = LabelFrame(f2, text="City")
    l.pack()
    ecity = Entry(l, state=entry_state, width=40)
    ecity.pack()
    f3 = LabelFrame(f2)
    f3.pack()
    l = LabelFrame(f3, text="State/Province")
    l.pack(side=LEFT)
    estate = Entry(l, state=entry_state, width=20)
    estate.pack()
    l = LabelFrame(f3, text="Postal Code")
    l.pack()
    ezip = Entry(l, state=entry_state, width=10)
    ezip.pack()

    l = Label(f2,
        wraplength=400,
        justify=LEFT,
        padx="5p", pady="5p",
        text="Enter an authorization token to send results to central server. Leave blank, otherwise."
        )
    l.pack()
    l = LabelFrame(f2, text="Auth Token", width=380)
    l.pack()
    eauth = Entry(l, justify=LEFT, state=entry_state, width=48)
    eauth.pack()

    b1 = Button(f1,text="Update Account & Location", command=UpdateAllSettings, disabledforeground='grey')
    b1.pack(side=BOTTOM)
    b2 = Button(f2,text="Update Location", command=UpdateLoggerSettings, disabledforeground='grey')
    b2.pack(side=BOTTOM)

# Get the coms auth token
if os.path.isfile(Path + 'coms_auth'):
    f = open(Path + 'coms_auth');
    PK = f.readline().strip()
    URL = f.readline().strip()
    f.close()
    Log('Coms auth token: ' + PK)
    Log('Coms URL: ' + URL)

Log("Setup - version " + Version)

root.after(1000, TimedCallback)
root.mainloop()
