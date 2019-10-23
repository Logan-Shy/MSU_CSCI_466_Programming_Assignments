import network_2

p = network_2.NetworkPacket(1, "Test", True, 4)

temp = p.to_byte_S()

p2 = network_2.NetworkPacket.from_byte_S(temp)
#test = "01234565789"
test = str(int(False))
test1 = bool(int(test))
# print(test)
# print(test1)

# print("---")

print(p2.dst_addr)
print(p2.data_S)
print(p2.segmentFlag)
print(p2.segmentNumber)