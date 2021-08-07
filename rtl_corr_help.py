# this module will be imported in the into your flowgraph
import os
import numpy
import xmlrpclib as xmlrpc
import time
doneffts = False
def st_update(pace,port,files,srate,secs):
    global doneffts
    
    #
    # We've already done this, leave without doing anything
    #
    if (doneffts == True):
        return 1
    
    #
    # Compute how many bytes are required in the capture files
    #
    needed = int(srate * secs * 8.0)
    doit = True
    
    #
    # Check each file to make sure that it is big enough
    #
    for f in files:
        if (os.path.exists(f) != True):
            doit = False
            break
        if (os.path.getsize(f) < needed):
            doit = False
    
    # We go here, time to do cross correlation using
    #   FFT-based fast convolution
    #
    if doit == True and doneffts == False:
        
        #
        # Make up a channel list consisting of buffers from the
        #  capture files
        #
        chans = []
        for f in files:
            chans.append(numpy.fromfile(f,dtype=numpy.csingle,sep=""))
        
        #
        # Pad the data with zeros to improve resolution
        #
        for i in range(len(chans)):
            
            #
            # Truncate to exactly "secs" worth of samples
            #
            chans[i] = chans[i][:int(srate*secs)]
            
            #
            # First channel is special--pad order is different
            #
            if (i == 0):
                chans[i] += numpy.zeros(len(chans[i]),dtype=numpy.csingle)
            else:
                chans[i] = numpy.zeros(len(chans[i]),dtype=numpy.csingle)+chans[i]
        
        #
        # Now we have a list of FFTs to compute on the padded channel data
        #
        ffts = []
        for i in range(len(chans)):
            ffts.append(numpy.fft.fft(chans[i]))
            time.sleep(0.25)
        iffts = []
        
        #
        # Now we need to do  conjugate multiply on each of the
        #  channels against channel 0
        #
        conjugate = numpy.conj(ffts[0])
        for i in range(1,len(chans)):
            conjm = numpy.multiply(conjugate,ffts[i])
            iffts.append(numpy.fft.ifft(conjm))
            time.sleep(0.25)
        
        #
        # Now we extract the location of max correlation
        #
        offsets = [0]
        phases = [0]
        for i in range(len(iffts)):
            magn = numpy.multiply(numpy.absolute(iffts[i]),numpy.absolute(iffts[i]))
            mx = numpy.argmax(magn)
            mc = iffts[i][mx]
            offsets.append(int(mx))
            phases.append(float(numpy.angle(mc)))
            time.sleep(0.125)
        doneffts = True
        try:
            handle =  xmlrpc.ServerProxy("http://localhost:%d" % port, allow_none=True)
        except:
            return 0
        mxd = max(offsets)
        ndx = 0
        #
        # Adjust delays an phases
        #
        for o in offsets:
            offsets[ndx] = mxd - offsets[ndx]
            phases[ndx] *= -1
            ndx += 1
        handle.set_delays(offsets)
        
        #
        # Invert phases
        #
        handle.set_phases(phases)
        print "Delays " + str(offsets)
        print "Phases " + str(phases)
    return (0 if doneffts == 0 else 1)

def log(d,prefix):
    ltp = time.gmtime()
    fn = prefix+"%d%02d%02d.csv" % (ltp.tm_year, ltp.tm_mon, ltp.tm_mday)
    fp = open(fn, "a")
    fp.write("%02d,%02d,%02d," % (ltp.tm_hour, ltp.tm_min, ltp.tm_sec))
    ndx = 0
    for v in d:
        fp.write("%11.9f,%11.9f" % (v.real, v.imag))
        if (ndx < len(d)-1):
            fp.write(",")
        ndx += 1
    fp.write("\n")
        
    print d
