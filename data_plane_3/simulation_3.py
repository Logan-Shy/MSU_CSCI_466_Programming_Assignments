'''
Created on Oct 12, 2016

TODO:
1. Generate large message (80 characters) and modify udt_send to break packets 
into smaller packets
2. modify MTU of second link to 30 (router_A -> server); Extend packet format in 
networkPacket class to implement segmentation (look at slide/book). Add packet stitching.
3. Add more hosts and links in simulation class to match given topology, and start them.
4. In network.py, modify the forward function in the router class to use a router 
table to send packets to the correct interface (from static to dynamic forwarding).
5. Extend packet class to allow router to decipher which host the packet arrived from.

@author: mwittie
'''
import network_3
import link_3
import threading
from time import sleep

##configuration parameters
router_queue_size = 0 #0 means unlimited
simulation_time = 1 #give the network sufficient time to transfer all packets before quitting

if __name__ == '__main__':
    object_List = [] #keeps track of objects, so we can kill their threads
    
    #create network nodes
    client = network_3.Host(1)
    object_List.append(client)
    server = network_3.Host(2)
    object_List.append(server)
    router_a = network_3.Router(name='A', intf_count=1, max_queue_size=router_queue_size)
    object_List.append(router_a)
    
    #create a Link Layer to keep track of links between network nodes
    link_layer = link_3.LinkLayer()
    object_List.append(link_layer)
    
    #add all the links
    #link parameters: from_node, from_intf_num, to_node, to_intf_num, mtu
    link_layer.add_link(link_3.Link(client, 0, router_a, 0, 50))
    link_layer.add_link(link_3.Link(router_a, 0, server, 0, 50))
    
    
    #start all the objects
    thread_List = []
    thread_List.append(threading.Thread(name=client.__str__(), target=client.run))
    thread_List.append(threading.Thread(name=server.__str__(), target=server.run))
    thread_List.append(threading.Thread(name=router_a.__str__(), target=router_a.run))
    
    thread_List.append(threading.Thread(name="Network", target=link_layer.run))
    
    for t in thread_List:
        t.start()
    
    
    #create some send events    
    for i in range(3):
        client.udt_send(2, 'Sample data %d' % i)
    
    
    #give the network sufficient time to transfer all packets before quitting
    sleep(simulation_time)
    
    #join all threads
    for o in object_List:
        o.stop = True
    for t in thread_List:
        t.join()
        
    print("All simulation threads joined")



# writes to host periodically