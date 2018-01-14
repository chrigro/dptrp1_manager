#!/usr/bin/env python
# coding=utf-8

import argparse
import sys
import os

parser = argparse.ArgumentParser(description='DPT-RP1 Manager')
parser.add_argument('integers', metavar='N', type=int, nargs='+', help='an integer for the accumulator')
parser.add_argument('--sum', dest='accumulate', action='store_const', const=sum, default=max, help='sum the integers (default: find the max)')

