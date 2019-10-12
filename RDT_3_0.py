import Network
import argparse
from time import sleep
import time
import hashlib


class Packet:
    ## the number of bytes used to store packet length
    seq_num_S_length = 10
    length_S_length = 10
    ## length of md5 checksum in hex
    checksum_length = 32 
        
    def __init__(self, seq_num, msg_S):
        self.seq_num = seq_num
        self.msg_S = msg_S
        
    @classmethod
    def from_byte_S(self, byte_S):
        if Packet.corrupt(byte_S):
            raise RuntimeError('Cannot initialize Packet: byte_S is corrupt')
        #extract the fields
        seq_num = int(byte_S[Packet.length_S_length : Packet.length_S_length+Packet.seq_num_S_length])
        msg_S = byte_S[Packet.length_S_length+Packet.seq_num_S_length+Packet.checksum_length :]
        return self(seq_num, msg_S)
        
        
    def get_byte_S(self):
        #convert sequence number of a byte field of seq_num_S_length bytes
        seq_num_S = str(self.seq_num).zfill(self.seq_num_S_length)
        #convert length to a byte field of length_S_length bytes
        length_S = str(self.length_S_length + len(seq_num_S) + self.checksum_length + len(self.msg_S)).zfill(self.length_S_length)
        #compute the checksum
        checksum = hashlib.md5((length_S+seq_num_S+self.msg_S).encode('utf-8'))
        checksum_S = checksum.hexdigest()
        #compile into a string
        return length_S + seq_num_S + checksum_S + self.msg_S
   
    
    @staticmethod
    def corrupt(byte_S):
        #extract the fields
        length_S = byte_S[0:Packet.length_S_length]
        seq_num_S = byte_S[Packet.length_S_length : Packet.seq_num_S_length+Packet.seq_num_S_length]
        checksum_S = byte_S[Packet.seq_num_S_length+Packet.seq_num_S_length : Packet.seq_num_S_length+Packet.length_S_length+Packet.checksum_length]
        msg_S = byte_S[Packet.seq_num_S_length+Packet.seq_num_S_length+Packet.checksum_length :]
        
        #compute the checksum locally
        checksum = hashlib.md5(str(length_S+seq_num_S+msg_S).encode('utf-8'))
        computed_checksum_S = checksum.hexdigest()
        #and check if the same
        return checksum_S != computed_checksum_S
        

class RDT:
    ## latest sequence number used in a packet
    seq_num = 1
    ## buffer of bytes read from network
    byte_buffer = '' 

    def __init__(self, role_S, server_S, port):
        self.network = Network.NetworkLayer(role_S, server_S, port)
    
    def disconnect(self):
        self.network.disconnect()
        
    def rdt_1_0_send(self, msg_S):
        p = Packet(self.seq_num, msg_S)
        self.seq_num += 1
        self.network.udt_send(p.get_byte_S())
        
    def rdt_1_0_receive(self):
        ret_S = None
        byte_S = self.network.udt_receive()
        self.byte_buffer += byte_S
        #keep extracting packets - if reordered, could get more than one
        while True:
            #check if we have received enough bytes
            if(len(self.byte_buffer) < Packet.length_S_length):
                return ret_S #not enough bytes to read packet length
            #extract length of packet
            length = int(self.byte_buffer[:Packet.length_S_length])
            if len(self.byte_buffer) < length:
                return ret_S #not enough bytes to read the whole packet
            #create packet from buffer content and add to return string
            p = Packet.from_byte_S(self.byte_buffer[0:length])
            ret_S = p.msg_S if (ret_S is None) else ret_S + p.msg_S
            #remove the packet bytes from the buffer
            self.byte_buffer = self.byte_buffer[length:]
            #if this was the last packet, will return on the next iteration
            
    
    def rdt_2_1_send(self, msg_S):
        # Make the packet
        p = Packet(self.seq_num, msg_S)
        # Send the packet
        self.network.udt_send(p.get_byte_S())
        # Use helper method to wait for ACK 
        # And to handle any NAKS/corruption
        self.handleAck(p)

    # Broken out handling of ACKS, saves repeat code and makes send method simpler
    def handleAck(self, packet):
        byte_stream = self.network.udt_receive()
        self.byte_buffer += byte_stream
        # Keep getting packets until ACK is received
        while True:
            byte_stream = self.network.udt_receive()
            self.byte_buffer += byte_stream

            # Check that enough bytes exist to get packet length
            if len(self.byte_buffer) >= Packet.length_S_length:
                # Get length of packet
                pLength = int(self.byte_buffer[0:Packet.length_S_length])
                # print("Packet Length field is valid")

                # Make sure enough bytes exist in byte buffer to make packet
                if len(self.byte_buffer) >= pLength:
                    # print("Packet length is valid")
                    # Make sure new packet isnt corrupt
                    # If it is purge buffer of packet and resend original packet
                    if Packet.corrupt(self.byte_buffer[0:pLength]):
                        print("Packet is corrupt")
                        self.byte_buffer = self.byte_buffer[pLength:]
                        self.network.udt_send(packet.get_byte_S())
                    # If packet is not corrupt make packet and process
                    else:
                        ackPack = Packet.from_byte_S(self.byte_buffer[0:pLength])
                        print(ackPack.msg_S + " " + str(ackPack.seq_num) + " " + str(self.seq_num))
                        # Purge buffer of packet
                        self.byte_buffer = self.byte_buffer[pLength:]
                        # If the message is an ACK all is good
                        if ackPack.msg_S == "ACK" and self.seq_num <= ackPack.seq_num:
                            # Increment seq number
                            self.seq_num += 1
                            print("Received ACK")
                            # Exit since we got ACK
                            return
                        else:
                            # Resend original packet 
                            self.network.udt_send(packet.get_byte_S())

    def rdt_2_1_receive(self):
        returnString = None
        byteSequence = self.network.udt_receive()
        self.byte_buffer += byteSequence
        # keep extracting packets
        while True:
            # check if we have enough bytes
            if (len(self.byte_buffer) < Packet.length_S_length):
                return returnString   # not enough bytes
            # extract length of packet
            length = int(self.byte_buffer[:Packet.length_S_length])
            if len(self.byte_buffer) < length:
                return returnString   # not enough bytes to read whole packet
            
            # create packet from buffer and add to return string

            # Check for packet corruption, if so send NACK
            if (Packet.corrupt(self.byte_buffer[0:length])):
                nackPacket = Packet(self.seq_num, "NACK")
                self.network.udt_send(nackPacket.get_byte_S()) # create nack and send it
                # purge byte buffer and await retransmission
                self.byte_buffer = self.byte_buffer[length:]

            else: # not corrupt
                packet = Packet.from_byte_S(self.byte_buffer[0:length])

                if packet.seq_num == self.seq_num:      # make sure its the same packet
                    # add message to return string
                    returnString = packet.msg_S if (returnString is None) else returnString + packet.msg_S
                    self.seq_num += 1
                    ackPacket = Packet(packet.seq_num, "ACK")
                    self.network.udt_send(ackPacket.get_byte_S())
                    self.waitForMore(ackPacket)
                # clear byte buffer
                self.byte_buffer = self.byte_buffer[length:]
    
    def rdt_3_0_send(self, msg_S):
        # Make the packet
        p = Packet(self.seq_num, msg_S)
        # Send the packet
        self.network.udt_send(p.get_byte_S())
        # Use helper method to wait for ACK 
        # And to handle any NAKS/corruption
        self.handleAck3(p)

    # Broken out handling of ACKS, saves repeat code and makes send method simpler
    # Now handles timeout error
    def handleAck3(self, packet):
        # Get the time right after packet is sent
        sentTime = time.time()
        # Set the timeout in seconds
        timeOut = 2
        byte_stream = self.network.udt_receive()
        self.byte_buffer += byte_stream
        # Keep getting packets until ACK is received
        while True:
            byte_stream = self.network.udt_receive()
            self.byte_buffer += byte_stream

            # Check that enough bytes exist to get packet length
            if len(self.byte_buffer) >= Packet.length_S_length:
                # Get length of packet
                pLength = int(self.byte_buffer[0:Packet.length_S_length])
                # print("Packet Length field is valid")

                # Make sure enough bytes exist in byte buffer to make packet
                if len(self.byte_buffer) >= pLength:
                    # print("Packet length is valid")
                    # Make sure new packet isnt corrupt
                    # If it is purge buffer of packet and resend original packet
                    if Packet.corrupt(self.byte_buffer[0:pLength]):
                        print("Packet is corrupt")
                        self.byte_buffer = self.byte_buffer[pLength:]
                        self.network.udt_send(packet.get_byte_S())
                    # If packet is not corrupt make packet and process
                    else:
                        ackPack = Packet.from_byte_S(self.byte_buffer[0:pLength])
                        print(ackPack.msg_S + " " + str(ackPack.seq_num) + " " + str(self.seq_num))
                        # Purge buffer of packet
                        self.byte_buffer = self.byte_buffer[pLength:]
                        # If the message is an ACK all is good
                        if ackPack.msg_S == "ACK" and self.seq_num <= ackPack.seq_num:
                            # Increment seq number
                            self.seq_num += 1
                            print("Received ACK")
                            # Exit since we got ACK
                            return
                        else:
                            # Resend original packet 
                            self.network.udt_send(packet.get_byte_S())
            # If no packet has come in after timeout resend
            else:
                if time.time() > sentTime + timeOut:
                    print("Resending due to timeout")
                    self.network.udt_send(packet.get_byte_S())

    def rdt_3_0_receive(self):
        returnString = None
        byteSequence = self.network.udt_receive()
        self.byte_buffer += byteSequence
        # keep extracting packets
        while True:
            # check if we have enough bytes
            if (len(self.byte_buffer) < Packet.length_S_length):
                return returnString   # not enough bytes
            # extract length of packet
            length = int(self.byte_buffer[:Packet.length_S_length])
            if len(self.byte_buffer) < length:
                return returnString   # not enough bytes to read whole packet
            
            # create packet from buffer and add to return string

            # Check for packet corruption, if so send NACK
            if (Packet.corrupt(self.byte_buffer[0:length])):
                nackPacket = Packet(self.seq_num, "NACK")
                self.network.udt_send(nackPacket.get_byte_S()) # create nack and send it
                # purge byte buffer and await retransmission
                self.byte_buffer = self.byte_buffer[length:]

            else: # not corrupt
                packet = Packet.from_byte_S(self.byte_buffer[0:length])

                if packet.seq_num == self.seq_num:      # make sure its the same packet
                    # add message to return string
                    returnString = packet.msg_S if (returnString is None) else returnString + packet.msg_S
                    self.seq_num += 1
                    ackPacket = Packet(packet.seq_num, "ACK")
                    self.network.udt_send(ackPacket.get_byte_S())
                    self.waitForMore(ackPacket)
                # clear byte buffer
                self.byte_buffer = self.byte_buffer[length:]

    def waitForMore(self, ack): 
        # wait a reasonable amount of time before closing the loop.
        timeout = time.time() + .1
        byteBuffer = ''
        while (time.time() < timeout):
            isDuplicate = False
            # continue extracting and add to bytebuffer
            byteSeq = self.network.udt_receive()
            byteBuffer += byteSeq

            if (len(byteBuffer) < Packet.length_S_length): 
                continue    # restart loop if not enough bytes
            length = int(byteBuffer[:Packet.length_S_length])
            if (len(byteBuffer) < length): 
                continue    # restart loop if length doesn't match defined packet length
            # Check if the packet is corrupt
            if (Packet.corrupt(byteBuffer[0:length])): 
                # if corrupted, create and send nack packet
                nackPacket = Packet(self.seq_num, 'NACK') 
                self.network.udt_send(nackPacket.get_byte_S()) 
                byteBuffer = '' 
                # if a duplicate is detected, add to timeout
                if (isDuplicate): 
                    timeout = timeout + .1
                continue
            else: # Time expired
                packet = Packet.from_byte_S(byteBuffer[0:length])
                if (packet.seq_num == self.seq_num - 1): 
                    isDuplicate = True
                    timeout = timeout + .1
                    self.network.udt_send(ack.get_byte_S()) #We don't have to wait anymore send ACK.
                    byteBuffer = ''
                else:
                    nack = Packet(self.seq_num, 'NACK')
                    self.network.udt_send(nack.get_byte_S())
                    break




        

if __name__ == '__main__':
    parser =  argparse.ArgumentParser(description='RDT implementation.')
    parser.add_argument('role', help='Role is either client or server.', choices=['client', 'server'])
    parser.add_argument('server', help='Server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()
    
    rdt = RDT(args.role, args.server, args.port)
    if args.role == 'client':
        rdt.rdt_3_0_send('MSG_FROM_CLIENT')
        sleep(2)
        print(rdt.rdt_3_0_receive())
        rdt.disconnect()
        
        
    else:
        sleep(1)
        print(rdt.rdt_3_0_receive())
        rdt.rdt_3_0_send('MSG_FROM_SERVER')
        rdt.disconnect()
        


        
        