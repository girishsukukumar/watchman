#!/usr/bin/python
import glob
import os
import shutil
import telegram
import socket
from   datetime import datetime
import time 
import datetime
import logging 
import pickle 
import errno 
import sys
import re as regularexpression
import subprocess
import argparse
from collections import namedtuple

DiskUsage = namedtuple('DiskUsage', 'total used free')

#  A constants are decleated here
IMAGE_ROOT = "/media/usb/images"
MOTION_THREASHOLD_GAP = 15 
g_message_to_user = "Hello"

# All Globals are initialized here.
g_message_to_user_flag = False 
g_video_to_user_flag = False 
g_RecordingStatus = True 
g_timeOfLastMovement = "0" 
g_imageOfLastMovement = "./msg_images/default.jpg" 
g_photo_to_user  = "./msg_images/default.jpg"
g_video_to_user  = ""
g_post_photo_to_user_flag = False 
g_hostname = ""
g_lastTimeOfMovementDectectedinEpoc = 0 
g_photo_when_motion_detected = "./msg_images/default.jpg"
g_motion_detected_after_threshold = False 
g_previousKeepAliveSendTime = 0  
g_first_photo_of_a_sequence  =  "./msg_images/default.jpg"
g_last_sequence_no  =  0 
g_internetConnected = True 
g_KEEP_ALIVE_TIME_OUT = 900 # 15 mintes
g_KEEP_ALIVE_PHOTO_FLAG = True
g_time_pattern = ""
g_logFile = "LogFile_name_not_set"


# ##############################################################
#  ******** Python Routines Definitions start here ****************
# ##############################################################
def disk_usage(path):
    """Return disk usage statistics about the given path.
          Will return the namedtuple with attributes: 'total', 'used' and 'free',
          which are the amount of total, used and free space, in bytes.
    """
    st = os.statvfs(path)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    return DiskUsage(total, used, free)

def CheckInternet():
  try:
    host = socket.gethostbyname('8.8.8.8')
    s = socket.create_connection((host, 53), 2)
    return True
  except:
     pass
  return False

# ##############################################################
#  ********  End of CheckInternet
# ##############################################################



def CreateFolders(path):
    logging.info('CreateFolders')
    for i in range(0,24):
        if len(str(i)) == 1:
           hour_string = "0" + str(i)
        else:
           hour_string = str(i)
        target_path = path + "/" + hour_string
        if os.path.exists(target_path) == False:
           os.mkdir(target_path)
           logging.info(target_path)
    logging.info('Endof CreateFolders')
       
    return 


def MonitorFiles(path):

    global g_RecordingStatus  
    global g_timeOfLastMovement
    global g_imageOfLastMovement  
    global g_lastTimeOfMovementDectectedinEpoc
    global g_photo_when_motion_detected
    global g_motion_detected_after_threshold 
    global MOTION_THREASHOLD_GAP
    global g_first_photo_of_a_sequence
    global g_last_sequence_no

    #os.listdir(".")

    #logging.info('MonitorFiles')
    previous_Seq_no = 0 
    imageFiles = glob.glob("./*.jpg")
    for imagename in imageFiles:
       presentTimeinEpoc =  int(time.time())
       fields = imagename.split('-')
       sequenceNo = fields[0]
       
       if sequenceNo != g_last_sequence_no :
         g_first_photo_of_a_sequence = imagename  
         g_last_sequence_no = sequenceNo

       day = fields[1]
       month = fields[2]
       year = fields[3]
       timestamp = fields[4]
       timefields = timestamp.split('_')
       hour = timefields[0]
       minutes = timefields[1]
       seconds = timefields[2]
       target_folder = path + "/" + hour
       g_timeOfLastMovement =  " Date:" +  day + "-" + month + "-" + year + " at: Time " 
       g_timeOfLastMovement = g_timeOfLastMovement +  hour + " Hours, " +  minutes + " Min, " + seconds + " Sec"
         
       if g_RecordingStatus == True:
          target_file = target_folder + "/" + imagename
          # Check whether the target file exist inside the folder 
          # This happens when there is a power down condition
          if os.path.isfile(target_file) == False: # File does not exist 
             try:
                shutil.move(imagename, target_folder)
                g_imageOfLastMovement = target_folder + "/" + g_first_photo_of_a_sequence 
                pickle.dump(g_timeOfLastMovement,open("timeOfLastMovement.p","wb"))
             except Exception as error_string:
                logging.info('Error while moving file: %s \n', str(error_string))
                logging.info('Function MonitorFiles during shutil.move of %s to %s',
                              imagename,
                              target_folder)
          else: # File exist so delete the target file and Move the orginal file again
                # This condition happens when there is power down 
                os.remove(target_file) 
                try:
                    shutil.move(imagename, target_folder)
                    g_imageOfLastMovement = target_folder + "/" + g_first_photo_of_a_sequence 
                    pickle.dump(g_timeOfLastMovement,open("timeOfLastMovement.p","wb"))
                except Exception as error_string:
                    logging.info('Error while moving file: %s \n', str(error_string))
                    logging.info('Function MonitorFiles during shutil.move of %s to %s',
                                  imagename,
                                  target_folder)
       else:
          os.remove(imagename)
          g_imageOfLastMovement = "./msg_images/norecording.jpg"  

       diff = presentTimeinEpoc - g_lastTimeOfMovementDectectedinEpoc
       g_lastTimeOfMovementDectectedinEpoc  = presentTimeinEpoc

       diff = (diff/60)  # diff is in minutes
       if diff >= MOTION_THREASHOLD_GAP :
          if g_motion_detected_after_threshold == False:
            g_motion_detected_after_threshold = True 
            logging.info('Motion detected %s',g_first_photo_of_a_sequence)
            g_photo_when_motion_detected = target_folder + "/" + g_first_photo_of_a_sequence
            # Keep a counter and add a sequence of 3 or photos or 
            # short movie clip to be send to user

       pickle.dump(g_timeOfLastMovement,open("lastmovement.p","wb"))

    return 

def CreateDailyFolders():
     global IMAGE_ROOT 
     global g_logFile
     #logging.info('Create Daily folders')
     now = datetime.datetime.now()
     today = now.strftime("%d-%b-%Y")
     today_path = IMAGE_ROOT + "/" + today  
     if os.path.exists(today_path) == False:
         os.mkdir(today_path)
         CreateFolders(today_path)
         #StopLogging() #Stop the logging so that  new log file is create each day
         #os.remove(g_logFile) #delete the old log file
         #os.remove("nohup.out") # delete the nohup.out
         #StartLogging() 
     return  today_path

def touch(fname, times=None):
    fhandle = open(fname, 'a')
    try:
        os.utime(fname, times)
    finally:
        fhandle.close() 

def GenerateVideoForTheHour(hour,minutes):
    global IMAGE_ROOT 

    #We process only for today not for all dates

    #Check images are there in given hour or not
    #IF there generate video and send it out
    #From a path to that location

    logging.info("Calling GenerateVideoFortheHour |%s| |%s|",hour,minutes)
    now = datetime.datetime.now()
    today = now.strftime("%d-%b-%Y")
    logging.info("hour parameter is|%s|",hour)
    path = IMAGE_ROOT + "/" + today
    if int(hour) < 10:
        hour_string = "0" + str(hour)
        logging.info("hour_string is set to =|%s|",hour_string)
    else:
        hour_string = str(hour)
        logging.info("Else:hour_string is set to =|%s|",hour_string)

    logging.info("Calling GenerateVideoFortheHour hour_string |%s|",hour_string)

    path = path + "/" + hour_string
    
    path_to_video = " "

    if int(hour) > 23:

        error_msg =  "Hour value is: " + hour + "This Value cannnot be larger than 23" 
        return error_msg,path_to_video

    # We ignore minutes for now
    # Check whether the path exists or not
    if os.path.exists(path) == False:
        error_msg =  "The" + path + "does not exist, check with your administrator"
        return error_msg,path_to_video

    # Check there are any files

    jpeg_files =  path + "/*.jpg"

    imageFiles = glob.glob(jpeg_files)

    if len(imageFiles) == 0:
       error_msg =  "No movements were seen during the period   " + str(hour) + ":" + str(minutes) + " to "  + str(hour+1) + "00"
       return error_msg,path_to_video

    #video_file_name = today + "_" + hour_string + "_" + str(minutes) + ".avi"
    video_file_name = today + "_" + hour_string + "_" + str(minutes) + ".gif"

    path_to_video = path + "/" + video_file_name
   
  
    #ffmpeg_utility = "ffmpeg -nostdin -pattern_type glob  -i \"*.jpg\"  -r 15  -vcodec libx264  " + video_file_name 
    ffmpeg_utility = "ffmpeg -nostdin -pattern_type glob  -i \"*.jpg\"  -r 15  -vcodec gif  " + video_file_name 

    logging.info(ffmpeg_utility)

    error_string = "Unable to generate video System Error"

    os.chdir(path) # Change directory to run the ffmepg
    cwd = os.getcwd()
    log_string = "Current directory changed to " + cwd
    logging.info(log_string)

    # Generate the video 
    try:
          retVal = os.system(ffmpeg_utility)
    except Exception,err:
          error_string = str(err)
          logging.info(' Error While generating time lapse video %s ', error_string)
          path_to_video = path + "/" + video_file_name
        
    os.chdir(IMAGE_ROOT) # come back to the orginal location
    cwd = os.getcwd()
    log_string = "Current directory changed to " + cwd
    logging.info(log_string)
    # Finally Check whether the video was generated or not

    if retVal != 0 :
       return 'Error while generating  video', " "
    elif os.path.isfile(path_to_video) == True:
        return "No Error", path_to_video
    else:
        return error_string ," "



def ProcessIconBasedMessages(msg):
    # We can assume this is a icon message
    # Check this is know icon or not
    global g_time_pattern
    global g_video_to_user
    global g_video_to_user_flag 
    global g_message_to_user 
    global g_message_to_user_flag 
    global g_photo_to_user
    global g_post_photo_to_user_flag


    g_video_to_user_flag = False 
    logging.info("ProcessIconBasedMessage")

    log_string = "Command is " + msg + " Icon Val = " + msg[0] 
    logging.info(log_string)

    unicode_char = msg[0]
    icon = ord(unicode_char)

    if (icon == 128249) or (icon == 127902) or (icon == 127909):
        action = "Send Video"
    elif (icon == 128248) or  (icon == 128247):
        action = "Latest Photo"
    else:
        action = "Invalid"

    if action == "Send Video":
          #Send Video of last one hour   
          # check the buffer if a time is specificed or not

          # Remove the icon char and extract the rest of the string for text
          logging.info('Video request icon received')

          substring = msg[1:] 

          if substring == "":
             # User did not specify an hour so take the current hour
             logging.info('User Did not specify a time')
             hours = datetime.datetime.now().hour
             minutes = datetime.datetime.now().minute
             error, path = GenerateVideoForTheHour(hours,minutes)
             logging.info("Returned from GenerateVideoFortheHour")
             logging.info(error)
             logging.info(path)


             if error == "No Error":
                g_video_to_user = path
                g_video_to_user_flag = True
                logging.info("video generated")

             else:
                g_message_to_user = error
                g_message_to_user_flag = True  
                logging.info(g_message_to_user)
          else:
             log_string = 'User Did specify a time' + substring
             logging.info('User Did  specify a time')
             substring = substring.replace(" ","") # remove white spaces
             substring = substring.strip() # remove white spaces
             logging.info(substring)
             if g_time_pattern.match(substring) !=  None:
                # break it into hours and minutes
                hours = substring.split(':')[0]
                mins =  substring.split(':')[1]
                hours = hours.replace(" ","") # remove white spaces if any 
                # for now we are ignoring the minutes part
                error, path = GenerateVideoForTheHour(hours,mins)
                if error == "No Error":
                  g_video_to_user = path
                  g_video_to_user_flag = True
                  logging.info(g_message_to_user)
                else:
                  g_message_to_user = error
                  g_message_to_user_flag = True  
                  logging.info(g_message_to_user)
             else:
                g_message_to_user = "|" + substring + "|" + "is not a valid time" 
                g_message_to_user_flag = True  
                logging.info(g_message_to_user)
    elif (action == "Latest Photo"):
          # Send the last photo to user 
                g_message_to_user = "Last movement was observed at" + g_timeOfLastMovement
                g_message_to_user_flag = True
                g_photo_to_user = g_imageOfLastMovement
                logstring = "Photo to be send is " + g_imageOfLastMovement
                logging.info(logstring)
                g_post_photo_to_user_flag = True
    else:
              g_message_to_user =  " Unknown Icon Command " 
              g_message_to_user_flag = True  
              logging.info(g_message_to_user)


    return 


def ProcessIncommingTelegramMessages(msg):
    global g_message_to_user 
    global g_message_to_user_flag 
    global g_timeOfLastMovement
    global g_RecordingStatus  
    global g_imageOfLastMovement  
    global g_photo_to_user   
    global g_post_photo_to_user_flag 
    global g_KEEP_ALIVE_PHOTO_FLAG

    text = msg.lower()
    if len(text) == 0:
        logging.info('ProecessIncomingMessage: Empty message received in <text> ')
        logging.info('Skipping the message')
        return


    logging.info('ProecessIncomingMessage: Entered')
    logging.info('ProcessIncommingMessages: Command is: %s ',text)

    # Check whether this is icon/emoji message or not

    icon = ord(text[0])
    log_string = "Command is " + msg + " Icon Val = " + str(icon)
    logging.info(log_string)

    if icon > 127:
        ProcessIconBasedMessages(text)
    elif text == "no photo":
        g_KEEP_ALIVE_PHOTO_FLAG = False 
        g_message_to_user_flag = True  
        g_message_to_user = "Photo of last movement will not be sent\
                               periodically, instead you will see only date \
                               and time of last movement. Use the command Photo ON \
                               to enable it again"
    elif text == "photo on":
        g_KEEP_ALIVE_PHOTO_FLAG = True 
        g_message_to_user_flag = True  
        g_message_to_user = "Photo of last movement will be send periodically"
    elif text == "recording status":
       if g_RecordingStatus == True:
          g_message_to_user_flag = True  
          g_message_to_user = "Recording is ON"
       else:
          g_message_to_user = "Recording is OFF" 
          g_message_to_user_flag = True  
    elif text == "stop recording":
       g_RecordingStatus  = False 
       g_message_to_user = "Recording Stopped"
       pickle.dump(g_RecordingStatus,open("recordingstatus.p","wb"))
       g_message_to_user_flag = True  
    elif text == "start recording":
       g_RecordingStatus  = True  
       g_message_to_user = "Recording Started"
       g_message_to_user_flag = True  
       pickle.dump(g_RecordingStatus,open("recordingstatus.p","wb"))
    elif text == "disk space":
        total,used,free= disk_usage(IMAGE_ROOT)
        freemegaBytes = free/(1024*1024)
        g_message_to_user = "Free Space = " +str(freemegaBytes) + " Mega Bytes" 
        g_message_to_user_flag = True 
    elif text == "recent activity":
        g_message_to_user = "Last movement was observed at" + g_timeOfLastMovement
        g_message_to_user_flag = True 
        g_photo_to_user = g_imageOfLastMovement
        logstring = "Photo to be send is " + g_imageOfLastMovement
        logging.info(logstring)
        g_post_photo_to_user_flag = True 
    elif text == "report":
        g_message_to_user = "To be Implemented"
        g_message_to_user_flag = True 
    elif text == "help":
        g_message_to_user = "-----------------\n \
                             1. Report\n \
                             2. Recent Activity\n \
                             3. Start Recording\n \
                             4. Stop Recording\n \
                             5. Disk Space \n \
                             6. Recording Status\n \
                             7. No Photo To disable display of photo\n \
                             8. Photo: to enable showing photo\n"
        
        g_message_to_user_flag = True 
    else:
         g_message_to_user = "This is not a valid command " + msg  
         g_message_to_user_flag = True 
    return 


def SendVideoToUsers(bot_id):
    global g_video_to_user 
    global g_previousKeepAliveSendTime
    global g_internetConnected

    logging.info('SendVideoToUsers video file is:')
    logging.info(g_video_to_user)

    if g_internetConnected == False:
       logging.info('Internet Connection not available')
       return
    g_previousKeepAliveSendTime =  int(time.time())
    
    try:
         msg_id = bot_id.getUpdates()[-1].message.chat_id
    except:
         error_string = sys.exc_info()[0]
         logging.info('SendVideo: Network Error while trying get updates : %s ',
                     error_string)
    try:
        msg = "Not updated"
        msg = bot_id.sendDocument(chat_id=msg_id, document=open(g_video_to_user,'rb'))
        logging.info('Status Returned from sending video: %s', msg);
        os.remove(g_video_to_user)
    except:
         error_string = sys.exc_info()[0]
         logging.info('Network Error while trying to send video : %s ',
                     error_string)

    logging.info('Exit From SendVideoToUsers');
    return

def SendMessagesToUsers(bot_id):
    global g_message_to_user 
    global g_hostname
    global g_previousKeepAliveSendTime
    global g_internetConnected

    logging.info('SendMessagesToUSers')
    if g_internetConnected == False:
       logging.info('Internet Connection not available')
       return
    g_previousKeepAliveSendTime =  int(time.time())
    try:
         msg_id = bot_id.getUpdates()[-1].message.chat_id
    except:
         error_string = sys.exc_info()[0]
         logging.info('Network Error while trying to send data : %s ',
                     error_string)
         
    g_message_to_user = g_hostname + ":" + g_message_to_user 

    try:
        bot_id.sendMessage(chat_id=msg_id, text=g_message_to_user)
    except:
         error_string = sys.exc_info()[0]
         logging.info('Network Error while trying to send data : %s ',
                     error_string)

    g_message_to_user = ""
    return 



def SendPhotoToUsers(bot_id):
    global g_photo_to_user   
    global g_previousKeepAliveSendTime
    global g_internetConnected

    logstring = ""
    logging.info('SendPhotoToUsers')
    logstring = "Photo to be sent is: " + g_photo_to_user 
    logging.info(logstring)

    g_previousKeepAliveSendTime =  int(time.time())
    if g_internetConnected == False:
       logging.info('Internet Connection not available')
       return

    try:
        msg_id = bot_id.getUpdates()[-1].message.chat_id
    except:
         error_string = sys.exc_info()[0]
         logging.info('Network Error while trying to send data : %s ',
                     error_string)
    try: 
        logstring = "Sending photo " + g_photo_to_user 
        logging.info(logstring)
        bot_id.sendPhoto(chat_id=msg_id, photo=open(g_photo_to_user,'rb'))
    except:
         error_string = sys.exc_info()[0]
         logging.info('Network Error while trying to send data : %s ',
                     error_string)
    g_photo_to_user = "./msg_images/default.jpg"
    return 


def RemoveOldTimeLapseVideo():
    global IMAGE_ROOT
    return

def StopLogging():
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    return

def StartLogging():
     global g_logFile
     now = datetime.datetime.now()
     today = now.strftime("%d-%b-%Y")
     g_logFile = "Classify_Log-" + today + ".log"
     #Reconfigure logging again, this time with a file.
     logging.basicConfig(format='%(asctime)s %(message)s',
                           filename=g_logFile, 
                           level=logging.INFO)
     return 

def main():
       global IMAGE_ROOT 
       global g_message_to_user 
       global g_message_to_user_flag
       global g_post_photo_to_user_flag
       global g_photo_to_user 
       global g_timeOfLastMovement
       global g_RecordingStatus
       global g_motion_detected_after_threshold
       global g_hostname 
       global g_previousKeepAliveSendTime
       global g_internetConnected
       global g_time_pattern
       global g_video_to_user_flag
       global g_KEEP_ALIVE_PHOTO_FLAG
       global g_lastTimeOfMovementDectectedinEpoc

       # Create script kill the daemon process
       processID  = os.getpid() 
       stopScript = open('StopClassify','w')       
       stopScript.write('#!/bin/sh\n')
       stopCmd = "kill -9 " + str(processID) + " \n" 
       stopScript.write(stopCmd)
       stopScript.close()

       presentTimeinEpoc =  int(time.time())
       g_previousKeepAliveSendTime = presentTimeinEpoc 

       # Get the hostname
       g_hostname = socket.gethostname()


       #This is to handle the initial condition where the pickle file is not present
       os.chdir(IMAGE_ROOT)

       #Load all pickled information if it is saved else take default values
       if os.path.isfile("lastmovement.p") and os.path.getsize("lastmovement.p") > 0 :
          g_timeOfLastMovement = pickle.load(open("lastmovement.p","rb"))
       else:
          g_timeOfLastMovement = "0"
          pickle.dump(g_timeOfLastMovement,open("lastmovement.p","wb"))
          

       if os.path.isfile("recordingstatus.p") and os.path.getsize("recordingstatus.p") > 0:
          g_RecordingStatus = pickle.load(open("recordingstatus.p","rb"))
       else:
          g_RecordingStatus = True           
          pickle.dump(g_RecordingStatus,open("recordingstatus.p","wb"))


       index_to_recentMessage = 0

       if os.path.isfile("index_to_prev_msg.p") and  os.path.getsize("index_to_prev_msg.p") > 0:
           index_to_previous_message = pickle.load(open("index_to_prev_msg.p", "rb" ))
       else:
           index_to_previous_message  = -1          
           pickle.dump(index_to_previous_message,open( "index_to_prev_msg.p", "wb" ))


       # Start Logging

       StartLogging()
       logging.info('Started')
       root_logger = logging.getLogger()
       #root_logger.disabled = True

       # Create Regular expression pattern to parse the time input given by user and store it in a global variable

       g_time_pattern = regularexpression.compile("[0-9]*:[0-9]*")

       bot = telegram.Bot(token='116375346:AAE0PR7BKBp5b4RbUP7eCInVqQYAwmSuwgw')

       g_message_to_user = "Camera Powered Up"

       SendMessagesToUsers(bot)

       total,used,free= disk_usage(IMAGE_ROOT)

       percentageStorageAvailable = (free/total) *100
       
       if percentageStorageAvailable < 20 : 
          g_message_to_user = "Storage Space is running low: " + str(percentageStorageAvailable) + " % of free space is only available"
          SendMessagesToUsers(bot)

       # Get into an infinite loop
       # keep checking for new images and process if any
       # keep checking from incomming messages from users
       # post messages to users

       while 1:
           presentTimeinEpoc =  int(time.time())
           temp_internetConnected = CheckInternet()  

           if temp_internetConnected == False:
               if g_internetConnected == True:
                  # Internet connection just lost remember the time
                  internetConnectionLostTime = presentTimeinEpoc
                  logging.info('Internet connection Lost')
                  logging.info('At time %s',datetime.datetime.fromtimestamp(internetConnectionLostTime).strftime('%c'))
                  
             
           if temp_internetConnected == True:
               if g_internetConnected == False:
                  # Internet connection just  restored
                  logging.info('Internet connection Restored')
                  logging.info('At time %s',datetime.datetime.fromtimestamp(1347517370).strftime('%c'))
                  msg = "Internet Connection was Lost at  "  + str(internetConnectionLostTime)
                  g_message_to_user = msg
                  SendMessagesToUsers(bot)
                  g_message_to_user = "Internet connection restored now"
                  SendMessagesToUsers(bot)


           g_internetConnected = temp_internetConnected 
           touch("Classify.touch")        
	   os.chdir(IMAGE_ROOT)
           RemoveOldTimeLapseVideo()
           today_path = CreateDailyFolders()
	   MonitorFiles(today_path)
           msg_from_user = " "
           if g_internetConnected == True:
              try:
                 updates  = bot.getUpdates()
                 recentMessage = updates[-1] 
                 index_to_recentMessage = len(updates) -1 
                 msg_from_user = recentMessage.message.text.strip('/')
                 #logging.info('Recent message = %s ',recentMessage.message.text)
              except Exception as errorString:
                 logging.info('Error %s \n', str(errorString))
                 logging.info('Error while receiving updates from Bot ')

           #logging.info('Recent message idx = %d ',index_to_recentMessage)
           #logging.info('Previous message idx = %d ',index_to_previous_message)

           if index_to_recentMessage != index_to_previous_message : 
              #index_to_previous_message = index_to_recentMessage 
              pickle.dump(index_to_previous_message,open( "index_to_prev_msg.p", "wb" ))
              g_message_to_user = "Processing your request..." + msg_from_user
              SendMessagesToUsers(bot)

              g_message_to_user = "Please wait...."
              SendMessagesToUsers(bot)

              g_message_to_user = ""
              ProcessIncommingTelegramMessages(msg_from_user)

           if g_message_to_user_flag == True:
              SendMessagesToUsers(bot)
              g_message_to_user_flag = False

           if g_post_photo_to_user_flag == True:
              SendPhotoToUsers(bot)
              g_post_photo_to_user_flag = False

           if g_video_to_user_flag == True:
               SendVideoToUsers(bot)
               g_video_to_user_flag = False

           if g_motion_detected_after_threshold == True:
              g_message_to_user ="Some Movements Observed..."
              log_string = "Motion detected image to be posted" + g_photo_when_motion_detected 
              logging.info(log_string)
              SendMessagesToUsers(bot)
              g_photo_to_user = g_photo_when_motion_detected
              SendPhotoToUsers(bot)
              g_motion_detected_after_threshold = False

           index_to_previous_message = index_to_recentMessage 
           # Check when was the last Keep alive message sent  
           diff = presentTimeinEpoc - g_previousKeepAliveSendTime

           if diff > g_KEEP_ALIVE_TIME_OUT:
              logging.info('Diff for keep alive = %d ',diff)
              logging.info('presentTimeinEpoc %d ',presentTimeinEpoc)
              logging.info('g_previousKeepAliveSendTime %d',
                            g_previousKeepAliveSendTime) 
              g_message_to_user ="Camera is Live "
              SendMessagesToUsers(bot)
              silenceperiod =  presentTimeinEpoc - g_lastTimeOfMovementDectectedinEpoc 
              #silenceperiod  =  presentTimeinEpoc - g_previousKeepAliveSendTime 
              # calculate the silence period, in min or hours or days
              timeunits = "sec or min or hours or days" #initializing the string

              if silenceperiod >=  g_KEEP_ALIVE_TIME_OUT:
                 silenceperiod  = silenceperiod/60 # in minutes
                 if silenceperiod <= 59:
                    timeunits = "minutes"
                 else: 
                    silenceperiod = silenceperiod/60 # in hours 
                    if silenceperiod <= 24:
                       timeunits = "hours"
                    else: 
                       silenceperiod = silenceperiod/24 # in days 
                       timeunits = "days"
                    #endif
                 #endif
              g_message_to_user = "There are no movements is  camera for the last " + str(silenceperiod) + " " + timeunits  
              SendMessagesToUsers(bot)

              if g_KEEP_ALIVE_PHOTO_FLAG == False:
                 g_photo_to_user =  g_imageOfLastMovement
                 g_message_to_user ="Photo of Last Movement is not set  as per request"
                 SendMessagesToUsers(bot)
                 SendPhotoToUsers(bot)
              g_previousKeepAliveSendTime = presentTimeinEpoc

###################################################################################################
#  End of Main
###################################################################################################


main()              

