import time
import os

def main():
  while True:
    print(os.environ['LOCATION'])
    time.sleep(5)
  
main()