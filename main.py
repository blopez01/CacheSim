#!/usr/bin/python

# sys library allows access to command line args
import sys
# re library allows regular expressions
import re

from random import seed
from random import randint

def ToBytes(size):
    '''
    Converts the given size (in KB, MB, or GB) to bytes.

    :param size: the size given in KB, MB, or GB
    :return: the converted size in bytes.
    '''

    convertedSize = 0

    if 'KB' in size:
        convertedSize = int(size[0:-2])
        convertedSize *= 1024
    elif 'MB' in size:
        convertedSize = int(size[0:-2])
        convertedSize *= 1048576
    elif 'GB' in size:
        convertedSize = int(size[0:-2])
        convertedSize *= 1073741824

    return convertedSize

# calculateArgs grabs some command line args and uses them to calculate cache metrics
def calculateArgs():

    # retrieve some command line args
    fileNames = []
    for i in range(0, len(sys.argv)):
        if sys.argv[i] == "-f":
            fileNames.append(sys.argv[i + 1])
        elif sys.argv[i] == "-s":
            cSize = int(sys.argv[i + 1])
        elif sys.argv[i] == "-b":
            bSize = int(sys.argv[i + 1])
        elif sys.argv[i] == "-a":
            assoc = int(sys.argv[i + 1])
        elif sys.argv[i] == "-r":
            replacementpolicy = sys.argv[i + 1]
            if replacementpolicy == "RR":
                rPolicy = "Round Robin"
            elif replacementpolicy == "RND":
                rPolicy = "Random"
        elif sys.argv[i] == "-p":
            physicalmemory = sys.argv[i + 1]
            physmembytes = ToBytes(physicalmemory)

    # declare some local temporary variables to calculate cache metrics
    tempCacheSize = int(cSize)
    tempAssoc = int(assoc)
    tempBlockSize = int(bSize)

    # declare some other local variables to keep track of bits
    count = 0
    assocBits = 0
    blockOffsetBits = 0

    # cost of cache memory per KB
    kbCost = 0.15

    # calculate individual bits used for cache
    while tempCacheSize > 1:
        tempAssoc = tempAssoc / 2
        if tempAssoc >= 1:
            assocBits += 1
        tempBlockSize = tempBlockSize / 2
        if tempBlockSize >= 1:
            blockOffsetBits += 1
        tempCacheSize = tempCacheSize/2
        count += 1
    cacheBits = 10 + count

    # calculate some other metrics of the cache

    indexBits = cacheBits - (blockOffsetBits + assocBits)

    totalBlocks = pow(2, (indexBits + assocBits))

    tagBits = 32 - blockOffsetBits - indexBits

    totalRows = pow(2, indexBits)

    overhead = (totalBlocks / 8) + ((totalBlocks * tagBits) / 8)

    impMemSize = overhead + pow(2, cacheBits)

    impMemSizeKB = float(impMemSize) / 1024.00

    totalCost = impMemSizeKB * kbCost

    return cSize, bSize, assoc, rPolicy, totalBlocks, tagBits, indexBits, totalRows, overhead, impMemSize, impMemSizeKB, totalCost, physicalmemory, fileNames

def simulation(filename):
    cSize, bSize, assoc, rPolicy, totalBlocks, tagBits, indexBits, totalRows, overhead, impMemSize, impMemSizeKB, totalCost, physicalmemory, fileNames = calculateArgs()

    kbCost = 0.13

    cacheDict = dict()
    cacheAccess = 0
    hit = 0
    compMiss = 0
    confMiss = 0
    instruction = 0
    cycle = 0

    missCycleReads = int(bSize) / 4

    # make regex patterns to match to lines
    progEIP = re.compile('(^EIP) \(([0-9][0-9])\): ([0-9a-z]+)')
    progdstM = re.compile('(^dstM): ([0-9a-z]+) .*srcM: ([0-9a-z]+)')

    # open file and read lines
    f = open(filename, "r")
    while f:
        line = f.readline()
        # verify regex matches
        matchEIP = re.match(progEIP, line)
        matchdstM = re.match(progdstM, line)
        # if instruction line
        if matchEIP:
            instrLen = matchEIP.group(2)
            eipAddr = matchEIP.group(3)

            instruction += 1
            cycle += 2

            hexAddr = "0x" + eipAddr
            intConv = int(hexAddr, 16)
            hexAddr = hex(intConv)
            offset = intConv & 15
            index = intConv >> 4 & (totalRows - 1)
            totalTag = pow(2, tagBits) - 1
            tag = intConv >> (indexBits + 4) & totalTag

            if hex(index) in cacheDict:
                hitFound = 0
                for i in range(1, len(cacheDict[hex(index)])):
                    if cacheDict[hex(index)][i] == hex(tag):
                        hit += 1
                        hitFound = 1
                        cycle += 1
                        break
                if hitFound == 0:
                    # otherwise we must replace a tag
                    # check if key has max values
                    if len(cacheDict[hex(index)]) == int(assoc) + 1:
                        # random replacement policy
                        if rPolicy == "RND":
                            # generate a random value from 1 to assoc, inclusive
                            rValue = randint(1, int(assoc))
                            # go to element in cache array and replace that element
                            cacheDict[hex(index)][rValue] = hex(tag)

                        # round robin replacement policy
                        if rPolicy == "RR":
                            # get next element to replace, which is first element in array of that index
                            rValue = cacheDict[hex(index)][0]
                            # go to element in cache array and replace that element
                            cacheDict[hex(index)][rValue] = hex(tag)
                            # increment value for next element to be replaced
                            rValue += 1
                            # if increment exceeds assoc range, reset to 1
                            if rValue > int(assoc):
                                rValue = 1
                            # set value in first element of array for that index for next replacement
                            cacheDict[hex(index)][0] = rValue
                        confMiss += 1
                        cycle += (4 * missCycleReads)
                    else:
                        # if we have space in the row, add to the cache value array
                        cacheDict[hex(index)].append(hex(offset))
                        compMiss += 1
                        cycle += (4 * missCycleReads)
            else:
                # if the index is not yet in the cache, initialize the first element of the cache value array to be the replacement value
                cacheDict[hex(index)] = [1]
                # append the value into the array
                cacheDict[hex(index)].append(hex(tag))
                compMiss += 1
                cycle += (4 * missCycleReads)
            cacheAccess += 1
            # print(matchEIP.group(1), instrLen, hexAddr, hex(tag), hex(index), hex(offset))
            # print(cacheDict)
            # print(cacheAccess, hit, compMiss, confMiss)

        # if memory line
        if matchdstM:
            dstMAddr = matchdstM.group(2)
            srcMAddr = matchdstM.group(3)
            if dstMAddr != "00000000":
                # do something

                cycle += 1
                hexAddr = "0x" + dstMAddr
                intConv = int(hexAddr, 16)
                hexAddr = hex(intConv)
                offset = intConv & 15
                index = intConv >> 4 & (totalRows - 1)
                totalTag = pow(2, tagBits) - 1
                tag = intConv >> (indexBits + 4) & totalTag

                if hex(index) in cacheDict:
                    hitFound = 0
                    for i in range(1, len(cacheDict[hex(index)])):
                        if cacheDict[hex(index)][i] == hex(tag):
                            hit += 1
                            hitFound = 1
                            cycle += 1
                            break
                    if hitFound == 0:
                        # otherwise we must replace a tag
                        # check if key has max values
                        if len(cacheDict[hex(index)]) == int(assoc) + 1:
                            # random replacement policy
                            if rPolicy == "RND":
                                # generate a random value from 1 to assoc, inclusive
                                rValue = randint(1, int(assoc))
                                # go to element in cache array and replace that element
                                cacheDict[hex(index)][rValue] = hex(tag)

                            # round robin replacement policy
                            if rPolicy == "RR":
                                # get next element to replace, which is first element in array of that index
                                rValue = cacheDict[hex(index)][0]
                                # go to element in cache array and replace that element
                                cacheDict[hex(index)][rValue] = hex(tag)
                                # increment value for next element to be replaced
                                rValue += 1
                                # if increment exceeds assoc range, reset to 1
                                if rValue > int(assoc):
                                    rValue = 1
                                # set value in first element of array for that index for next replacement
                                cacheDict[hex(index)][0] = rValue
                            confMiss += 1
                            cycle += (4 * missCycleReads)
                        else:
                            # if we have space in the row, add to the cache value array
                            cacheDict[hex(index)].append(hex(offset))
                            compMiss += 1
                            cycle += (4 * missCycleReads)
                else:
                    # if the index is not yet in the cache, initialize the first element of the cache value array to be the replacement value
                    cacheDict[hex(index)] = [1]
                    # append the value into the array
                    cacheDict[hex(index)].append(hex(tag))
                    compMiss += 1
                    cycle += (4 * missCycleReads)
                cacheAccess += 1
            if srcMAddr != "00000000":
                cycle += 1
                hexAddr = "0x" + srcMAddr
                intConv = int(hexAddr, 16)
                hexAddr = hex(intConv)
                offset = intConv & 15
                index = intConv >> 4 & (totalRows - 1)
                totalTag = pow(2, tagBits) - 1
                tag = intConv >> (indexBits + 4) & totalTag

                if hex(index) in cacheDict:
                    hitFound = 0
                    for i in range(1, len(cacheDict[hex(index)])):
                        if cacheDict[hex(index)][i] == hex(tag):
                            hit += 1
                            hitFound = 1
                            cycle += 1
                            break
                    if hitFound == 0:
                        # otherwise we must replace a tag
                        # check if key has max values
                        if len(cacheDict[hex(index)]) == int(assoc) + 1:
                            # random replacement policy
                            if rPolicy == "RND":
                                # generate a random value from 1 to assoc, inclusive
                                rValue = randint(1, int(assoc))
                                # go to element in cache array and replace that element
                                cacheDict[hex(index)][rValue] = hex(tag)

                            # round robin replacement policy
                            if rPolicy == "RR":
                                # get next element to replace, which is first element in array of that index
                                rValue = cacheDict[hex(index)][0]
                                # go to element in cache array and replace that element
                                cacheDict[hex(index)][rValue] = hex(tag)
                                # increment value for next element to be replaced
                                rValue += 1
                                # if increment exceeds assoc range, reset to 1
                                if rValue > int(assoc):
                                    rValue = 1
                                # set value in first element of array for that index for next replacement
                                cacheDict[hex(index)][0] = rValue
                            confMiss += 1
                            cycle += (4 * missCycleReads)
                        else:
                            # if we have space in the row, add to the cache value array
                            cacheDict[hex(index)].append(hex(offset))
                            compMiss += 1
                            cycle += (4 * missCycleReads)
                else:
                    # if the index is not yet in the cache, initialize the first element of the cache value array to be the replacement value
                    cacheDict[hex(index)] = [1]
                    # append the value into the array
                    cacheDict[hex(index)].append(hex(tag))
                    compMiss += 1
                    cycle += (4 * missCycleReads)
                cacheAccess += 1
        # if EOF
        if line == "":
            break
    f.close()
    totalMiss = confMiss + compMiss
    hitRate = (hit * 100) / cacheAccess
    missRate = 100 - hitRate
    cpi = cycle/instruction
    unusedKB = (((int(totalBlocks) - compMiss) * (int(bSize) + overhead)) / 1024) / (int(cSize) * 1024)
    unusedKBPercent = (unusedKB * 100) / impMemSizeKB
    waste = kbCost * unusedKB
    return cacheAccess, hit, compMiss, confMiss, hitRate, missRate, totalMiss, cpi, unusedKB, unusedKBPercent, waste
def display(filename):
    # import variables from calculateArgs()
    bSize: int
    cSize, bSize, assoc, rPolicy, totalBlocks, tagBits, indexBits, totalRows, overhead, impMemSize, impMemSizeKB, totalCost, physicalmemory, fileNames = calculateArgs()
    cacheAccess, hit, compMiss, confMiss, hitRate, missRate, totalMiss, cpi, unusedKB, unusedKBPercent, waste = simulation(filename)

    print("Cache Simulator CS 3853 Fall 2021 - Group #5\n")
    print("Trace File: ", filename, "\n")

    print("***** Cache Input Parameters *****")
    print("Cache Size:", cSize, "KB")
    print("Block Size:", bSize, "bytes")
    print("Associativity:", assoc)
    print("Replacement Policy:", rPolicy)
    print("Physical Memory:", physicalmemory, "\n")

    print("***** Cache Calculated Values *****\n")
    print("Total # Blocks:", totalBlocks)
    print("Tag Size:", tagBits, "bits")
    print("Index Size:", indexBits, "bits")
    print("Total # Rows:", totalRows)
    print("Overhead Size:", overhead, "bytes")
    print("Implementation Memory Size: " + str(round(impMemSizeKB, 2)) + " KB " + "(" + str(round(impMemSize, 2)) + " bytes)")
    print("Cost: $%.2f\n" % totalCost)

    print("***** CACHE SIMULATION RESULTS *****\n")
    print("Total Cache Accesses:", cacheAccess)
    print("Cache Hits:", hit)
    print("Cache Misses", totalMiss)
    print("--- Compulsory Misses:", compMiss)
    print("--- Conflict Misses:", confMiss, "\n")

    print("***** ***** CACHE HIT & MISS RATE ***** *****\n")
    print("Hit Rate:", round(hitRate, 2), "%")
    print("Miss Rate:", round(missRate, 2), "%")
    print("CPI:", round(cpi, 2), "Cycles/Instruction")
    print("Unused Cache Space:", round(unusedKB, 2), "/", round(impMemSizeKB, 2), "=", round(unusedKBPercent, 2), "%   Waste: $", round(waste, 2))
    print("Unused Cache Blocks:", int((unusedKB * 1024) // bSize), "/", totalBlocks, "\n")

    print("***** VIRTUAL MEMORY RESULTS *****\n")
    print("Physical Memory:", physicalmemory, "\n")

def main():
    seed()
    calculateArgs()
    cSize, bSize, assoc, rPolicy, totalBlocks, tagBits, indexBits, totalRows, overhead, impMemSize, impMemSizeKB, totalCost, physicalmemory, fileNames = calculateArgs()
    for i in fileNames:
        simulation(i)
        display(i)

main()