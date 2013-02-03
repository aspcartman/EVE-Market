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

def colorRate(rate):
        if rate > 0.5:
            return 'green'   
        else:  
             return 'red'


class Deal(object):
    typeID = 0
    profit = 0
    buyPrice = 0
    buySystem = 0
    sellSystem = 0
    volume = 0
    rang = 1

    typeInfo = 0
    buySSInfo = 0
    sellSSInfo = 0

    def __init__(self,array,db): # typeID, profit, minPrice, startSS, stopSS
        self.typeID = array[0]
        self.profit = array[1]
        self.buyPrice = array[2]
        self.buySystem = array[3]
        self.sellSystem = array[4]
        self.volume = db.getTypeInfo(self.typeID)[1]

        self.typeInfo = db.getTypeInfo(self.typeID)
        self.buySSInfo = db.getSSInfo(self.buySystem)
        self.sellSSInfo = db.getSSInfo(self.sellSystem)

    def __str__(self):
        return '%d \t %s (%d m3) \t %dISK : %dISK \t %s(%.1f) ----> %s(%.1f) \t (DUNNO jumps)'\
        % (self.typeID, self.typeInfo[0], self.typeInfo[1], self.buyPrice, self.profit, self.buySSInfo[1], self.buySSInfo[2], self.sellSSInfo[1], self.sellSSInfo[2])

    def desc(self):
        return (self.typeID, self.typeInfo[0], self.typeInfo[1], self.buyPrice, self.profit, self.buySSInfo[1], self.buySSInfo[2], self.sellSSInfo[1], self.sellSSInfo[2])


class DatabaseDelegate(object):
    cursor = object()
    qdt = 0 # Last query dt
    ssgraph = 0 # Solar System Graph

    solarSystemsInfoCache = {}
    typeInfoCache = {}
    jumpsCache = {}

    def __init__(self):
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

# Orders =========================================

    def getBuyOrdersAroundSSForItem(self,typeID,solarSystemID): #Founds every buy order around a solarSystem
        sqlQuery = "SELECT `orderID`,`price`,`solarSystemID` FROM  `emdrOrders` WHERE (`typeID` = %d && `solarSystemID` != %d && `bid` = 1) ORDER BY `price` DESC" % (typeID,solarSystemID)
        data = self.runQueryR(sqlQuery)
        return data

    def getBuyOrdersInSSForItem(self,typeID,solarSystemID): #Founds every buy order in a solarSystem
        sqlQuery = "SELECT `orderID`,`price`,`solarSystemID` FROM  `emdrOrders` WHERE (`typeID` = %d && `solarSystemID`  = %d && `bid` = 1) ORDER BY `price` DESC" % (typeID,solarSystemID)
        data = self.runQueryR(sqlQuery)
        return data

    def getSellOrdersAroundSSForItem(self,typeID,solarSystemID): #Founds every sell order around a solarSystem
        sqlQuery = "SELECT `orderID`,`price`,`solarSystemID` FROM  `emdrOrders` WHERE (`typeID` = %d && `solarSystemID` != %d && `bid` = 0) ORDER BY `price`" % (typeID,solarSystemID)
        data = self.runQueryR(sqlQuery)
        return data

    def getSellOrdersInSSForItem(self,typeID,solarSystemID): #Founds every sell order in a solarSystem
        sqlQuery = "SELECT `orderID`,`price`,`solarSystemID` FROM  `emdrOrders` WHERE (`typeID` = %d && `solarSystemID`  = %d && `bid` = 0) ORDER BY `price`" % (typeID,solarSystemID)
        data = self.runQueryR(sqlQuery)
        return data

    def getAllOrdersInRadius(self,solarSystemID,radius): # Returns ( (typeID, profit, buyPrice, buySolarSystem, sellSolarSystem), ... )
        self.removeOldRows()
        solarSystems = arrayList(self.getSSAroundSS(solarSystemID,radius))

        print "Searching for Max buy orders (to which we'll sell) in those systems. It may take a while..."
        sqlQuery_forBuy = "CREATE TEMPORARY TABLE buyOrders AS (SELECT `orderID`, `typeID`, MAX(`price`) AS `maxPrice`, `solarSystemID` AS `endSolarSystem`\
                            FROM `emdrOrders`\
                            WHERE (`solarSystemID` IN (%s) && `BID` = 1)\
                            GROUP BY `typeID`, `endSolarSystem`)" % solarSystems
        sqlQuery_forCountInBuy = "SELECT Count(*) FROM buyOrders"
        self.runQueryR(sqlQuery_forBuy)

        text = "Found %d buy orders." %  self.runQueryR(sqlQuery_forCountInBuy)[0][0]
        text = colored(text, 'cyan')
        print "Done %s. %s" % ( self.qdt, text)

        print "Searching for Min sell orders (which we are going to buy) in those systems. It may take a while..."
        sqlQuery_forSell = "CREATE TEMPORARY TABLE sellOrders AS (SELECT `orderID`, `typeID`, MIN(`price`) AS `minPrice`, `solarSystemID` AS `startSolarSystem`\
                            FROM `emdrOrders`\
                            WHERE (`solarSystemID` IN (%s) && `BID` = 0)\
                            GROUP BY `typeID`, `startSolarSystem`)" % solarSystems
        sqlQuery_forCountInSell = "SELECT Count(*) FROM sellOrders"
        self.runQueryR(sqlQuery_forSell)

        text = "Found %d sell orders." %  self.runQueryR(sqlQuery_forCountInSell)[0][0]
        text = colored(text, 'cyan')
        print "Done %s. %s" % ( self.qdt, text)

        print "Generating profitable deals from this orders." 
        sqlQuery_forDeals = "SELECT `buyOrders`.`typeID`, SUM(`maxPrice` - `minPrice`) AS `profit`,`minPrice`, `startSolarSystem`,`endSolarSystem` \
                    FROM   `buyOrders`,`sellOrders`\
                    WHERE  `buyOrders`.`typeID` = `sellOrders`.`typeID`\
                    GROUP BY `typeID`,`startSolarSystem`,`endSolarSystem`\
                    HAVING SUM(`maxPrice` - `minPrice`) > 0.025 * SUM(`minPrice`) && SUM(`maxPrice` - `minPrice`) > 100" # May be we don't need second statement
        deals = self.runQueryR(sqlQuery_forDeals)

        text = "Got %d profitable deals!" % len(deals)
        text = colored(text, 'cyan')
        print "Done %s. %s" % (self.qdt, text)

        print "Droping temporary tables."
        sqlQuery_forDrop = "DROP TABLE buyOrders,sellOrders"
        self.runQueryR(sqlQuery_forDrop)
        print "Done %s." % ( self.qdt )
        
        print "Generating actual deals."
        dt = clock()
        actualDeals = []
        for x in deals:
            actualDeals.append(Deal(x,self))
        dt = clock() - dt
        print "Done %s." % dt



        '%d \t %s (%d m3) \t %dISK : %dISK \t %s(%.1f) ----> %s(%.1f) \t (DUNNO jumps)'
        table = Texttable()
        table.set_deco(Texttable.HEADER)
        table.set_cols_align(["r", "l", "c", "r", "r", "l", "l", "r"])
        table.set_cols_width([6,53,12,12,12,45,45,2])
        table.add_row(['TypeID','Name', 'Volume', 'Buy Price (ISK)', 'Profit (ISK)', 'Buy SS', 'Sell SS', 'J'])
        table.set_cols_dtype(["t", "t", "t", "t", "t", "t", "t", "t"])
        for x in actualDeals:
            buyColor = colorRate(x.buySSInfo[2])   
            buyText = '%s:%s (%.1f)' % (x.buySSInfo[0], x.buySSInfo[1], x.buySSInfo[2])
            buyText = colored(buyText, buyColor)

            sellColor = colorRate(x.sellSSInfo[2])   
            sellText = '%s:%s (%.1f)' % (x.sellSSInfo[0], x.sellSSInfo[1], x.sellSSInfo[2])
            sellText = colored(sellText, sellColor)

            sTypeID = x.typeID
            sTypeName = x.typeInfo[0]
            sTypeVol = '%10.2f' % x.typeInfo[1]
            sBuyPrice = '%d' % x.buyPrice
            sProfit = '%d' % x.profit
            sBuySS = '%s' % buyText
            sSellSS = '%s' % sellText
            sJump = '%d' % self.getJumpsBetweenSS(x.buySystem,x.sellSystem)
            table.add_row([sTypeID, sTypeName, sTypeVol, sBuyPrice, sProfit, sBuySS, sSellSS, sJump])

        print table.draw()

# End Orders =========================================

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

    # Get all items, that has sell orders in current SS and buy surrounding ones
    def getUrgentItems(self,solarSystemID,jumps):
        ssAround = self.getSSAroundSS(solarSystemID,jumps)
        #Should return all 
        sqlQuery = "(SELECT DISTINCT `typeID` FROM `emdrOrders` WHERE (`typeID` IN \
                    (SELECT DISTINCT `typeID` FROM `emdrOrders` WHERE (`solarSystemID` = %d && `BID` = 0))) AND (`solarSystemID` IN (%s) && `BID` = 1))"\
                        % (solarSystemID,arrayList(ssAround))
        data = self.runQueryR(sqlQuery)
        data = arrayOpen(data)
        return data

    def getUrgentItemsWithSS(self,solarSystemID,jumps): # returns [(unicue typeIDs), (typeID, ssID), (typeID, ssID), ...]
        ssAround = self.getSSAroundSS(solarSystemID,jumps)
        #Should return all 
        sqlQuery = "(SELECT DISTINCT `typeID`,`solarSystemID` FROM `emdrOrders` WHERE (`typeID` IN \
                    (SELECT DISTINCT `typeID` FROM `emdrOrders` WHERE (`solarSystemID` = %d && `BID` = 0))) AND (`solarSystemID` IN (%s) && `BID` = 1))"\
                        % (solarSystemID,arrayList(ssAround))
        data = self.runQueryR(sqlQuery)
        # [(typeID, typeID, ...), (typeID,solarSystemID), (typeID,solarSystemID), (typeID,solarSystemID) ...]
        types = []
        for element in data:
            typeID = element[0]
            if typeID not in types:
                types.append(typeID)
        data.insert(0,types)
        return data


    def getItemsNames(self,itemTypeIDs):
        sqlQuery = "SELECT `typeID`,`typeName` FROM `invTypes` WHERE `typeID` IN (%s)" % arrayList(itemTypeIDs)
        data = self.runQueryR(sqlQuery)
        return data

    def maxProfit1Item(self,typeID,buySS,sellSS):
        sellOrders = self.getSellOrdersInSSForItem(typeID,buySS)
        buyOrders = self.getBuyOrdersInSSForItem(typeID,sellSS)
        return buyOrders[0][1] - sellOrders[0][1]

        