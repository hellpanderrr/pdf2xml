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
import networkx as nx
from scipy.spatial import Delaunay
from scipy.spatial import ConvexHull
from matplotlib.path import Path
from HTMLParser import HTMLParser
from lxml import etree as ET
from collections import Counter
import itertools as IT

def makexml(path):
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
    def concave(points,alpha_x=150,alpha_y=250):
      points = [(i[0],i[1]) if type(i)<> tuple else i for i in points]
      de = Delaunay(points)
      dec = []
      b = alpha_x
      a = alpha_y
      for i in de.simplices:
          tmp = []
          j = [points[c] for c in i]
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
      ret = []
      for graph in nx.connected_component_subgraphs(G):
            ch = ConvexHull(graph.nodes())
            tmp = []
            for i in ch.vertices:
                tmp.append(graph.nodes()[i])
            ret.append(tmp)
      print len([graph for graph in nx.connected_component_subgraphs(G)])
      return ret,[graph.nodes() for graph in nx.connected_component_subgraphs(G)]

    def get_by_font(objs, n):
        points = []
        objs = []
        objs = [i for i in objs if hasattr(i,'get_text')]
        fonts = []
        for i in objs:
            chars = get_chars(i)
            if chars[0] is  pdfminer.layout.LTChar or chars is pdfminer.layout.LTCurve  :
                continue
            font = round(min( [char.size for char in chars]),2)
            fonts.append(font)
        x = Counter([i for i in f])
        for i in t:
            chars = get_chars(i)
            if j[0] is  pdfminer.layout.LTChar or j is pdfminer.layout.LTCurve  :
                continue
            for k in chars:
                font = round(min( [j.size for j in get_chars(k)]) if isiterable(k) else k.size ,2)
                if font == x.most_common(5)[n][0]:
                    points.append([i.x0,i.y0])
                    points.append([i.x0+10,i.y0])
                    points.append([i.x0+50,i.y0])
                    objs.append(i)
                    break
        return points,objs

    def area_of_polygon(x, y):
        """Calculates the signed area of an arbitrary polygon given its verticies
        http://stackoverflow.com/a/4682656/190597 (Joe Kington)
        http://softsurfer.com/Archive/algorithm_0101/algorithm_0101.htm#2D%20Polygons
        """
        area = 0.0
        for i in xrange(-1, len(x) - 1):
            area += x[i] * (y[i + 1] - y[i - 1])
        return area / 2.0

    def centroid_of_polygon(points):
        """
        http://stackoverflow.com/a/14115494/190597 (mgamba)
        """
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

    def gen_xml(objs,n,xml):
        import copy
        objs_ = copy.copy(objs)
        objs = sum([i for i in objs.itervalues()],[])
        as_list = []
        for i in sorted(sort_by_x(objs)):
            as_list.append(sort_by_x(objs)[int(i)])
        as_list = sum(as_list,[])
        f = []
        for i in as_list:
            size = round(min([j.size for j in get_chars(i)]),2)
            if i.get_text().strip():
                f.append(size)
        c = Counter(f)
        most_used = c.most_common(5)[0][0]
        t = [i for i in sorted(c) if i > most_used]
        title = xml.find('title')
        body = xml.find('body')
        subtitle = xml.find('subtitle')
        intro = xml.find('intro')

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
                size = round(min([j.size for j in get_chars(i)]),2)
                if i.get_text().strip():
                    f.append(size)
            c = Counter(f)
            most_used = c.most_common(5)[0][0]
            t = [i for i in sorted(c) if i > most_used]
            for i in as_list:
                size = round(min([j.size for j in get_chars(i)]),2)
                text = i.get_text()
                if t[0] < size < max(f):
                    body.text +='<h1>' + text.replace('\n','') + '</h1>'
                    break
                if most_used < size < max(f):
                    body.text +='<h2>' + text.replace('\n','') + '</h2>'
                    break
                retain_n = False
                for j in layout:
                    if isiterable(j) and i in j:
                        if len(j)>1:
                            if round(i.y0) == round(j.y0):
                                retain_n = True
                body.text +=  text.replace('\n','') if not retain_n else text
        if objs_['subtitle']:
            for i in objs_['subtitle']:
                subtitle.text += text
        if objs_['intro']:
            for i in objs_['intro']:
                intro.text += text

        return xml

    def group_by(objs,g_n):
        body = []
        for p in concave(gg (find_tables(objs)[0] ,0 )[0],50,100)[0]:
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
                if ap.contains_point([i.x0,i.y0]):
                    if hasattr(i,'get_text'):
                        body.append(i)
        title = []
        subtitle = []
        intro = []
        fonts = []
        n_objs = list(set(objs)-set(body))
        for i in n_objs:
            if hasattr(i,'get_text'):
                ls = get_chars(i)
                font = round(min( [j.size for j in ls]),2)
                fonts.append(font)
        c = Counter(fonts)
        most_used = c.most_common(5)[0][0]
        for n,i in enumerate(sorted(n_objs,key=lambda x:x.y0,reverse=True)):
            if hasattr(i,'get_text'):
                font = round(min( [j.size for j in get_chars(i)]),2)
                if font == max(fonts) and g_n == 0:
                    print 'header %s ' % i
                    title.append(i)
                prev = objs[n-1]
                if hasattr(prev,'get_text'):
                    if round(min( [j.size for j in get_chars(prev)]),2) == max(fonts) and  '.' not in i.get_text() and g_n == 0:
                        subtitle.append(i)
                        print 'subtitle %s ' % i

        return {'body':body,'title':title,'subtitle':subtitle,'intro':intro}
    def make_xml(objs,objs_r,objs_l,n,xml):
        if objs:
            regobjs = find_tables(objs)[0]
            xml = gen_xml(group_by(regobjs,n),n,xml)
        if objs_l:
            regobjs = find_tables(objs_l)[0]
            xml = gen_xml(group_by(regobjs,n),n,xml)
        if objs_r:
            regobjs = find_tables(objs_r)[0]
            xml = gen_xml(group_by(regobjs,n),n,xml)

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
    def find_tables(objs,has_text=False,only=False):
        regobjs = tableobjs = []
        if objs:
            group = []
            for i in objs:
                n=0
                if has_text and hasattr(i,'get_text'):
                    continue
                tmp = []
                for j in objs:
                        if has_text and hasattr(j,'get_text'):
                            continue
                        if j.hdistance(i) < 10 and j.vdistance(i) < 10 and j <> i and (type(j) == pdfminer.layout.LTRect  or type(j) == pdfminer.layout.LTLine) :
                            n+=1
                            tmp.append(j)
                if n>2:
                    group.append(i)
                    group+=tmp
            if only:
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
    f = path
    #f = 'C:\\Users\\hellpanerrr\\Downloads\\samples-and-notes\\GIM1114_Feature Biljecki.pdf'#GIM1214_Feature Rajabifard.pdf'#GIM1114_Feature Biljecki.pdf'
    fp = open(f, 'rb')
    # Create a PDF parser object associated with the file object.
    parser = PDFParser(fp)
    os.remove(f)
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
    for n,page in enumerate(PDFPage.create_pages(document)):
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
        if layout.width/(layout.height*1.0) > 0.8:
            objs_l = [i for i in sorted(objs,key = lambda x:x.x0) if i.x0<= layout.width/2]
            objs_r = [i for i in sorted(objs,key = lambda x:x.x0) if i.x0>  layout.width/2]
        tree = make_xml(objs,objs_r,objs_l,n,tree)
    return HTMLParser().unescape(ET.tostring(tree, encoding='unicode', method='xml'))
