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
def _build_annotations( self, page ):
        for annot in page.annots.resolve():
            if isinstance( annot, PDFObjRef ):
                annot= annot.resolve()
                assert annot['Type'].name == "Annot", repr(annot)
                if annot['Subtype'].name == "Widget":
                    if annot['FT'].name == "Btn":
                        assert annot['T'] not in self.fields
                        self.fields[ annot['T'] ] = annot['V'].name
                    elif annot['FT'].name == "Tx":
                        assert annot['T'] not in self.fields
                        self.fields[ annot['T'] ] = annot['V']
                    elif annot['FT'].name == "Ch":
                        assert annot['T'] not in self.fields
                        self.fields[ annot['T'] ] = annot['V']
                        # Alternative choices in annot['Opt'] )
                    else:
                        raise Exception( "Unknown Widget" )
            else:
                raise Exception( "Unknown Annotation" )
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
            s[i[0]] = sorted(i[1],key=lambda x:x.y0,reverse=True)
    return s
def make_xml(l,q):
    
    for i in l:
            size = round(get_chars(i)[0].size,2)
            text = i.get_text()
            if size > min(fonts):
                q+='<strong>'+text+'</strong>'
            elif size == min(fonts):
                q+= text.replace('\n','')
            elif size == max(fonts):
                q+= '<header>'+text+'</header>'
    return q
def find_tables(objs):
    regobjs = None
    if objs:
        o = []
        for i in objs:
            n=0
            #if type(i) == pdfminer.layout.LTTextLineHorizontal:
            tmp = []
            for j in objs:
                    if j.hdistance(i) < 10 and j.vdistance(i) < 10 and j <> i and (type(j) == pdfminer.layout.LTRect  or type(j) == pdfminer.layout.LTLine) :
                        n+=1
                        tmp.append(j)
                        #print j.width,j.height,type(j)
            if n>3:
                o.append(i)
                o+=tmp
        if o:                
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
    return regobjs
def gen_xml(objs,n):
    q=''
    l=[]
    for i in sorted(sort_by_x(objs)):
        l.append(sort_by_x(objs)[int(i)])       
    l = sum(l,[]) 
    f = []
   # l=sorted(l,key=lambda x:get_chars(x)[0].fontname)
    for i in l:
        f.append(round(get_chars(i)[0].size,2))

    c = Counter(f)   
    print c
    for i in l:
                size = round(pd.Series([j.size for j in get_chars(i)]).mean(),2)
                
                text = i.get_text()
                if  max(f) >size > c.most_common(1)[0][0]:
                  
                    q +='<strong>'+text.replace('\n','')+'</strong>'

                elif size == max(f) and n==0:
                    q += '<header>'+text+'</header>'
                else :
                    
                    q += text.replace('\n','') if '\n' in text and text.strip() else text
    return q
def tt(objs,objs_r,objs_l,n):
    q = ''
    if objs:
        regobjs=find_tables(objs)
        q = gen_xml(regobjs,n)
    if objs_l:
        regobjs=find_tables(objs_l)
        q = gen_xml(regobjs,n)
    if objs_r:
        regobjs=find_tables(objs_r)
        q += gen_xml(regobjs,n)
    return q
f = 'C:\\Users\\hellpanerrr\\Downloads\\samples-and-notes\\p1.pdf'
#f = 'C:\\Users\\hellpanerrr\\Downloads\\samples-and-notes\\GIM1114_Feature Biljecki.pdf'#GIM1214_Feature Rajabifard.pdf'#GIM1114_Feature Biljecki.pdf'
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



q = '<xml>\n'
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
    objs = [i for i in objs if  layout.height*0.05   <= i.y0 <= layout.height-layout.height*0.05 ]
    #determines if page is actually has two pages
    if layout.width/(layout.height*1.0) > 0.8:
        print 'aaa'
        objs_l = [i for i in sorted(objs,key = lambda x:x.x0) if i.x0<= layout.width/2]
        objs_r = [i for i in sorted(objs,key = lambda x:x.x0) if i.x0>  layout.width/2]
        
        
        
    if  'objs_r' not in globals() or not objs_r:
        fonts = get_fonts(objs)
        s = sort_by_x(layout) 
        l = []
        for i in sorted(s):
            l.append(s[i])
        l = sum(l, [])
        
        q+= tt(objs,objs_r,objs_l,n)
    else:
          
        fonts = get_fonts(objs_r)
        print fonts
        s = sort_by_x(layout) 
        l = []
        for i in sorted(s):
            l.append(s[i])
        l = sum(l, [])
        q+= tt(objs,objs_r,objs_l,n)
        
        #q = make_xml(l,q)
        
        

q += '</xml>'    
with open('test.xml','wb') as f:
    f.write(q.encode('utf-8'))
