import os
import sys

myPath = os.path.dirname(os.path.abspath(__file__))
myPath = myPath.replace("iron_condor_lumibot_example", "")
myPath = myPath + "/lumibot/"

print (myPath)