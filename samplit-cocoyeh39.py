import sys, random

#Hiiii hw1a +  Hi! HW1b -> resolved

def process_file(filename):
  with open(filename, "r") as file:
    for line in file:
      if random.random() < 0.01:
        print(line, end="")

process_file(sys.argv[1])
