import os
import re
import sys
import urllib2
import pdfminer
import math
import itertools as IT
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from collections import Counter
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
from lxml import etree as ET
from HTMLParser import HTMLParser
from scipy.spatial import ConvexHull
from scipy.spatial import Delaunay
from matplotlib.path import Path
from bs4 import BeautifulSoup
ROUND_BY = 1
def main(args):
    input_file = args[1]
    output_file = args[2]
    print args
    fp = open(input_file, 'rb')
    #with open('test.pdf','wb') as s:
    #    s.write(urllib2.urlopen(f).read())
    #fp = open('test.pdf', 'rb')
    filename = os.path.split(input_file)[1].split('.')[0]
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
    laparams.detect_vertical = True
    # Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    root = ET.Element('xml')
    intro = ET.SubElement(root,'intro')
    title = ET.SubElement(root,'title')
    subtitle = ET.SubElement(root,'subtitle')
    body = ET.SubElement(root,'body')
    section = ET.SubElement(root,'section')
    body.text= intro.text = title.text = subtitle.text = section.text = ' '
    tree = ET.ElementTree(root)
    global fonts, layout, images_list, filename
    fonts = Counter([])
    images_list = []
    all_objs = []
    for n,page in enumerate(PDFPage.create_pages(document)):
        #if n <> 0: continue
        print n
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
        all_objs.append(objs)
        fonts += get_fonts(objs)
    for n,objs in enumerate(all_objs):
        #determines if page is actually has two pages
        #if layout.width/(layout.height*1.0) > 0.8:
           # print 'aaa'
        #    objs_l = [i for i in sorted(objs,key = lambda x:x.x0) if i.x0<= layout.width/2]
        #    objs_r = [i for i in sorted(objs,key = lambda x:x.x0) if i.x0>  layout.width/2]
        tree = make_xml(objs,n,tree)
        print 'end'
    soup = BeautifulSoup(HTMLParser().unescape(ET.tostring(tree,encoding='unicode',method='xml')).replace('&','&amp;').replace(' >','&gt;').replace('< ','&lt;'),'xml')
    with open(output_file,'wb') as f:
        f.write(str(soup.prettify().encode('utf-8')))
def median(lst):
    lst = sorted(lst)
   
    if len(lst) < 1:
            return None
    if len(lst) %2 == 1:
            return lst[((len(lst)+1)/2)-1]
    if len(lst) %2 == 0:
            return float(sum(lst[(len(lst)/2)-1:(len(lst)/2)+1]))/2.0
def save_image (lt_image, page_number, images_folder):
    """Try to save the image data from this LTImage object, and return the file name, if successful"""
    result = None
    if lt_image.stream:
        file_stream = lt_image.stream.get_rawdata()
        file_ext = determine_image_type(file_stream[0:4])
        print file_ext
        if file_ext:
            file_name = ''.join([lt_image.name, '_',str(page_number) , file_ext])
            if write_file(images_folder, file_name, lt_image.stream.get_rawdata(), flags='wb'):
                result = file_name
    return result
def determine_image_type (stream_first_4_bytes):
    """Find out the image file type based on the magic number comparison of the first 4 (or 2) bytes"""
    file_type = None
    bytes_as_hex = b2a_hex(stream_first_4_bytes)
    if bytes_as_hex.startswith('ffd8'):
        file_type = '.jpeg'
    elif bytes_as_hex == '89504e47':
        file_type = '.png'
    elif bytes_as_hex == '47494638':
        file_type = '.gif'
    elif bytes_as_hex.startswith('424d'):
        file_type = '.bmp'
    return file_type
from binascii import b2a_hex
def write_file (folder, filename, filedata, flags='w'):
    """Write the file data to the folder and filename combination
    (flags: 'w' for write text, 'wb' for write binary, use 'a' instead of 'w' for append)"""
    result = False
    if os.path.isdir(folder):
        try:
            file_obj = open(os.path.join(folder, filename), flags)
            file_obj.write(filedata)
            file_obj.close()
            result = True
        except IOError:
            pass
    return result
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
        return []
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


def concave(points,alpha_x=150,alpha_y=250):
  points = [(i[0],i[1]) if type(i)<> tuple else i for i in points]
 # print points[:10]  
  de = Delaunay(points)
  dec = []
  b = alpha_x
  a = alpha_y
  for i in de.simplices:
      tmp = []
      j = [points[c] for c in i]
     # print j
      if abs(j[0][1]-j[1][1])>a or abs(j[1][1]-j[2][1])>a or abs(j[0][1]-j[2][1])>a or abs(j[0][0]-j[1][0])>b or abs(j[1][0]-j[2][0])>b or abs(j[0][0]-j[2][0])>b:
          continue
      for c in i:
          tmp.append(points[c])
      dec.append(tmp)
  
  G = nx.Graph()
  for i in dec:
        
        G.add_edge(i[0],i[1])
        G.add_edge(i[0],i[2])
        G.add_edge(i[1],i[2])
  #plt.show()
  ret = []
  for graph in nx.connected_component_subgraphs(G):
        ch = ConvexHull(graph.nodes())
        tmp = []
     #   print sorted(ch.vertices)
        for i in ch.vertices:
            #print i
            tmp.append(graph.nodes()[i])
            #tmp.append(graph.nodes()[i[1]])
 #       print tmp
        ret.append(tmp)
  print len([graph for graph in nx.connected_component_subgraphs(G)])
  return ret,[graph.nodes() for graph in nx.connected_component_subgraphs(G)]
def find_tables(objs,has_text=False,only_items=False):
    #return objs,[]
    regobjs = tableobjs = []
    if objs:
        group = []
        for i in objs:
            n = 0
            if has_text and hasattr(i,'get_text'):
                continue
            tmp = []
            for j in objs:
                    if has_text and hasattr(j,'get_text'):
                        continue
                    #if abs(j.y0-i.y0)<10
                    if (type(j) == pdfminer.layout.LTRect  or type(j) == pdfminer.layout.LTLine) and j.hdistance(i) < 10 and j.vdistance(i) < 10 and j <> i:
                        n+=1
                        tmp.append(j)
            if n > 2:
                group.append(i)
                group+=tmp
        if only_items:
            return group
        if group:
            points = [(i.x0,i.y0) for i in group]
            concave_ = concave(points)[0]
            boundaries = []
            for i in concave_:
                y0 = min(i,key=lambda x:x[1])[1]
                y1 = max(i,key=lambda x:x[1])[1]
                x0 = min(i,key=lambda x:x[0])[0]
                x1 = max(i,key=lambda x:x[0])[0]
                boundaries.append([x0,y0,x1,y1])
            tableobjs = []
            for i in boundaries:
                tableobjs += [j for j in objs if i[0] <= j.x0 <= i[2] and i[1] <=j.y0 <= i[3]]
        regobjs = list(set(objs)-set(tableobjs))
    return regobjs,tableobjs
def gen_xml(objs,g_n,xml):
    import copy
    objs_ = copy.copy(objs)
    objs = sum([i for i in objs.itervalues()],[])
    #print objs
    as_list = []
    for i in sorted(sort_by_x(objs)):
        as_list.append(sort_by_x(objs)[int(i)])       
    as_list = sum(as_list,[]) 
    f = []
    for i in as_list:
        size = round(min([j.size for j in get_chars(i)]),ROUND_BY)
        if i.get_text().strip():
           # print '** %s **' %i.get_text(),round(min([j.size for j in get_chars(i)]),2)
            f.append(size)
  #  print set(f)  
    c = Counter(f)   
    most_used = c.most_common(5)[0][0]
    t = [i for i in sorted(c) if i > most_used]    
    title = xml.find('title')
    body = xml.find('body')  
    subtitle = xml.find('subtitle')
    intro = xml.find('intro') 
    section = xml.find('section')
   # print c.most_common(5)
    if objs_['title']:
        for i in objs_['title']:
                text = i.get_text()
                title.text += text
    if objs_['body']:
        f = []
       
        as_list = []
        for i in sorted(sort_by_x(objs_['body'])):
            as_list.append(sort_by_x(objs_['body'])[int(i)])       
        as_list = sum(as_list,[]) 
        for i in as_list:
            size = round(min([j.size for j in get_chars(i)]),ROUND_BY)
            if i.get_text().strip():
               # print '** %s **' %i.get_text(),round(min([j.size for j in get_chars(i)]),2)
                f.append(size)
        #print as_list
       
        c = fonts# Counter(f)   
       # print c
        most_used = c.most_common(5)[0][0]
        t = [i for i in sorted(c) if i > most_used]
        #print t
        for n,i in enumerate(as_list):
            if n>0:
                if as_list[n-1].y0 - i.y0 > 20:
                    body.text += '\n'
            size = round(median([j.size for j in get_chars(i)]),ROUND_BY)      
            font = get_chars(i)[0].fontname
            text = i.get_text()
            remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
            text = remove_re.sub('', text)
            if text:
               # print repr(text),size,font
            #if t[0] < size < max(f):
          #      body.text +='<h1>' + text.replace('\n','') + '</h1>'
          #      break
                if most_used < size or size < most_used  :         
                    body.text +='<h2>' + text.replace('\n','') + '</h2>'
                    continue

                retain_n = False
                for j in layout:
                    if isiterable(j) and i in j: 
                        if len(j)>1:                               
                            if round(i.y0) == round(j.y0):
                                retain_n = True
                #print repr(text)
                body.text +=  text.replace('\n','') if not retain_n else text
            
            
    if objs_['subtitle']:
        for i in objs_['subtitle']:
            text = i.get_text() if hasattr(i,'get_text')  else ''
            subtitle.text += text
    if objs_['intro']:
        for i in objs_['intro']:
            intro.text += i.get_text() if hasattr(i,'get_text')  else ''
    elif g_n == 0:
        intro.text = body.text.split('\n')[0]
        body.text = '\n'.join(body.text.split('\n')[1:])
    if objs_['section']:
        print ('<page %s>' % (g_n+1))
        section.text += ('<page %s>' % (g_n+1))
        for i in objs_['section']:
            if hasattr(i,'get_text'):
                retain_n = False
                text = i.get_text()
                for j in layout:
                    if isiterable(j) and i in j: 
                        if len(j)>1:                               
                            if round(i.y0) == round(j.y0):
                                retain_n = True
                section.text +=  text.replace('\n',' ') if not retain_n else text
                
        for n,i in enumerate([j for j in objs_['section'] if isinstance(j,pdfminer.layout.LTImage) or isinstance(j,pdfminer.layout.LTFigure)]):
            print 'found image %s, page%s' % (i,n)
            if isiterable(i):
                for j in i:
                    if isinstance(j,pdfminer.layout.LTImage):
                        images_list.append(j)
                        j.name = '%s_%s_%s' % (filename,g_n+1,n)
                        print 'saving %s'%j,save_image(j,g_n,os.path.abspath(''))
                        section.text += '<img src="%s" />' % os.path.join((os.path.abspath(''),save_image(j,g_n,os.path.abspath(''))))
            else:
                images_list.append(i)
                i.name = '%s_%s_%s' % (filename,g_n+1,n)
                print 'saving %s' % i
                section.text += '<img src="%s\\%s" />' % (os.path.abspath(''),save_image(i,g_n,os.path.abspath('')))
        section.text += ('</page %s>' % (g_n+1))
    return xml
def area_of_polygon(x, y):
    """Calculates the signed area of an arbitrary polygon given its verticies
    """
    area = 0.0
    for i in xrange(-1, len(x) - 1):
        area += x[i] * (y[i + 1] - y[i - 1])
    return area / 2.0

def centroid_of_polygon(points):
    area = area_of_polygon(*zip(*points))
    result_x = 0
    result_y = 0
    N = len(points)
    points = IT.cycle(points)
    x1, y1 = next(points)
    for i in range(N):
        x0, y0 = x1, y1
        x1, y1 = next(points)
        cross = (x0 * y1) - (x1 * y0)
        result_x += (x0 + x1) * cross
        result_y += (y0 + y1) * cross
    result_x /= (area * 6.0)
    result_y /= (area * 6.0)
    return (result_x, result_y)
def sort_by_font(objs,n):
    points = []
    ret = []

    objs = [i for i in objs if hasattr(i,'get_text')]
    local_fonts = []
    for obj in objs:
        ls = get_chars(obj)   
        if ls:
            if ls[0] is  pdfminer.layout.LTChar or obj is pdfminer.layout.LTCurve  : 
                continue
            font = round(min( [j.size for j in ls]),ROUND_BY)
            local_fonts.append([font,j.get_text()[:30]])
    fonts_count = fonts#Counter([i[0] for i in fonts])
    for obj in objs:
        ls = get_chars(obj)
        if ls:
            if ls[0] is pdfminer.layout.LTChar or obj is pdfminer.layout.LTCurve  : 
                continue
            for k in ls:
                font = round(min( [j.size for j in get_chars(k)]) if isiterable(k) else k.size ,ROUND_BY)
                if font == fonts_count.most_common(5)[n][0]:
                    points.append([obj.x0,obj.y0])
                    points.append([obj.x0+10,obj.y0])
                    points.append([obj.x0+50,obj.y0])
                    ret.append(obj)
                    break
    return points,ret
def group_by(objs,g_n):
    body = []
    by_font = sort_by_font (find_tables(objs)[0], 0)
    if any(by_font):
        for p in concave( sort_by_font (find_tables(objs)[0], 0 )[0],50,100)[0]:
            path = p
            path.append(path[0])
            path = [[i[0],i[1]] for i in p]
            center = centroid_of_polygon(path)
            for i in path:
                if i[0] > center[0]:
                    i[0] += 10
                else:
                    i[0] -= 10
                if i[1] > center[1]: 
                    i[1] += 10
                else:
                    i[1] -= 10

            ap = Path(path)
            for i in objs:
                #plt.plot(i.x0,i.y0,'ob')
                if ap.contains_point([i.x0,i.y0]):
                   # if hasattr(i,'get_text'):
                        body.append(i)
    
    title = []
    subtitle = []
    intro = []
    section = []
    fonts = []
    n_objs = list(set(objs)-set(body)- set((find_tables(objs)[1])))
    if n_objs:
        for i in n_objs:
            if hasattr(i,'get_text') and i.get_text().strip():
                ls = get_chars(i)
                if ls:
                    font = round(min( [j.size for j in ls]),ROUND_BY)
                    fonts.append(font)
        c = Counter(fonts)
        print c
        if c:
            most_used = c.most_common(5)[0][0]         
            biggest   = max(fonts)
            if c[biggest] ==1:
                for i in n_objs:
                    if get_chars(i):
                        text = i.get_text()
                        font = round(min( [j.size for j in get_chars(i)]),ROUND_BY)
                        if font == biggest and ' ' not in text:
                            fonts.pop(fonts.index(biggest))
                            biggest = sorted(fonts)[-1]
        print '***'
        for n,i in enumerate(sorted(n_objs,key=lambda x:x.y0,reverse=True)):
            
            if hasattr(i,'get_text') and i.get_text().strip():
                
                print repr(i.get_text())
                text = i.get_text()
                if get_chars(i):
                    font = round(min( [j.size for j in get_chars(i)]),ROUND_BY)
                    
                    #print repr(i.get_text()),font
                    if g_n == 0:
                        prev = objs[n-1] 
                        if font == biggest: #and ' ' in text :
                            
                            print 'header %s ' % i
                            title.append(i)
                            continue
                   #     elif font == biggest and not ' ' in text:
                   #         fonts.pop(fonts.index(biggest))
                    #        biggest = sorted(fonts)[-1]
                        elif hasattr(prev,'get_text') and round(min( [j.size for j in get_chars(prev)]),ROUND_BY) == max(fonts) and  '.' not in i.get_text() and g_n == 0:

                                subtitle.append(i)
                                print 'subtitle %s ' % i
                                continue
                        elif g_n == 0:
                            #print repr(i.get_text())
                            intro.append(i)
                            continue
                    section.append(i)
            else: 
                section.append(i)
        print '***'   
    #print sort_by_x(body)
    #print {'body':body,'title':title,'subtitle':subtitle,'intro':intro,'section':section}
    return {'body':body,'title':title,'subtitle':subtitle,'intro':intro,'section':section}
def make_xml(objs,n,xml):
    
    if objs:
        regobjs = find_tables(objs)[0]
        
        xml = gen_xml(group_by(regobjs,n),n,xml)
    #if objs_l:
   #     regobjs = find_tables(objs_l)[0]
       # xml = gen_xml(group_by(regobjs,n),n,xml)
  #  if objs_r:
  #      regobjs = find_tables(objs_r)[0]
       # xml = gen_xml(group_by(regobjs,n),n,xml)
    
    return xml
def get_fonts(objs):
    """Returns a set with rounded font sizes"""
    fonts = []
    
    for i in objs:
            if hasattr(i,'get_text') and i.get_text().strip() and isiterable(i):
                #print i
                fonts.append(round(median( [j.size for j in get_chars(i)]),ROUND_BY) )  #and  'Italic' in i[0].fontname:

    return Counter(fonts)
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
    
    
if __name__ == '__main__':
    main(sys.argv)

