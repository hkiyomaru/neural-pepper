#!/usr/bin/env python
import rospy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from microsofttranslator import Translator
from cv_bridge import CvBridge, CvBridgeError
import cv2
import sys
import os
import re
import string
import time
from datetime import *
import commands
import base64
import urllib2
import json
import wave

tts_url ='http://rospeex.ucri.jgn-x.jp/nauth_json/jsServices/VoiceTraSS'

def speakCaption():
    filename = str(datetime.now()) + ".png"
    os.rename("./pepper_picture/now.png", "./pepper_picture/" + filename)

    print "Creating caption..."
    script = 'curl -F "file=@./pepper_picture/' + filename + '" localhost:8000'
    result = commands.getoutput(script).split("\n")[3]
    print result
    
    print "Translating..."
    translator = Translator('Your client ID', 'Your client secret') #change this line
    result = translator.translate(result, "ja")
    print result
    
    print "Creating wav.file with Rospeex and preparing speech..."
    tts_command = { "method":"speak",
                    "params":["1.1",
                    {"language":"ja","text":result,"voiceType":"*","audioType":"audio/x-wav"}]}
    
    obj_command = json.dumps(tts_command) # string to json object
    req = urllib2.Request(tts_url, obj_command)
    received = urllib2.urlopen(req).read() # get data from server
    
    obj_received = json.loads(received)
    tmp = obj_received['result']['audio'] # extract result->audio
    speech = base64.decodestring(tmp.encode('utf-8'))
    
    f = open ("./result_voice/out.wav",'wb')
    f.write(speech)
    f.close
    
    commands.getoutput('aplay ./result_voice/out.wav')

class GetPicture(object):
    #Initializing
    def __init__(self):
        self._pic_sub = rospy.Subscriber('/pepper_robot/camera/front/image_raw', Image, self.callback, queue_size=10)
        cv2.namedWindow("Pepper Picture", 60)
        self.bridge = CvBridge()

    #Callback function
    def callback(self, data):
        #Get pepper picture
        try:
            cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
            commands.getoutput('aplay ./speech_sets/caution.wav')
            rospy.sleep(5)
            print(e)

        #Display picture
        cv2.imshow("Pepper Picture", cv_image)

        #Save picture
        cv2.imwrite("./pepper_picture/now.png", cv_image)

        cv2.waitKey(3)

class JoyTwist(object):
    def __init__(self):
        self._joy_sub = rospy.Subscriber('/joy', Joy, self.joy_callback, queue_size=1)
        self._twist_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        self.rflag = 0
        self.lflag = 0


    def joy_callback(self, joy_msg):
        twist = Twist()
        if joy_msg.buttons[3] == 1:
            speakCaption()
        twist.linear.x = (joy_msg.axes[1] + joy_msg.axes[5]) * 0.08
        twist.angular.z = (joy_msg.axes[0] + joy_msg.axes[4]) * 0.3
        if twist.angular.z < 0 and self.rflag == 0:
            commands.getoutput('aplay ./speech_sets/turn_right.wav')
            self.rflag = 1
            self.lflag = 0
        elif twist.angular.z > 0 and self.lflag == 0:
            commands.getoutput('aplay ./speech_sets/turn_left.wav')
            self.lflag = 1
            self.rflag = 0
        self._twist_pub.publish(twist)

def main():
    rospy.init_node('node_runner')
    joy_twist = JoyTwist()
    get_picture = GetPicture()
    rospy.spin()

if __name__ == "__main__":
    sys.exit(main())
