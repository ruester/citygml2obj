import sys, os
from lxml import etree
import StringIO
from osgeo import ogr
import _mysql
import datetime

#-- Global variables
OUTFILE = "footprints_extruded.obj"
INFILE = "footprints_extruded.xml"
SEPSG, TEPSG = 28992,4326

GML = "{%s}" % 'http://www.opengis.net/gml'
CGML = "{%s}" % 'http://www.citygml.org/citygml/1/0/0'

def main(argv):
    convert(INFILE, OUTFILE)

    insertDB(OUTFILE,51.996995388,4.375324684,INFILE,370)

def insertDB(objFilePath,cPointLat,cPointLong,gmlFilePath,nof):
    """ Insert information about uploaded file into mysql db"""

    host = 'localhost'
    user = 'root'
    password = '1234'
    dbname = 'vis3'     
    
    db = _mysql.connect(host,user,password,dbname)

    # get current date
    now = datetime.datetime.now()

    date = str(now.year)+"-"+str(now.month)+"-"+str(now.day)

    db.query("""INSERT INTO bingmodel (obj,cPointLat,cPointLong,gml,nof,date)
VALUES ('"""+str(objFilePath)+"""',"""+str(cPointLat)+""","""+str(cPointLong)+""",'"""+str(gmlFilePath)+"""',"""+str(nof)+""",'"""+date+"""')""")   

def transformPoint(sEPSG, tEPSG, xypoint):
    #source SRS 
    sSRS=ogr.osr.SpatialReference()
    if (sEPSG == 28992):
        sSRS.ImportFromWkt("""
            PROJCS["Amersfoort / RD New",
            GEOGCS["Amersfoort",
                DATUM["Amersfoort",
                    SPHEROID["Bessel 1841",6377397.155,299.1528128,
                        AUTHORITY["EPSG","7004"]],
                    AUTHORITY["EPSG","6289"]],
                PRIMEM["Greenwich",0,
                    AUTHORITY["EPSG","8901"]],
                UNIT["degree",0.01745329251994328,
                    AUTHORITY["EPSG","9122"]],
                TOWGS84[565.237,50.0087,465.658,-0.406857,0.350733,-1.87035,4.0812],
                AUTHORITY["EPSG","4289"]],
            UNIT["metre",1,
                AUTHORITY["EPSG","9001"]],
            PROJECTION["Oblique_Stereographic"],
            PARAMETER["latitude_of_origin",52.15616055555555],
            PARAMETER["central_meridian",5.38763888888889],
            PARAMETER["scale_factor",0.9999079],
            PARAMETER["false_easting",155000],
            PARAMETER["false_northing",463000],
            AUTHORITY["EPSG","28992"]]
        """)
    else:
        sSRS.ImportFromEPSG(sEPSG) 

    #target SRS 
    tSRS=ogr.osr.SpatialReference() 
    tSRS.ImportFromEPSG(tEPSG) 

    poCT=ogr.osr.CoordinateTransformation(sSRS,tSRS) 

    x, y = xypoint
    return poCT.TransformPoint(x,y,0.)
    
def convert(infile, outfile):
    """
    Function that converts simple citygml to .obj
    Input:
        infile
        outfile
    Output:
        - Wavefront .OBJ file
    """

    def xyOffset(plist):
        x = (min(plist[0])+max(plist[0]))/2
        y = (min(plist[1])+max(plist[1]))/2
        return (x,y)

    # parse the infile
    print 'Reading file...'
    tree = etree.parse(infile)
    # for storing vertices:
    vert = StringIO.StringIO()
    # for storing faces:
    fac = StringIO.StringIO()

    pointlist = []
    count = 0
    # loop through the ciyObjectMember elements, for all faces put the points in a set (so that they are not duplicated). Then extend the pointlist with that set. This gives every unique point an index
    for cOM in tree.iter(CGML+"cityObjectMember"):
        count += 1
        s = set([])
        for lR in cOM.iter(GML+"LinearRing"):
            for pos in lR:
                s.update([pos.text])
        pointlist += list(s)
        # with pointlist we can generate the face-lines in the .obj file:
        for lR in cOM.iter(GML+"LinearRing"):
            print >>fac, "f",
            for pos in range(len(lR)-1):
                print >>fac, pointlist.index(lR[pos].text)+1,
            print >>fac

    print 'translating points...'
    # initialize
    pointlistF = []
    for t in range(3):
        pointlistF.append([])

    # convert pointlist to floating points
    for v in pointlist:
        c = v.split()
        pointlistF[0].append(float(c[0]))
        pointlistF[1].append(float(c[1]))
        pointlistF[2].append(float(c[2]))

    # calculate offset
    offset = xyOffset(pointlistF)

    # Generate the vertex-lines in the .obj file. Also translate the points using the OFFSET
    for i in range(len(pointlistF[0])):
        print >>vert, "v %.7f %.7f %.2f" % ( pointlistF[0][i]-offset[0], pointlistF[1][i]-offset[1], pointlistF[2][i] )

    # write the file
    f = open(OUTFILE, 'w')
    lg, lt, h = transformPoint(SEPSG,TEPSG,offset)
    f.write("#Location in WGS84 (lat,long):\n#%.9f,%.9f\n#Number of features:\n#%d\n" % (lt, lg, count))
    f.write(vert.getvalue())
    f.write(fac.getvalue())
    f.close()
    
    print 'Applied offset: %.9f, %.9f' % offset
    print 'EPSG %d location: %.9f, %.9f' % (TEPSG,lt,lg)

if __name__ == "__main__":
    main(sys.argv[1:])
