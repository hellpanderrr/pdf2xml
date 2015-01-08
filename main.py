import os
import re
import pdfminer
import pandas as pd
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox,LTAnno, LTTextLine, LTFigure, LTImage,LTTextLineHorizontal,LTChar,LTLine,LTText,LTTextContainer
import getopt
import argparse
import sys
from collections import Counter
import matplotlib.pyplot as plt
import networkx as nx
from lxml import etree as ET
from HTMLParser import HTMLParser

def find_keys(d,key,area,r=True,l=True):
        key = int(key)
        keys = []
        for j in range(key-area*l,key+area*r):
            if d.has_key(j):
                keys.append(j)
        return keys
def get_chars(line,with_anno=False):
    #get chars from the LTTextline
    ret = []
    if not isiterable(line):
        return [LTChar]
    for char in line:
        if with_anno:
            ret.append(char)
        elif not with_anno and type(char) <> pdfminer.layout.LTAnno:
            ret.append(char)
    return ret
isiterable = lambda obj: isinstance(obj, basestring) or getattr(obj, '__iter__', False)
def get_objects(layout):
    #collecting all objects from the layout, 1 level depth
    objs = []
    for obj in layout:

        if isiterable(obj):
            for element in obj:
                objs.append(element)
        else:
            objs.append(obj)
    return objs
def find_tables(objs):
    regobjs = tableobjs = None
    if objs:
        group = []
        for i in objs:
            n=0
            #if type(i) == pdfminer.layout.LTTextLineHorizontal:
            tmp = []
            for j in objs:
                    if j.hdistance(i) < 10 and j.vdistance(i) < 10 and j <> i and (type(j) == pdfminer.layout.LTRect  or type(j) == pdfminer.layout.LTLine) :
                        n+=1
                        tmp.append(j)
            if n>3:
                group.append(i)
                group+=tmp
        if group:                
            y0 = min(sorted(o, key=lambda x:x.y0, reverse=True), key = lambda x:x.y0).y0        
            y1 = max(sorted(o, key=lambda x:x.y0, reverse=True), key = lambda x:x.y0).y0     
            x0 = min(sorted(o, key=lambda x:x.x0, reverse=True), key = lambda x:x.x0).x0        
            x1 = max(sorted(o, key=lambda x:x.x0, reverse=True), key = lambda x:x.x0).x0 
            print x0,y0,x1,y1
            for i in sorted(objs_r,key=lambda x:x.y0,reverse=True):

                if  x0 <=i.x0 <= x1 and y0 <=i.y0 <= y1:
                    if hasattr(i,'get_text'):
                        pass#print i.get_text(),i
            tableobjs = [i for i in objs if x0 <=i.x0 <= x1 and y0 <=i.y0 <= y1]
            print len(objs),len(tableobjs)
            regobjs = list(set(objs)-set(tableobjs))
        else:
            regobjs=objs
    return regobjs,tableobjs
def gen_xml(objs,n,xml):
    as_list = []
    for i in sorted(sort_by_x(objs)):
        as_list.append(sort_by_x(objs)[int(i)])       
    as_list = sum(as_list,[]) 
    f = []
    for i in as_list:
        size = round(min([j.size for j in get_chars(i)]),2)
        if i.get_text().strip():
           # print '** %s **' %i.get_text(),round(min([j.size for j in get_chars(i)]),2)
            f.append(round(min([j.size for j in get_chars(i)]),2))
    f = list(set(f))
    c = Counter(f)   
    header = xml.find('header')
    body = xml.find('body')   
    for i in as_list:
                size = round(min([j.size for j in get_chars(i)]),2)            
                text = i.get_text()
                if size == max(f) and n==0:
                    header.text += text
                if  c.most_common(1)[0][0] < size < max(f):                  
                    body.text +='<h1>'+text.replace('\n','')+'</h1>'
                elif f[-2] < size < f[-1]:
                    body.text +='<h2>'+text.replace('\n','')+'</h2>'
                else: 
                    body.text += text.replace('\n','') if '\n' in text and text.strip() else text
                    print repr( text.replace('\n','') if '\n' in text and text.strip() else text)
                    
    return xml
def make_xml(objs,objs_r,objs_l,n,xml):
    
    if objs:
        regobjs=find_tables(objs)[0]
        xml = gen_xml(regobjs,n,xml)
    if objs_l:
        regobjs=find_tables(objs_l)[0]
        xml = gen_xml(regobjs,n,xml)
    if objs_r:
        regobjs=find_tables(objs_r)[0]
        xml = gen_xml(regobjs,n,xml)
    return xml
def get_fonts(objs):
    """Returns a set with rounded font sizes"""
    fonts = set()
    for i in objs:
            if hasattr(i,'get_text'): #and  'Italic' in i[0].fontname:
                for j in get_chars(i):
                    fonts.add(round(j.size,2))
    return fonts
def sort_by_x(objs,decimals=-1,has_text=True):
    """Sorts objects by their _x coordinate and stores them accordingly in a dictionary 
    """
    s={}
    for i in sorted(objs,key=lambda x:(x.x0)):
            if has_text and hasattr(i,'get_text'):
                if round(i.x0,decimals) not in s:
                    s[round(i.x0,decimals)] = list()
                s[round(i.x0,decimals)].append(i)
               # if i.x0>450:
                    #print i
            elif not has_text :
                if round(i.x0,decimals) not in s:
                    s[round(i.x0,decimals)] = list()
                s[round(i.x0,decimals)].append(i)
    for i in sorted(s):
        if i:
            adjacent = find_keys(s,i,150,l=False)
            if len(adjacent)>1:
                for j in adjacent[1:]:
                    
                    s[i]+=s[j]
                    s[j]=[]
                s[i]=sorted(s[i],key=lambda x:x.y0,reverse=True)
    for i in s:
        if not i:
            s.remove(i)
    for i in s.items():
            s[i[0]] = sorted(i[1],key=lambda x:x.y1,reverse=True)
    return s

f = 'C:\\Users\\hellpanerrr\\Downloads\\samples-and-notes\\p1.pdf'
#f = 'C:\\Users\\hellpanerrr\\Downloads\\samples-and-notes\\GIM1214_Feature Rajabifard.pdf'#GIM1114_Feature Biljecki.pdf'#'#GIM1114_Feature Biljecki.pdf'
fp = open(f, 'rb')
# Create a PDF parser object associated with the file object.
parser = PDFParser(fp)
# Create a PDF document object that stores the document structure.
document = PDFDocument(parser)
# Check if the document allows text extraction. If not, abort.
if not document.is_extractable:
    raise PDFTextExtractionNotAllowed
# Create a PDF resource manager object that stores shared resources.
rsrcmgr = PDFResourceManager()
# Create a PDF device object.
laparams = LAParams()
# Create a PDF page aggregator object.
device = PDFPageAggregator(rsrcmgr, laparams=laparams)
interpreter = PDFPageInterpreter(rsrcmgr, device)

root = ET.Element('xml')
header = ET.SubElement(root,'header')
title = ET.SubElement(root,'title')
subtitle = ET.SubElement(root,'subtitle')
body = ET.SubElement(root,'body')
body.text=''
header.text =''
title.text=' '
subtitle.text=''
tree = ET.ElementTree(root)
for n,page in enumerate(PDFPage.create_pages(document)):
    #if n <> 0: continue
    objs = []
    objs_r = objs_l =''
    interpreter.process_page(page)
    # receive the LTPage object for the page.
    layout = device.get_result()
    print n,layout.width,layout.height,layout.width/(layout.height*1.0)
    # collecting objects from the all pages, sorting them by their Y coordinate
    objs.append( get_objects(layout))#sorted( get_objects(layout),key=lambda x:x.y0,reverse=True)     )
    objs = objs[0]#sum(objs,[])
    #objs = [i for i in objs if  layout.height*0.05   <= i.y0 <= layout.height-layout.height*0.05 ]
    #determines if page is actually has two pages
    if layout.width/(layout.height*1.0) > 0.8:
        objs_l = [i for i in sorted(objs,key = lambda x:x.x0) if i.x0<= layout.width/2]
        objs_r = [i for i in sorted(objs,key = lambda x:x.x0) if i.x0>  layout.width/2]
        tree = make_xml(objs,objs_r,objs_l,n,tree)
ET.ElementTree(ET.fromstring(HTMLParser().unescape(ET.tostring(tree, encoding='unicode', method='xml')))).write('test.xml',encoding="UTF-8",xml_declaration=True,pretty_print=True)
