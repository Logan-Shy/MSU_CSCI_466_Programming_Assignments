'''
Created on Oct 12, 2016

TODO:
Generate large message (80 characters) and modify udt_send to break packets 
into smaller packets

@author: mwittie
'''
import network_1
import link_1
import threading
from time import sleep

##configuration parameters
router_queue_size = 0 #0 means unlimited
simulation_time = 1 #give the network sufficient time to transfer all packets before quitting

if __name__ == '__main__':
    object_List = [] #keeps track of objects, so we can kill their threads
    
    #create network nodes
    client = network_1.Host(1)
    object_List.append(client)
    server = network_1.Host(2)
    object_List.append(server)
    router_a = network_1.Router(name='A', intf_count=1, max_queue_size=router_queue_size)
    object_List.append(router_a)
    
    #create a Link Layer to keep track of links between network nodes
    link_layer = link_1.LinkLayer()
    object_List.append(link_layer)
    
    #add all the links
    #link parameters: from_node, from_intf_num, to_node, to_intf_num, mtu
    link_layer.add_link(link_1.Link(client, 0, router_a, 0, 50))
    link_layer.add_link(link_1.Link(router_a, 0, server, 0, 50))
    
    
    #start all the objects
    thread_List = []
    thread_List.append(threading.Thread(name=client.__str__(), target=client.run))
    thread_List.append(threading.Thread(name=server.__str__(), target=server.run))
    thread_List.append(threading.Thread(name=router_a.__str__(), target=router_a.run))
    
    thread_List.append(threading.Thread(name="Network", target=link_layer.run))
    
    for t in thread_List:
        t.start()
    
    
    #Send one large file to be split into smaller packets.   
    
    client.udt_send(2, 'This is gonna be one long boyo. Did you know my father died when I was a little boy?')
    
    
    #give the network sufficient time to transfer all packets before quitting
    sleep(simulation_time)
    
    #join all threads
    for o in object_List:
        o.stop = True
    for t in thread_List:
        t.join()
        
    print("All simulation threads joined")



# writes to host periodically