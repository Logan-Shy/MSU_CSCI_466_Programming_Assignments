'''
Created on Oct 12, 2016

@author: mwittie
'''
import queue
import threading


## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.queue = queue.Queue(maxsize)
        self.mtu = None
    
    ##get packet from the queue interface
    def get(self):
        try:
            return self.queue.get(False)
        except queue.Empty:
            return None
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, block=False):
        self.queue.put(pkt, block)
        
        
## Implements a network layer packet (different from the RDT packet 
# from programming assignment 2).
# NOTE: This class will need to be extended to for the packet to include
# the fields necessary for the completion of this assignment.
class NetworkPacket:
    ## packet encoding lengths 
    dst_addr_S_length = 5
    sFlag_length = 1
    sNum_length = 5
    
    ##@param dst_addr: address of the destination host
    # @param data_S: packet payload
    def __init__(self, dst_addr, data_S, isSegmentFlag = False, segmentNumber = 0):
        self.dst_addr = dst_addr
        self.data_S = data_S
        self.segmentFlag = isSegmentFlag
        self.segmentNumber = segmentNumber
        
    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()
        
    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst_addr).zfill(self.dst_addr_S_length)
        byte_S += str(int(self.segmentFlag))
        byte_S += str(self.segmentNumber).zfill(self.sNum_length)
        byte_S += str(self.data_S)
        return byte_S
    
    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst_addr = int(byte_S[0 : NetworkPacket.dst_addr_S_length])
        segmentFlag = bool(int(byte_S[NetworkPacket.dst_addr_S_length]))
        segmentNumber = int(byte_S[NetworkPacket.dst_addr_S_length+2 : NetworkPacket.dst_addr_S_length+1+NetworkPacket.sNum_length])
        data_S = byte_S[NetworkPacket.dst_addr_S_length+1+NetworkPacket.sNum_length: ]
        return self(dst_addr, data_S, segmentFlag, segmentNumber)
    

    

## Implements a network host for receiving and transmitting data
class Host:
    segment_list = []
    packetDict = {}

    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.in_intf_L = [Interface()]
        self.out_intf_L = [Interface()]
        self.stop = False #for thread termination
    
    ## called when printing the object
    def __str__(self):
        return 'Host_%s' % (self.addr)
       
    ## create a packet and enqueue for transmission
    # @param dst_addr: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst_addr, data_S):
        # String to send can be done in one packet; make it so
        if len(data_S) <= 30:
            p = NetworkPacket(dst_addr, data_S)
            self.out_intf_L[0].put(p.to_byte_S()) #send packets always enqueued successfully
            print('%s: sending packet "%s" on the out interface with mtu=%d' % (self, p, self.out_intf_L[0].mtu))
        # data string is too big; break into smaller packets
        elif len(data_S) > 20:
            segmentCount = 0
            while len(data_S) > 20:
                segmentCount += 1 # add to segment count
                p = NetworkPacket(dst_addr, data_S[:19], True, segmentCount)    # make packet out of first 50 characters
                self.out_intf_L[0].put(p.to_byte_S())       # and send it
                print('%s: sending segment %i of packet "%s" on the out interface with mtu=%d' % (self, segmentCount, p, self.out_intf_L[0].mtu))
                data_S = data_S[19:]    # remove sent string from data string
            # data string no longer large than MTU; send final packet
            p = NetworkPacket(dst_addr, data_S, True, 0)
            self.out_intf_L[0].put(p.to_byte_S()) # send final packet
            print('%s: sending final segment of packet "%s" on the out interface with mtu=%d' % (self, p, self.out_intf_L[0].mtu))

    def reconstruct(self, segments, id):
        originalPkt = ''
        for segment in segments:
            #Check segment ID to prevent mismatches
            if segment[6] == id:
                #merge all segments
                originalPkt += segment[11:]
        return originalPkt

    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.in_intf_L[0].get()
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))
            #Check to see if packet is a segment
            if pkt_S[5] == '1':
                self.segment_list.append(pkt_S)
                #check for final packet
                if pkt_S[7] == pkt_S[9] and pkt_S[8] == pkt_S[10]:
                    #reconstruct original string
                    original = self.reconstruct(self.segment_list, pkt_S[6])
                    p = NetworkPacket(pkt_S[:5], 0, pkt_S[6] + '0000', original)
                    print('%s: reconstructed packet "%s"' % (self, p.to_byte_S()))

    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return
        


## Implements a multi-interface router described in class
class Router:
    
    ##@param name: friendly router name for debugging
    # @param intf_count: the number of input and output interfaces 
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, intf_count, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.in_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]
        self.out_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]

    ## called when printing the object
    def __str__(self):
        return 'Router_%s' % (self.name)

    ## look through the content of incoming interfaces and forward to
    # appropriate outgoing interfaces
    def forward(self):
        for i in range(len(self.in_intf_L)):
            pkt_S = None
            try:
                #get packet from interface i
                pkt_S = self.in_intf_L[i].get()
                #if packet exists make a forwarding decision
                if pkt_S is not None:
                    p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                    # HERE you will need to implement a lookup into the 
                    # forwarding table to find the appropriate outgoing interface
                    # for now we assume the outgoing interface is also i

                    # Packet segementation
                    self.out_intf_L[i].put(p.to_byte_S(), True)
                    print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' \
                        % (self, p, i, i, self.out_intf_L[i].mtu))
            except queue.Full:
                print('%s: packet "%s" lost on interface %d' % (self, p, i))
                pass
                
    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.forward()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return 