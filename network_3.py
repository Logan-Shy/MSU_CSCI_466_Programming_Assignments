# coding: utf-8
import queue
import threading
import time


## wrapper class for a queue of packets
from pandas._libs import json

class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):
        self.in_queue = queue.Queue(maxsize)
        self.out_queue = queue.Queue(maxsize)
    
    ##get packet from the queue interface
    # @param in_or_out - use 'in' or 'out' interface
    def get(self, in_or_out):
        try:
            if in_or_out == 'in':
                pkt_S = self.in_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the IN queue')
                return pkt_S
            else:
                pkt_S = self.out_queue.get(False)
                # if pkt_S is not None:
                #     print('getting packet from the OUT queue')
                return pkt_S
        except queue.Empty:
            return None
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param in_or_out - use 'in' or 'out' interface
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, in_or_out, block=False):
        if in_or_out == 'out':
            # print('putting packet in the OUT queue')
            self.out_queue.put(pkt, block)
        else:
            # print('putting packet in the IN queue')
            self.in_queue.put(pkt, block)
            
        
## Implements a network layer packet.
class NetworkPacket:
    ## packet encoding lengths 
    distance_S_length = 5
    prot_S_length = 1
    
    ##@param distance: address of the destination host
    # @param data_S: packet payload
    # @param prot_S: upper layer protocol for the packet (data, or control)
    def __init__(self, distance, prot_S, data_S):
        self.distance = distance
        self.data_S = data_S
        self.prot_S = prot_S
        
    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()
        
    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.distance).zfill(self.distance_S_length)
        if self.prot_S == 'data':
            byte_S += '1'
        elif self.prot_S == 'control':
            byte_S += '2'
        else:
            raise('%s: unknown prot_S option: %s' %(self, self.prot_S))
        byte_S += self.data_S
        return byte_S
    
    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        distance = byte_S[0 : NetworkPacket.distance_S_length].strip('0')
        prot_S = byte_S[NetworkPacket.distance_S_length : NetworkPacket.distance_S_length + NetworkPacket.prot_S_length]
        if prot_S == '1':
            prot_S = 'data'
        elif prot_S == '2':
            prot_S = 'control'
        else:
            raise('%s: unknown prot_S field: %s' %(self, prot_S))
        data_S = byte_S[NetworkPacket.distance_S_length + NetworkPacket.prot_S_length : ]        
        return self(distance, prot_S, data_S)
    

    

## Implements a network host for receiving and transmitting data
class Host:
    
    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.intf_L = [Interface()]
        self.stop = False #for thread termination
    
    ## called when printing the object
    def __str__(self):
        return self.addr
       
    ## create a packet and enqueue for transmission
    # @param distance: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, distance, data_S):
        p = NetworkPacket(distance, 'data', data_S)
        print('%s: sending packet "%s"' % (self, p))
        self.intf_L[0].put(p.to_byte_S(), 'out') #send packets always enqueued successfully
        
    ## receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.intf_L[0].get('in')
        if pkt_S is not None:
            print('%s: received packet "%s"' % (self, pkt_S))
       
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
        


## Implements a multi-interface router
class Router:
    
    ##@param name: friendly router name for debugging
    # @param cost_D: cost table to neighbors {neighbor: {interface: cost}}
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, cost_D, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.intf_L = [Interface(max_queue_size) for _ in range(len(cost_D))]
        #save neighbors and interfeces on which we connect to them
        self.cost_D = cost_D    # {neighbor: {interface: cost}}
        #TODO: set up the routing table for connected hosts
        self.rt_tbl_D = {}  # {destination: {router: cost}}
        for neighbor in self.cost_D:
            for interface in self.cost_D[neighbor]:
                row = {}
                row[self.name] = self.cost_D[neighbor][interface]
                self.rt_tbl_D[neighbor] = row
                break

        self.rt_tbl_D[self.name] = {}
        self.rt_tbl_D[self.name][self.name] = 0

        print('%s: Initialized routing table' % self)
        self.print_routes()
    ## Print routing table
    def print_routes(self):
        # TODO: print the routes as a two dimensional table
        print(self.rt_tbl_D)
        print("╒══════"+"╤══════"*(len(self.rt_tbl_D)-1)+"╤══════╕")
        print("|  " + self.name + "  |", end="")
        for router in (self.rt_tbl_D):
            print("  " + router + "  |", end="")
        print("")
        print("╞══════"+"╪══════"*(len(self.rt_tbl_D)-1)+"╪══════╡")
        routers = {}
        for destination in self.rt_tbl_D:
            for val in self.rt_tbl_D[destination]:
                routers.setdefault(val, [])
                routers[val].append(self.rt_tbl_D[destination][val])
        for val in routers:
            print("|  " + val + "  |", end="")
            for i in routers[val]:
                print("  ", i, " |", end="")
            print("")
        print("╘══════"+"╧══════"*(len(self.rt_tbl_D)-1)+"╧══════╛")


    ## called when printing the object
    def __str__(self):
        return self.name


    ## look through the content of incoming interfaces and 
    # process data and control packets
    def process_queues(self):
        for i in range(len(self.intf_L)):
            pkt_S = None
            #get packet from interface i
            pkt_S = self.intf_L[i].get('in')
            #if packet exists make a forwarding decision
            if pkt_S is not None:
                p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                if p.prot_S == 'data':
                    self.forward_packet(p,i)
                elif p.prot_S == 'control':
                    self.update_routes(p, i)
                else:
                    raise Exception('%s: Unknown packet type in packet %s' % (self, p))
            

    # Cost function for routing
    # Takes in a packet, and incoming interface
    # Returns the interface to send on
    def getCost(self, p, i):
        # Get destination dict from self
        dest = p.distance
        # If dest is a neighbor, send it
        if dest in self.cost_D.keys():
            return(dest)
        # If dest is not a neighbor calculate paths
        else:
            # Find router with cheapest cost to destination, and work backwards until we hit 
            # current router
            routers = self.rt_tbl_D[dest]
            routerWLowestCost = ""
            lcost = 50
            for router in routers:
                cost = routers[router]
                if cost < lcost:
                    routerWLowestCost = router
                    lcost = cost
            return(routerWLowestCost)
                    

    ## forward the packet according to the routing table
    #  @param p Packet to forward
    #  @param i Incoming interface number for packet p
    def forward_packet(self, p, i):
        try:
            # TODO: Here you will need to implement a lookup into the 
            # forwarding table to find the appropriate outgoing interface
            # for now we assume the outgoing interface is 1

            # Packet knows destination
            # Router has table showing proper interface for transmission
            # Router also knows costs to transmit
            # TODO: Cost function to determine route?
            # Get proper interface to send on
            routerToUse = self.getCost(p, i)
            dictT = self.cost_D[routerToUse]
            print(dictT)
            inter, cost = dictT.popitem()
            print("Cost of %d to jump to %s from %s" % (cost, routerToUse, self.name))
            self.intf_L[inter].put(p.to_byte_S(), 'out', True)
            print('%s: forwarding packet "%s" from interface %d to %d' % \
                (self, p, i, inter))
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## send out route update
    # @param i Interface number on which to send out a routing update
    def send_routes(self, i):
        # TODO: Send out a routing table update
        distVector = {}
        for distance in self.rt_tbl_D:
            for router in self.rt_tbl_D[distance]:
                if (router == self.name):
                    distVector[distance] = {}
                    distVector[distance][router] = self.rt_tbl_D[distance][router]

        msg = json.dumps(distVector)
        p = NetworkPacket(0, 'control', msg)
        print("name: %s, msg: %s" % (self.name, msg))
        try:
            print('%s: sending routing update "%s" from interface %d' % (self, p, i))
            self.intf_L[i].put(p.to_byte_S(), 'out', True)
        except queue.Full:
            print('%s: packet "%s" lost on interface %d' % (self, p, i))
            pass


    ## forward the packet according to the routing table
    #  @param p Packet containing routing information
    def update_routes(self, p, i):
        #TODO: add logic to update the routing tables and
        # possibly send out routing updates
        distVector = json.loads(p.data_S) # {destination: {router: cost}}
        for distance in distVector:
            for router in distVector[distance]:
                if distance not in self.rt_tbl_D:
                    self.rt_tbl_D[distance] = {}
                self.rt_tbl_D[distance][router] = distVector[distance][router]
        updated = False
        for distance in self.rt_tbl_D:
            if distance == self.name:
                continue
            minCost = 999
            if self.name in self.rt_tbl_D[distance]:
                minCost = self.rt_tbl_D[distance][self.name]
            for router in self.rt_tbl_D[distance]:
                cost = 0
                if router == self.name:
                    cost += self.rt_tbl_D[distance][router]
                else:
                    cost += self.rt_tbl_D[router][self.name] + self.rt_tbl_D[distance][router]
                if cost < minCost:
                    updated = True
                    minCost = cost
            self.rt_tbl_D[distance][self.name] = minCost
        if updated:
            for i in range(0, len(self.intf_L)):
                self.send_routes(i)
        print('%s: Received routing update %s from interface %d' % (self, p, i))

                
    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.process_queues()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return 