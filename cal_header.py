#
# Routines for implementing XML descriptions of calibration data.
# 
# History:
#   2015-Mar-29  DG
#     First written (for Solpnt).
#   2015-Mar-30  DG
#     Added FGHz and Poln arrays to Solpnt
#   2015-Mar-31  DG
#     Added DCM_base_attn().  Changed name Solpnt to TPcal, and changed 
#     routine names to end in "...2xml"  Also added cal_types dictionary.
#   2015-Apr-01  DG
#     Forgot to commit changes to database!  Added commit at bottom of
#     send_xml2sql().
#   2015-May-29  DG
#      Converted from using datime() to using Time() based on astropy.
#   2016-Apr-07  DG
#      Added get_size() and write_cal() routines.  Also added some selection
#      keywords (type and t) to send_xml2sql() routine.
#   2016-Apr-09  DG
#      Added read_cal() and read_cal_xml() routines.  Also binary buffer
#      writing routines *2sql() for the various types of calibration data.
#      Changed the total power type to prototype, because I need to break
#      the scheme a little (need to change number of frequencies, ants in
#      the type definition on the fly).  For the "production" TP calibration,
#      a number of things will change, but I cannot know exactly how until
#      I can successfully record the relevant data.
#   2016-05-05  DG
#      Added a fifth cal type for equalizer gains, and routines
#      eq_gain2xml() and eq_gain2sql()
#   2016-05-21  DG
#      Change to dcm_master_table2sql() to allow output from one of the
#      better adc_cal2.py routines (get_dcm_attn()).
#
import struct, util
import numpy as np

def cal_types():
    ''' Routine that defines all of the basic "long-term" calibration
        /information types as a dictionary.  These types and descriptions 
        will be written into the Description field of the aBin table.
        A new type can be added at the end--there is no significance to
        the type number--it is just a unique ordinal.
        
        Although not strictly necessary, in case one of these definitions
        is changed in any way, it is good practice to increment the version
        number, given as the last element of each type.        
    '''
    return {1:['Prototype total power calibration (output of SOLPNTCAL)','proto_tpcal2xml',1.0],
            2:['DCM master base attenuation table [units=dB]','dcm_master_table2xml',1.0],
            3:['DCM base attenuation table [units=dB]','dcm_table2xml',1.0],
            4:['Delay centers [units=ns]','dlacen2xml',1.0],
            5:['Equalizer gains','eq_gain2xml',1.0]}

def str2bin(string):
    ''' Convert the given string to a binary packed byte buffer '''
    return struct.pack(str(len(string)+1)+'s',string+'\n')

def proto_tpcal2xml(nant, nfrq):
    ''' Writes the XML description of the prototype total power calibration binary
        data (SOLPNTCAL result).  Returns a binary representation of the
        text file, for putting into the SQL database.  For the prototype
        data, the format varies due to variable numbers of antennas/frequencies
    '''
    version = cal_types()[1][2]
    
    buf = ''
    buf += str2bin('<Cluster>')
    buf += str2bin('<Name>TPcal</Name>')
    buf += str2bin('<NumElts>5</NumElts>')
    
    # Timestamp (double) [s, in LabVIEW format]
    # Start time of SOLPNT observation on which calibration is based
    buf += str2bin('<DBL>')
    buf += str2bin('<Name>Timestamp</Name>')
    buf += str2bin('<Val></Val>')
    buf += str2bin('</DBL>')
    
    # Version of this XML file.  This number should be incremented each
    # time there is a change to the structure of this file.
    buf += str2bin('<DBL>')
    buf += str2bin('<Name>Version</Name>')
    buf += str2bin('<Val>'+str(version)+'</Val>')
    buf += str2bin('</DBL>')

    # Array of frequencies in GHz (nfrq)
    buf += str2bin('<Array>')
    buf += str2bin('<Name>FGHz</Name>')
    buf += str2bin('<Dimsize>'+str(nfrq)+'</Dimsize>\n<SGL>\n<Name></Name>\n<Val></Val>\n</SGL>')
    buf += str2bin('</Array>')

    # Array of Poln (2)
    # Polarization list (Miriad definition) (signed int)
    #     1: Stokes I
    #     2: Stokes Q
    #     3: Stokes U
    #     4: Stokes V
    #    -1: Circular RR
    #    -2: Circular LL
    #    -3: Circular RL
    #    -4: Circular LR
    #    -5: Linear XX
    #    -6: Linear YY
    #    -7: Linear XY
    #    -8: Linear YX
    #     0: Not used
    buf += str2bin('<Array>')
    buf += str2bin('<Name>Poln</Name>')
    buf += str2bin('<Dimsize>2</Dimsize>\n<I32>\n<Name></Name>\n<Val></Val>\n</I32>')
    buf += str2bin('</Array>')

    # Array of clusters for each antenna (nant)
    buf += str2bin('<Array>')
    buf += str2bin('<Name>Antenna</Name>')
    buf += str2bin('<Dimsize>'+str(nant)+'</Dimsize>')

    # Cluster containing information for one antenna
    buf += str2bin('<Cluster>')
    buf += str2bin('<Name></Name>')
    buf += str2bin('<NumElts>3</NumElts>')

    # Antenna number (1-13).
    buf += str2bin('<U16>')
    buf += str2bin('<Name>Antnum</Name>')
    buf += str2bin('<Val></Val>')
    buf += str2bin('</U16>')

    # Calibration factors (nfrq x 2) = nfreq x npol
    buf += str2bin('<Array>')
    buf += str2bin('<Name>Calfac</Name>')
    buf += str2bin('<Dimsize>'+str(nfrq)+'</Dimsize><Dimsize>2</Dimsize>\n<SGL>\n<Name></Name>\n<Val></Val>\n</SGL>')
    buf += str2bin('</Array>')

    # Offsun values (448 x 2) = nfreq x npol
    buf += str2bin('<Array>')
    buf += str2bin('<Name>Offsun</Name>')
    buf += str2bin('<Dimsize>'+str(nfrq)+'</Dimsize><Dimsize>2</Dimsize>\n<SGL>\n<Name></Name>\n<Val></Val>\n</SGL>')
    buf += str2bin('</Array>')

    # End cluster
    buf += str2bin('</Cluster>')   # End Calinfo cluster
    buf += str2bin('</Array>')     # End Antenna array
    buf += str2bin('</Cluster>')   # End TPcal cluster

    return buf

def dcm_master_table2xml():
    ''' Writes the XML description of the DCM master base attenuation 
        table (created by pcapture.py).  Returns a binary representation 
        of the text file, for putting into the SQL database.  The version 
        number must be incremented each time there is a change to the 
        structure of this header.
    '''
    version = cal_types()[2][2]
    
    buf = ''
    buf += str2bin('<Cluster>')
    buf += str2bin('<Name>DCMMasterBaseAttn</Name>')
    buf += str2bin('<NumElts>4</NumElts>')
    
    # Timestamp (double) [s, in LabVIEW format]
    # Time of creation of the table (close to packet capture time)
    buf += str2bin('<DBL>')
    buf += str2bin('<Name>Timestamp</Name>')
    buf += str2bin('<Val></Val>')
    buf += str2bin('</DBL>')
    
    # Version of this XML file.  This number should be incremented each
    # time there is a change to the structure of this file.
    buf += str2bin('<DBL>')
    buf += str2bin('<Name>Version</Name>')
    buf += str2bin('<Val>'+str(version)+'</Val>')
    buf += str2bin('</DBL>')

    # List of bands (34), with band number (1-34) if used, 0 if not.
    buf += str2bin('<Array>')
    buf += str2bin('<Name>Bands</Name>')
    buf += str2bin('<Dimsize>34</Dimsize>\n<U16>\n<Name></Name>\n<Val></Val>\n</U16>')
    buf += str2bin('</Array>')

    # Array of base attenuations [dB] (34 x 30).  Attenuations for unmeasured
    # antennas and/or bands are set to nominal value of 10 dB.  Values are
    # ordered as Ant1x, Ant1y, Ant2x, Ant2y, ..., Ant15x, Ant15y
    buf += str2bin('<Array>')
    buf += str2bin('<Name>Attenuation</Name>')
    buf += str2bin('<Dimsize>30</Dimsize><Dimsize>34</Dimsize>\n<U16>\n<Name></Name>\n<Val></Val>\n</U16>')
    buf += str2bin('</Array>')

    # End cluster
    buf += str2bin('</Cluster>')   # End DCMMasterBaseAttn cluster

    return buf

def dcm_table2xml():
    ''' Writes the XML description of the DCM base attenuation table 
        (derived from the DCM master base attenuation table and the
        current frequency sequence.  Returns a binary representation of the
        text file, for putting into the SQL database.  The version number
        must be incremented each time there is a change to the structure 
        of this header.
    '''
    version = cal_types()[3][2]
    
    buf = ''
    buf += str2bin('<Cluster>')
    buf += str2bin('<Name>DCMBaseAttn</Name>')
    buf += str2bin('<NumElts>3</NumElts>')
    
    # Timestamp (double) [s, in LabVIEW format]
    # Time of creation of the table (close to packet capture time)
    buf += str2bin('<DBL>')
    buf += str2bin('<Name>Timestamp</Name>')
    buf += str2bin('<Val></Val>')
    buf += str2bin('</DBL>')
    
    # Version of this XML file.  This number should be incremented each
    # time there is a change to the structure of this file.
    buf += str2bin('<DBL>')
    buf += str2bin('<Name>Version</Name>')
    buf += str2bin('<Val>'+str(version)+'</Val>')
    buf += str2bin('</DBL>')

    # Array of base attenuations [dB] (50 x 30).  Attenuations for unmeasured
    # antennas and/or bands are set to nominal value of 10 dB.  Values are
    # ordered as Ant1x, Ant1y, Ant2x, Ant2y, ..., Ant15x, Ant15y
    buf += str2bin('<Array>')
    buf += str2bin('<Name>Attenuation</Name>')
    buf += str2bin('<Dimsize>30</Dimsize><Dimsize>50</Dimsize>\n<U16>\n<Name></Name>\n<Val></Val>\n</U16>')
    buf += str2bin('</Array>')

    # End cluster
    buf += str2bin('</Cluster>')   # End DCMBaseAttn cluster

    return buf

def dlacen2xml():
    ''' Writes the XML description of the Delay Centers table (currently
        created by hand).  Returns a binary representation of the xml
        text file, for putting into the SQL database.  The version number
        must be incremented each time there is a change to the structure 
        of this header.
    '''
    version = cal_types()[4][2]
    
    buf = ''
    buf += str2bin('<Cluster>')
    buf += str2bin('<Name>Delaycenters</Name>')
    buf += str2bin('<NumElts>3</NumElts>')
    
    # Timestamp (double) [s, in LabVIEW format]
    # Time of creation of the table (precise time not critical)
    buf += str2bin('<DBL>')
    buf += str2bin('<Name>Timestamp</Name>')
    buf += str2bin('<Val></Val>')
    buf += str2bin('</DBL>')
    
    # Version of this XML file.  This number should be incremented each
    # time there is a change to the structure of this file.
    buf += str2bin('<DBL>')
    buf += str2bin('<Name>Version</Name>')
    buf += str2bin('<Val>'+str(version)+'</Val>')
    buf += str2bin('</DBL>')

    # List of delay centers [ns] (2 x 16).
    buf += str2bin('<Array>')
    buf += str2bin('<Name>Delaycen_ns</Name>')
    buf += str2bin('<Dimsize>2</Dimsize><Dimsize>16</Dimsize>\n<SGL>\n<Name></Name>\n<Val></Val>\n</SGL>')
    buf += str2bin('</Array>')

    # End cluster
    buf += str2bin('</Cluster>')   # End Delaycenters cluster

    return buf

def eq_gain2xml():
    ''' Writes the XML description of the equalizer gain table.  Returns 
        a binary representation of the xml, for putting into the SQL 
        database.  The version number must be incremented each time there 
        is a change to the structure of this header.
    '''
    version = cal_types()[5][2]
    
    buf = ''
    buf += str2bin('<Cluster>')
    buf += str2bin('<Name>EQ_Gain</Name>')
    buf += str2bin('<NumElts>3</NumElts>')
    
    # Timestamp (double) [s, in LabVIEW format]
    # Time of creation of the table (precise time not critical)
    buf += str2bin('<DBL>')
    buf += str2bin('<Name>Timestamp</Name>')
    buf += str2bin('<Val></Val>')
    buf += str2bin('</DBL>')
    
    # Version of this XML file.  This number should be incremented each
    # time there is a change to the structure of this file.
    buf += str2bin('<DBL>')
    buf += str2bin('<Name>Version</Name>')
    buf += str2bin('<Val>'+str(version)+'</Val>')
    buf += str2bin('</DBL>')

    # List of equalizer gains (nant x npol x nband) (2 x 2 x 34).  This
    # can be extended to handle 128 subbands/band, if needed.  Note inverted
    # order of dimensions
    buf += str2bin('<Array>')
    buf += str2bin('<Name>EQ_Coeff</Name>')
    buf += str2bin('<Dimsize>34</Dimsize><Dimsize>2</Dimsize><Dimsize>2</Dimsize>\n<SGL>\n<Name></Name>\n<Val></Val>\n</SGL>')
    buf += str2bin('</Array>')

    # End cluster
    buf += str2bin('</Cluster>')   # End EQ_Gain cluster

    return buf

def send_xml2sql(type=None,t=None,test=False,nant=None,nfrq=None):
    ''' Routine to send any changed calibration xml definitions to the 
        SQL Server.  The latest definition (if any) for a given type is
        checked to see if the version matches.  If not, an update is 
        stored.  This routine will typically be run whenever a definition
        is added or changed.  If type is provided (i.e. not None), only 
        the given type will be updated (and only if its internal version 
        number has changed).
        
        The timestamp of the new record will be set according to the Time()
        object t, if provided, or the current time if not.
        
        As a debugging tool, if test is True, this routine goes through the
        motions but does not write to the abin table.
    '''
    import dbutil, read_xml2, sys
    if t is None:
        t = util.Time.now()
    timestamp = int(t.lv)  # Current time as LabVIEW timestamp
    cursor = dbutil.get_cursor()
    typdict = cal_types()
    if type:
        # If a particular type is specified, limit the action to that type
        typdict = {type:typdict[type]}
    for key in typdict.keys():
        #print 'Working on',typdict[key][0]
        # Execute the code to create the xml description for this key
        if key == 1:
            # Special case for TP calibration
            if nant is None or nfrq is None:
                print 'For',typdict[key][0],'values for both nant and nfrq are required.'
                cursor.close()
                return
            exec 'buf = '+typdict[key][1]+'(nant='+str(nant)+',nfrq='+str(nfrq)+')'
        else:
            exec 'buf = '+typdict[key][1]+'()'
        # Resulting buf must be written to a temporary file and reread
        # by xml_ptrs()
        f = open('/tmp/tmp.xml','wb')
        f.write(buf)
        f.close()
        mydict, xmlver = read_xml2.xml_ptrs('/tmp/tmp.xml')
        defn_version = float(key)+xmlver/10.  # Version number expected
        # Retrieve most recent key.0 record and check its version against the expected one
        query = 'select top 1 * from abin where Version = '+str(key)+'.0 and Timestamp <= '+str(timestamp)+' order by Timestamp desc'
        #print 'Executing query'
        outdict, msg = dbutil.do_query(cursor,query)
        #print msg
        if msg == 'Success':
            if len(outdict) == 0:
                # This type of xml file does not yet exist in the database, so mark it for adding
                add = True
            else:
                # There is one, so see if they differ
                buf2 = outdict['Bin'][0]   # Binary representation of xml file
                if buf == buf2:
                    # This description is already there so we will skip it
                    add = False
                else:
                    add = True
        else:
            # Some kind of error occurred, so print the message and skip adding the xml description
            #print 'Query',query,'resulted in error message:',msg
            add = False
        if add:
            # This is either new or updated, so add the xml description
            # to the database
            #print 'Trying to add',typdict[key][0]
            try:
                if test:
                    print 'Would have updated',typdict[key][0],'to version',defn_version
                else:
                    cursor.execute('insert into aBin (Timestamp,Version,Description,Bin) values (?,?,?,?)',
                   timestamp, key, typdict[key][0], dbutil.stateframedef.pyodbc.Binary(buf))
                    print 'Type definition for',typdict[key][0],'successfully added/updated to version',defn_version,'--OK'
                    cursor.commit()
            except:
                print 'Unknown error occurred in adding',typdict[key][0]
                print sys.exc_info()[1]
        else:
            print 'Type definition for',typdict[key][0],'version',defn_version,'exists--OK'
    cursor.close()

def read_cal_xml(type,t=None):
    ''' Read the calibration type definition xml record of the given type, for the 
        given time (as a Time() object), or for the current time if None.
        
        Returns a dictionary of look-up information and its internal version.  A side-effect
        is that a file /tmp/type<n>.xml is created, where <n> is the type.
    '''
    import dbutil, read_xml2, sys
    if t is None:
        t = util.Time.now()
    timestamp = int(t.lv)  # Given (or current) time as LabVIEW timestamp
    typdict = cal_types()
    try:
        typinfo = typdict[type]
    except:
        print 'Type',type,'not found in type definition dictionary.'
        return {}, None
    cursor = dbutil.get_cursor()
    # Read type definition XML from abin table
    query = 'select top 1 * from abin where Version = '+str(type)+'.0 and Timestamp <='+str(timestamp)+' order by Timestamp desc'
    sqldict, msg = dbutil.do_query(cursor,query)
    if msg == 'Success':
        if len(sqldict) == 0:
            # This type of xml file does not yet exist in the database, so mark it for adding
            print 'Type',type,'not defined in abin table.'
            cursor.close()
            return {}, None
        else:
            # There is one, so read it and the corresponding binary data
            buf = sqldict['Bin'][0]   # Binary representation of xml file
            xmlfile = '/tmp/type'+str(type)+'.xml'
            f = open(xmlfile,'wb')
            f.write(buf)
            f.close()
            xmldict, thisver = read_xml2.xml_ptrs(xmlfile)
            cursor.close()
            return xmldict, thisver

def read_cal(type,t=None):
    ''' Read the calibration data of the given type, for the given time (as a Time() object),
        or for the current time if None.
        
        Returns a dictionary of look-up information and a binary buffer containing the 
        calibration record.
    '''
    import dbutil, read_xml2, sys
    if t is None:
        t = util.Time.now()
    timestamp = int(t.lv)  # Given (or current) time as LabVIEW timestamp
    xmldict, ver = read_cal_xml(type, t)
    cursor = dbutil.get_cursor()

    if xmldict != {}:
        query = 'set textsize 2147483647 select top 1 * from abin where Version = '+str(type+ver/10.)+' and Timestamp <= '+str(timestamp)+' order by Timestamp desc'
        sqldict, msg = dbutil.do_query(cursor,query)
        cursor.close()
        if msg == 'Success':
            if sqldict == {}:
                print 'Error: Query returned no records.'
                print query
                return {}, None
            buf = sqldict['Bin'][0]   # Binary representation of data
            return xmldict, str(buf)
        else:
            print 'Unknown error occurred reading',typdict[type][0]
            print sys.exc_info()[1]
            return {}, None
    else:
        return {}, None
                
def get_size(fmt):
    # Complicated, but clever routine to determine the size of my
    # non-Pythonic format string, in which arrays are indicated by
    # a number followed by a fmt substring in square [] brackets.
    # An example is:
    #   fmt = 'ddI448fI2iI13[II896fII896f]'
    # which means 'ddI448fI2iI' followed by 13 'II896fII896f'
    fs = fmt.split('[')
    flist = [fs[0]]
    if len(fs) != 1:
        # There was an open [, so find numbers at end of first element
        for f in fs[1:]:
            flist.append(f.split(']'))
    outlist = []
    out = flist[0]
    for f in flist:
        if type(f) != str:
            chk = f[1]
            outlist.append(val*f[0])
        else:
            chk = f
        for idx in range(1,len(chk)+1):
            try:
                val2 = int(chk[-idx:])
                out = chk[:-idx]
                val = val2
            except:
                outlist.append(out)
                break
    outfmt = ''.join(outlist)
    return struct.calcsize('>'+outfmt)
        
def write_cal(type,buf,t=None):
    ''' Write the calibration data provided in data buffer buf of the given type, 
        for the given time (as a Time() object), or for the current time if None.
        Typcially, the time should refer to when the calibration data were taken,
        so the correct time object should be provided.
        
        The type keyword is a real number whose integer part indicates the type
        definition.  The fractional part must not be 0 (since this would indicate
        a type definition record rather than a data record).  The relevant type 
        definition is read from the database, and its total size is determined and 
        compared with the buffer size, as a sanity check.
        
        Returns True if success, or False if failure.
    '''
    import dbutil, read_xml2, sys
    if t is None:
        t = util.Time.now()
    timestamp = int(t.lv)  # Given (or current) time as LabVIEW timestamp
    typdict = cal_types()
    try:
        typinfo = typdict[int(type)]
    except:
        print 'Type',int(type),'not found in type definition dictionary.'
        return False
    cursor = dbutil.get_cursor()
    # Read type definition XML from abin table and do a sanity check
    query = 'select top 1 * from abin where Version = '+str(int(type))+'.0 and Timestamp <='+str(timestamp)+' order by Timestamp desc'
    outdict, msg = dbutil.do_query(cursor,query)
    if msg == 'Success':
        if len(outdict) == 0:
            # This type of xml file does not yet exist in the database, so indicate an error
            print 'Error: Type',type,'not defined in abin table.'
            cursor.close()
            return False
        else:
            # There is one, so read it and do a sanity check against binary data
            f = open('/tmp/tmp.xml','wb')
            f.write(outdict['Bin'][0])
            f.close()
            keys, mydict, fmt, ver = read_xml2.xml_read('/tmp/tmp.xml')
            binsize = get_size(fmt)
            if len(buf) == binsize:
                cursor.execute('insert into aBin (Timestamp,Version,Description,Bin) values (?,?,?,?)',
                   timestamp, type+ver/10., typinfo[0], dbutil.stateframedef.pyodbc.Binary(buf))
                cursor.commit()
                cursor.close()
                return True
            else:
                print 'Error: Size of buffer',len(buf),'does not match this calibration type.  Expecting',binsize
                cursor.close()
                return False
                
def proto_tpcal2sql(filename,t=None):
    ''' Writes prototype TP calibration data as a record into SQL server table abin
    
        This kind of record is type definition 1.
    '''
    typedef = 1
    ver = cal_types()[typedef][2]
    if t is None:
        t = util.Time.now()
    try:
        # Open and read TP calibration file
        npol,nfrq,nant = filename.replace('.dat','').split('_')[1:]
        nant = int(nant)
        nsiz = int(npol)*int(nfrq)*nant
        nfi = int(nfrq)
        f = open(filename,'rb')
        data = f.read()
        f.close()
        fghz = np.array(struct.unpack_from(nfrq+'f',data,0))
        calfac = np.array(struct.unpack_from(str(nsiz)+'f',
                                    data,nfi*4)).reshape(int(npol),int(nfi),nant)
        offsun = np.array(struct.unpack_from(str(nsiz)+'f',
                                    data,(nfi+nsiz)*4)).reshape(int(npol),int(nfi),nant)
    except:
        print 'Error: Could not open/read file',filename
        return False
    # For TP calibration, must explicitly write xml for this nant and nfrq, since
    # the definition changes if nant and nfrq change
    send_xml2sql(typedef,t,nant=nant,nfrq=nfi)
    # Write timestamp 
    buf = struct.pack('d',int(t.lv))
    # Write version number
    buf += struct.pack('d',ver)
    buf += struct.pack('I',nfi) # Length of frequency array
    buf += struct.pack(nfrq+'f',*fghz)
    buf += struct.pack('I',2) # Length of frequency array
    buf += struct.pack('2i',*np.array([-5,-6]))  # Polarizations XX and YY
    buf += struct.pack('I',nant) # Length of antenna array
    for i in range(nant):
        # Antenna number
        buf += struct.pack('H',i+1)
        # Calibration factors
        buf += struct.pack('I',nfi) # Number of frequencies
        buf += struct.pack('I',2)   # Number of polarizations
        buf += struct.pack(str(nfi*2)+'f',*(calfac[:,:,i].reshape(nfi*2)))
        # Offsun level
        buf += struct.pack('I',nfi) # Number of frequencies
        buf += struct.pack('I',2)   # Number of polarizations
        buf += struct.pack(str(nfi*2)+'f',*(offsun[:,:,i].reshape(nfi*2)))
    return write_cal(typedef,buf,t)
    
def dcm_master_table2sql(filename,tbl=None,t=None):
    ''' Writes a DCM master base attenuation calibration table as a record into 
        SQL server table abin. filename can either be a txt file (DCM_master_table.txt) 
        or a DCM_list (from the output of adc_cal2.make_DCM_table()) or a table from
        the output of adc_cal2.set_dcm_attn() [use filename='' and give the table as tbl].

        This kind of record is type definition 2.
    '''
    typedef = 2
    ver = cal_types()[typedef][2]
    if t is None:
        t = util.Time.now()
    if tbl is None:
        # Check the format of the input file and see if it is a file or a python list    
        try:
            # Open and read DCM_master_table.txt file
            if type(filename) is str: 
                f = open(filename,'r')
                lines = f.readlines()
                f.close()
            if type(filename) is list:
                lines = filename
            # Read file of attenuations (34 non-comment lines with band + 30 attns)
            bands = np.zeros(34,'int')
            attn = np.zeros((34,30),'float')
            for line in lines:
                if line[0] != '#':
                    band,rline = line.strip().split(':')
                    attn[int(band)-1] = map(int,rline.split())
                    bands[int(band)-1] = band
        except:
                print 'Error: Could not open/read file',filename
                return False
    else:
        # Standard table was input, so interpret as output from adc_cal.set_dcm_attn()
        bands = np.linspace(1,34,34).astype(int)
        attn = tbl[:,:30]
        
    # Write timestamp 
    buf = struct.pack('d',int(t.lv))
    # Write version number
    buf += struct.pack('d',ver)
    buf += struct.pack('I',34)
    buf += struct.pack('34H',*bands)
    buf += struct.pack('I',34)
    buf += struct.pack('I',30)
    for i in range(34):
        buf += struct.pack('30H',*attn[i])
    return write_cal(typedef,buf,t)

def dcm_table2sql(filename,t=None):
    ''' Writes an instance of DCM table attenuation calibration for the 
        current scan as a record into SQL server table abin. filename can 
        either be a txt file (DCM_table.txt) or a list

        This kind of record is type definition 3.
    '''
    typedef = 3
    ver = cal_types()[typedef][2]
    if t is None:
        t = util.Time.now()
    try:
        if type(filename) is str: 
            # Open and read DCM_table.txt file
            f = open(filename,'r')
            lines = f.readlines()
            f.close()
        if type(filename) is list:
            lines = filename
        # Read file of attenuations (50 non-comment lines with ant + 30 attns)
        attn = np.zeros((50,30),'float')
        for i,line in enumerate(lines):
            attn[i] = map(int,line.split())
    except:
        print 'Error: Could not open/read file',filename
        return False
    # Write timestamp 
    buf = struct.pack('d',int(t.lv))
    # Write version number
    buf += struct.pack('d',ver)
    buf += struct.pack('I',50)
    buf += struct.pack('I',30)
    for i in range(50):
        buf += struct.pack('30H',*attn[i])
    return write_cal(typedef,buf,t)

def dla_cen2sql(filename='/tmp/delay_centers_tmp.txt', t=None):
    ''' Write delays given in file filename to SQL server table abin
        with the timestamp given by Time() object t (or current time, if none)
        
        This kind of record is type definition 4.
    '''
    typedef = 4
    ver = cal_types()[typedef][2]
    if t is None:
        t = util.Time.now()
    try:
        # Open and read file of delay_center values
        f = open(filename,'r')
        lines = f.readlines()
        f.close()
        # Read file of delays (16 non-comment lines with ant, dlax, dlay)
        tau_ns = np.zeros((16,2),'float')
        for line in lines:
            if line[0] != '#':
                ant,xdla,ydla = line.strip().split()
                tau_ns[int(ant)-1] = np.array([float(xdla),float(ydla)])
    except:
        print 'Error: Could not open/read file',filename
        return False

    # Write timestamp 
    buf = struct.pack('d',int(t.lv))
    # Write version number
    buf += struct.pack('d',ver)
    buf += struct.pack('I',2)
    buf += struct.pack('I',16)
    for i in range(16):
        buf += struct.pack('2f',*tau_ns[i])
    return write_cal(typedef,buf,t)

def eq_gain2sql(coeff, ver=1.0, t=None):
    ''' Write coefficients to SQL server table abin, with the timestamp 
        given by Time() object t (or current time, if none)
        
        This kind of record is type definition 5.  This data type
        can have many "versions," i.e. tables, for different source
        types.  In particular, we will have one for calibrators and
        one for the Sun.  
           Version 1.0 => calibrator/blank sky
           Version 2.0 => Sun
    '''
    typedef = 5
    if t is None:
        t = util.Time.now()

    # Write timestamp 
    buf = struct.pack('d',int(t.lv))
    # Write version number
    buf += struct.pack('d',ver)
    buf += struct.pack('I',34)
    buf += struct.pack('I',2)
    buf += struct.pack('I',2)
    for i in range(2):
        for j in range(2):
            buf += struct.pack('34f',*coeff[i,j])
    return write_cal(typedef,buf,t)
