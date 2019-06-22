# ofdm_rx class 
# Last modification by initentity generator 
#Simple buffer template

import os
import sys
import numpy as np
import tempfile

from thesdk import *
from verilog import *

from channel_equalizer import *
from f2_symbol_sync import *
from ofdm_demodulator import *

class ofdm_rx(verilog,thesdk):
    #Classfile is required by verilog and vhdl classes to determine paths.
    @property
    def _classfile(self):
        return os.path.dirname(os.path.realpath(__file__)) + "/"+__name__

    def __init__(self,*arg): 
        self.proplist = [ 'Rs' ];    # Properties that can be propagated from parent
        self.Rs =  100e6;            # Sampling frequency
        self.iptr_A = IO();          # Pointer for input data
        _=verilog_iofile(self,name='A',dir='in')
        self.io_iqSamples = IO();    # Pointer for input data

        self._Z=IO()
        _=verilog_iofile(self,name='Z',datatype='complex' dir='out')
        self.control_write = IO();   # Pointer for control inputs created by controller
        
        self._control_read = IO()
        _=verilog_iofile(self,name='control_read',datatype='complex', dir='in')
        self.model='py';             # Can be set externally, but is not propagated
        self.par= False              # By default, no parallel processing
        self.queue= []               # By default, no parallel processing
        self._Z = IO();              # Pointer for output data
        if len(arg)>=1:
            parent=arg[0]
            self.copy_propval(parent,self.proplist)
            self.parent =parent;
        self.init()

    def init(self):
        self.symbol_sync=f2_symbol_sync(self)
        self.ofdm_demodulator=ofdm_demodulator(self)
        self.channel_equalizer=channel_equalizer(self)
        
        self.symbol_sync.io_iqSamples=self.io_iqSamples
        ## Rest of the sync-to-demodulator connections here

        self.channel_equalizer.A=self.ofdm_demodulator._Z
        self.channel_equalizer.A=self.ofdm_demodulator._Z
        self.channel_equalizer.equalize_sync=self.ofdm_demodulator._symbol_sync_out
        self.channel_equalizer.estimate_sync=  ## This Must be re-thinked.
        self.channel_equalizer.estimate_user_index=  ## This Must be re-thinked.
        self._Z=self.channel_equalizer._Z

        # Adds an entry named self._iofile_Bundle.Members['Z']
        self.vlogparameters=dict([ ('g_Rs',self.Rs),])

        if self.model=='vhdl':
            self.print_log(type='F', msg='VHDL model not yet supported')

    def main(self):
        self.symbol_sync.run()
        self.ofdm_demodulator.run()
        self.channel_equalizer.run()
        if self.par:
            self.queue.put(self._Z.Data)

    def run(self,*arg):
        if len(arg)>0:
            self.par=True      #flag for parallel processing
            self.queue=arg[0]  #multiprocessing.queue as the first argument
        if self.model=='py':
            self.main()
        else: 
          self.write_infile()

          if self.model=='sv':
              self.iofile_bundle.Members['io_iqSamples'].data=self.io_iqSamples.Data.reshape(-1,1)
              #These methods are defined in controller.py
              self.control_write.Data.Members['control_write'].adopt(parent=self)

              # Create testbench and execute the simulation
              self.define_testbench()
              self.tb.export(force=True)
              self.write_infile()
              self.run_verilog()
              self.read_outfile()
              del self.iofile_bundle
              self.run_verilog()

          elif self.model=='vhdl':
              self.print_log(type='F', msg='VHDL model not yet supported')


    def write_infile(self):
        for name, val in self.iofile_bundle.Members.items():
            if val.dir=='in':
                self.iofile_bundle.Members[name].write()

    def read_outfile(self):
        #Handle the ofiles here as you see the best
        a=self.iofile_bundle.Members['Z']
        a.read(dtype='object')
        self._Z.Data=a.data
        if self.par:
            self.queue.put(self._Z.Data)
        del self.iofile_bundle #Large files should be deleted

    # Testbench definition method
    def define_testbench(self):
        #Initialize testbench
        self.tb=vtb(self)

        # Dut is creted automaticaly, if verilog file for it exists
        self.tb.connectors.update(bundle=self.tb.dut_instance.io_signals.Members)

        #Assign verilog simulation parameters to testbench
        self.tb.parameters=self.vlogparameters

        # Copy iofile simulation parameters to testbench
        for name, val in self.iofile_bundle.Members.items():
            self.tb.parameters.Members.update(val.vlogparam)

        # Define the iofiles of the testbench. '
        # Needed for creating file io routines 
        self.tb.iofiles=self.iofile_bundle

        #Define testbench verilog file
        self.tb.file=self.vlogtbsrc

        # Create TB connectors from the control file
        for connector in self.control_write.Data.Members['control_write'].verilog_connectors:
            self.tb.connectors.Members[connector.name]=connector
            # Connect them to DUT
            try: 
                self.dut.ios.Members[connector.name].connect=connector
            except:
                pass

        ## Start initializations
        #Init the signals connected to the dut input to zero
        for name, val in self.tb.dut_instance.ios.Members.items():
            if val.cls=='input':
                val.connect.init='\'b0'

        # IO file connector definitions
        # Define what signals and in which order and format are read form the files
        # i.e. verilog_connectors of the file
        name='Z'  
        ionames=[]
        for i in range(self.Users):
            ionames+=[ 'io_Z_real_%s' %(i), 'io_Z_imag_%s' %(i) ]
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)
        for ioname in ionames:
            self.tb.connectors.Members[ioname].type='signed'
        self.iofile_bundle.Members[name].verilog_io_condition_append(cond='&& initdone')

        name='io_iqSamples'
        ionames=[]
        ionames+=[ name+'_real', name+'_imag']
        self.iofile_bundle.Members[name].verilog_connectors=\
                self.tb.connectors.list(names=ionames)
        self.iofile_bundle.Members[name].verilog_io_condition='initdone'

        self.tb.generate_contents()

if __name__=="__main__":
    import matplotlib.pyplot as plt
    from  ofdm_rx import *
    t=thesdk()
    t.print_log(type='I', msg="This is a testing template. Enjoy")
