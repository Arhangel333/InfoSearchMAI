import sys
import yaml


v = 1 #verbose output

def myprint(text):
    if(v):
        print(text)

if(len(sys.argv)<=1):
    print("Usage: <programm> <input.yaml> ")
    exit(0)

file = sys.argv[1]

myprint(file)

    
with open(file, "r") as f:
    yam = yaml.safe_load(f)
    myprint(yam)
