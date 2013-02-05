import MySQLdb
import sys
from termcolor import colored, cprint


# Import pygraph
from pygraph.classes.graph import graph
from pygraph.algorithms.filters.radius import radius
from pygraph.algorithms.searching import breadth_first_search
from pygraph.algorithms.minmax import shortest_path
from texttable import *

# Import for benchmark
# from time import clock
import datetime
clock = datetime.datetime.now
# bid = 0 - sell, can buy
# bid = 1 - buy, can sell
import padnums

def arrayList(array): # ['a','b','c'] -> 'a,b,c'
    length = len(array)
    result = '%s' % array[0]
    for x in xrange(1, length):
        result += ', %s' % array[x]
    return result

def arrayOpen(array): # ((a,),(b,)) -> (a,b)
    result = []
    for x in array:
        for y in x:
            result.append(y)
    return result

def formDict(keys,values):
    if (len(keys) != len(values)):
        return 0
    result = {}
    for x in xrange(len(keys)):
        result[keys[x]] = values[x]
    return result


def printByLine(array):
    for x in array:
        print x

def printByLineD(dict):
    for x in dict:
        print "%s: %s" % (x,dict[x])

# Dictionary Categories
def containsAllKeys(dictionary,keys):
    if all (k in dictionary for k in keys):
        return True
    else:
        return False

def selectByKeys(dictionary,keys):
    result = {}
    for key in keys:
        result[key] = dictionary[key]
    return result

# Color
def colorRate(rate):
        if rate > 0.5:
            return 'green'   
        else:  
             return 'red'

# Deals

class Deal(object):
    typeID = 0
    iBuyOrderID = 0 # Order to buy with
    iSellOrderID = 0 # Order to sell to
    iBuySSID = 0 # Where sell order is
    iSellSSID = 0 # Where buy order is
    profit = 0
    amount = 0
    rang = 1

    typeInfo = 0
    iBuySSInfo = 0 # SS where i buy
    iSellSSInfo = 0 # SS where i sell
    iBuyOrderInfo = 0
    iSellOrderInfo = 0
    jumps = 0

    def __init__(self,array,db): # typeID, sellOrderID, buyOrderID, sellSSID, buySSID, profit, amount
        self.typeID = array[0]
        self.iBuyOrderID = array[1] # Order to sell to
        self.iSellOrderID = array[2] # Order to buy with
        self.iBuySSID = array[3] # Where sell order is
        self.iSellSSID = array[4] # Where buy order is
        self.profit = array[5]
        self.amount = array[6]

        self.typeInfo = db.getTypeInfo(self.typeID)
        self.iBuySSInfo = db.getSSInfo(self.iBuySSID)
        self.iSellSSInfo = db.getSSInfo(self.iSellSSID)
        self.iBuyOrderInfo = db.getOrderInfo(self.iBuyOrderID)
        self.iSellOrderInfo = db.getOrderInfo(self.iSellOrderID)
        self.jumps = db.getJumpsBetweenSS(self.iBuySSID,self.iSellSSID)
    # def __repr__(self):
    #     return '%d' % (self.typeID)
    # def __str__(self):
    #     return '%d \t %s (%d m3) \t %d \t %s(%.1f) ----> %s(%.1f) \t (%d jumps)'\
    #     % self.desc()
    
    def desc(self):
        # print         self.iSellOrderInfo
        return [self.typeInfo[0],
        self.amount,
        self.typeInfo[1]*self.amount, 
        self.iBuyOrderInfo[1]*self.amount, 
        self.profit*self.amount, 
        self.profit / float(self.iBuyOrderInfo[1]) * 100,
        self.iSellOrderInfo[1]*self.amount, 
        self.iBuySSInfo[1], self.iBuySSInfo[2], 
        self.iSellSSInfo[1], self.iSellSSInfo[2], self.jumps]
    
    @staticmethod
    def printDeals(deals):
        table = map(lambda x: x.desc(),deals)
        for entry in table:
            entry[4] = "%d (%.1f)" % (entry[4],entry[5])
            entry[7] = "%s (%.1f)" % (entry[7],entry[8])
            entry[9] = "%s (%.1f)" % (entry[9],entry[10])
            del entry[5]
            del entry[7]
            del entry[8]
        table.insert(0,("TYPE","AMOUNT","VOLUME","BUY PRICE","PROFIT","SELL PRICE","BUY","SELL","JUMPS"))
        padnums.pprint_table(sys.stdout,table)


class DatabaseDelegate(object):
    cursor = object()
    qdt = 0 # Last query dt
    ssgraph = 0 # Solar System Graph

    solarSystemsInfoCache = {}
    typeInfoCache = {}
    jumpsCache = {}
    ordersInfoCache = {}

    def __init__(self):
        # db = MySQLdb.connect(host="aspcart.hopto.org", user="tkorchagin", passwd="78789898",db="EVE")   
        db = MySQLdb.connect(host="192.168.0.111", user="aspcartman", passwd="vicevice",db="EVE")
        self.cursor = db.cursor()

    def runQueryR(self,query):
        time = clock()
        self.cursor.execute(query)
        self.qdt = clock() - time
        return self.cursor.fetchall()

    def removeOldRows(self):
        print "Removing orders older than 24 hours."
        sqlQuery = "DELETE FROM emdrOrders WHERE DATEDIFF(CURDATE(),`generatedAt`) > 1"
        self.runQueryR(sqlQuery)

# Orders ========================================

    def getOrderInfo(self,orderID):
        if orderID in self.ordersInfoCache:
            return self.ordersInfoCache[orderID]

        sqlQuery = "SELECT * FROM `emdrOrders` WHERE `orderID` = %d" % orderID
        result = self.runQueryR(sqlQuery)
        result = arrayOpen(result)

        self.ordersInfoCache[orderID] = result
        return result

# End Orders ====================================

# Deals =========================================

    def getDealsAroundSS(self,SS,radius):
        solarSystems = self.getSSAroundSS(SS,radius)
        print "Getting Sell Orders"
        sqlSellOrders = "SELECT `orderID`,`typeID`,`price`,`volRemaining`, `solarSystemID`\
                         FROM `emdrOrders`\
                         WHERE `solarSystemID` IN (%s) AND `BID` = 0 AND `generatedAt` > ADDDATE(NOW(), INTERVAL -9 HOUR)\
                         ORDER BY `typeID`,`price`" % arrayList(solarSystems)
        sellOrders = list(self.runQueryR(sqlSellOrders))
        sellOrders = map(lambda x: list(x), sellOrders)
        print "Done in %s. %d" % (self.qdt,len(sellOrders))

        print "Getting Buy Orders"
        sqlBuyOrders = " SELECT `orderID`,`typeID`,`price`,`volRemaining`, `solarSystemID`\
                         FROM `emdrOrders`\
                         WHERE `solarSystemID` IN (%s) AND `BID` = 1 AND `generatedAt` > ADDDATE(NOW(), INTERVAL -9 HOUR)\
                         ORDER BY `typeID`,`price` DESC" % arrayList(solarSystems)
        buyOrders = list(self.runQueryR(sqlBuyOrders))
        buyOrders  = map(lambda x: list(x), buyOrders)
        print "Done in %s. %d" % (self.qdt,len(buyOrders))

        print "Algorithm begin."
        deals = []
        log = []
        header = ["OrderID","TypeID","Price","Amount","","OrderID","TypeID","Price","Amount","RESULT"]
        log.append(header)

        while (len(sellOrders) and len(buyOrders)):
            so = sellOrders[0]
            bo = buyOrders[0]
            if (len(sellOrders) % 30 == 0):
                log.append(['','','','','','','','','',''])
                log.append(header)

            logE = [so[0],so[1],so[2],so[3],"",bo[0],bo[1],bo[2],bo[3]]

            if (so[1] < bo[1]):
                del sellOrders[0]
                res = "sItem < bItem"
                logE.append(res)
                log.append(logE)
                continue
            if (so[1] > bo[1]):
                del buyOrders[0]
                res = "sItem > bItem"
                logE.append(res)
                log.append(logE)
                continue

            profit = bo[2] - so[2]
            if (profit < so[2] * 0.05):
                del sellOrders[0]
                del buyOrders[0]
                res = "unprofitable"
                logE.append(res)
                log.append(logE)
                continue

            res = "OK!"
            logE.append(res)
            log.append(logE)

            amount = min(so[3], bo[3])
            tmp = so[3] - bo[3]
            if (tmp < 0):
                del sellOrders[0]
                bo[3] -= amount
            elif (tmp > 0):
                del buyOrders[0]
                so[3] -= amount
            else:
                del sellOrders[0]
                del buyOrders[0]

            # typeID, sellOrderID, buyOrderID, iSellSSID, iBuySSID, profit, amount
            myDeal = Deal([so[1],so[0],bo[0],bo[4],so[4],profit,amount],self)
            deals.append(myDeal)

            

        padnums.pprint_table(sys.stdout,log)
        print "Here we go, %d deals!" % len(deals)
        Deal.printDeals(deals)



# End Deals =========================================

# Solar Systems ==============================
    def getSSInfo(self,solarSystemID): # (Region, Name, Security)
        if solarSystemID in self.solarSystemsInfoCache:
            return self.solarSystemsInfoCache[solarSystemID]

        sqlQuery = "SELECT `regionName`, `solarSystemName`, `security` \
                    FROM `mapSolarSystems`, `mapRegions`\
                    WHERE ((`solarSystemID` = %d) && (`mapSolarSystems`.`regionID` = `mapRegions`.`regionID`))" % solarSystemID
        data = self.runQueryR(sqlQuery)
        data = arrayOpen(data)

        self.solarSystemsInfoCache[solarSystemID] = data
        return data

    def getSSsInfos(self,solarSystemIDs): # {SSID: (Region, Name, Security), ...}
        if containsAllKeys(self.solarSystemsInfoCache, solarSystemIDs):
            return selectByKeys(self.solarSystemsInfoCache, solarSystemIDs)

        sqlQuery = "SELECT `solarSystemID`, `regionName`, `solarSystemName`, `security` \
                    FROM `mapSolarSystems`, `mapRegions`\
                    WHERE ((`solarSystemID` IN (%s)) && (`mapSolarSystems`.`regionID` = `mapRegions`.`regionID`))" % solarSystemIDs
        data = self.runQueryR(sqlQuery)
        result = {}
        for x in data:
            result[x[0]] = (x[1],x[2],x[3])
        # self.solarSystemsInfoCache.update(result)
        return result
   
    def getSSAroundSS(self,solarSystemID,jumps):
        ss = self.getSSInfo(solarSystemID)

        color = 0
        if ss[2] > 0.5:
            color = 'green'   
        else:
            color = 'red'        
    
        ssRegion = colored(ss[0],color)
        ssName = colored(ss[1],color)
        ssSecruity = colored('%.1f' % ss[2], color)

        if (self.ssgraph):
            gr = self.ssgraph
        else:
            gr = graph()
            nodes = self.getAllSS()
            gr.add_nodes(nodes)
            for edge in self.getAllSSEdges():
                gr.add_edge(edge)

        print "Searching for Solar Systems around %s: %s(%s) in %d jumps." % (ssRegion, ssName, ssSecruity, jumps)

        ssinrad = breadth_first_search(gr,solarSystemID,radius(jumps))
        ssinrad = ssinrad[1]
        
        text = "Found %d systems" % len(ssinrad)
        text = colored(text, 'cyan')
        print "Done. %s, including current one." % text

        return ssinrad

    def getJumpsBetweenSS(self,ss1,ss2):
        if ss1 in self.jumpsCache:
            return self.jumpsCache[ss1][ss2]
        if ss2 in self.jumpsCache:
            return self.jumpsCache[ss2][ss1]

        gr = 0
        if (self.ssgraph):
            gr = self.ssgraph
        else:
            gr = graph()
            nodes = self.getAllSS()
            gr.add_nodes(nodes)
            for edge in self.getAllSSEdges():
                gr.add_edge(edge)
        
        paths = shortest_path(gr,ss1)[1]
        self.jumpsCache[ss1] = paths
        return paths[ss2]

    def getAllSS(self):
        sqlQuery = "SELECT `solarSystemID` FROM `mapSolarSystems`"
        result = self.runQueryR(sqlQuery)
        result = arrayOpen(result)
        return result

    def getAllSSEdges(self):
        sqlQuery = "SELECT `fromSolarSystemID`,`toSolarSystemID` FROM `mapSolarSystemJumps` WHERE `fromSolarSystemID`<`toSolarSystemID`" # for Google Graph
        result = self.runQueryR(sqlQuery)
        return result
# End Solar Systems ==========================

# Items ======================================

    def getTypeInfo(self,typeID): # (typeName,volume)
        if typeID in self.typeInfoCache:
            return self.typeInfoCache[typeID]

        sqlQuery = "SELECT `typeName`,`volume` FROM `invTypes` WHERE `typeID` = %d" % typeID
        result = self.runQueryR(sqlQuery)
        result = arrayOpen(result)

        self.typeInfoCache[typeID] = result
        return result

    def getTypesInfos(self,typeIDs): # {typeID:[typeName,volume]}
        sqlQuery = "SELECT `typeID`, `typeName`, `volume` FROM `invTypes` WHERE `typeID` IN (%s)" % arrayList(typeIDs)
        data = self.runQueryR(sqlQuery)
        return data 
