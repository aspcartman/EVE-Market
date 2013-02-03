import MySQLdb
import sys
from termcolor import colored, cprint

# Import pygraph
from pygraph.classes.graph import graph
from pygraph.algorithms.filters.radius import radius
from pygraph.algorithms.searching import breadth_first_search

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

class Deal(object):
    typeID = 0
    profit = 0
    buyPrice = 0
    buySystem = 0
    sellSystem = 0
    volume = 0
    name = ''
    rang = 1

    def __init__(self,array,db):
        self.typeID = array[0]
        self.profit = array[1]
        self.buyPrice = array[2]
        self.buySystem = array[3]
        self.sellSystem = array[4]

        buySSInfo = db.getSSInfo(self.buySystem)
        sellSSInfo = db.getSSInfo(self.sellSystem)
        typeInfo = db.getTypeInfo(self.typeID)



    def __str__(self):
        return '%d\t%s (%dm3) \t %dISK : %dISK \t ' % (self.typeID, self.name, self.volume,self.buy, self.profit )


class DatabaseDelegate(object):
    cursor = object()
    qdt = 0 # Last query completion time

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
        sqlQuery_forDeals = "CREATE TEMPORARY TABLE deals AS (SELECT `buyOrders`.`typeID`, SUM(`maxPrice` - `minPrice`) AS `profit`,`minPrice`, `startSolarSystem`,`endSolarSystem` \
                    FROM   `buyOrders`,`sellOrders`\
                    WHERE  `buyOrders`.`typeID` = `sellOrders`.`typeID`\
                    GROUP BY `typeID`,`startSolarSystem`,`endSolarSystem`\
                    HAVING SUM(`maxPrice` - `minPrice`) > 0.025 * SUM(`minPrice`) && SUM(`maxPrice` - `minPrice`) > 100)" # May be we don't need second statement
        result = self.runQueryR(sqlQuery_forDeals)
        print "Done %s." % ( self.qdt )

        print "Reading SQL data..."
        sqlQuery_forDeals = "SELECT * FROM `deals`"
        deals = self.runQueryR(sqlQuery_forDeals)

        text = "Got %d profitable deals!" % len(deals)
        text = colored(text, 'cyan')
        print "Done %s. %s" % (self.qdt, text)

        print "Getting distinct types."
        sqlQuery_forTypes = "SELECT DISTINCT `typeID` FROM `deals`"
        typeIDs = self.runQueryR(sqlQuery_forTypes)
        typeIDs = arrayOpen(typeIDs)
        print "Done %s. Got %d types." % ( self.qdt, len(typeIDs) )
        
        print "Droping temporary tables."
        sqlQuery_forDrop = "DROP TABLE buyOrders,sellOrders,deals"
        self.runQueryR(sqlQuery_forDrop)
        print "Done %s." % ( self.qdt )

        print "Fetching good's info"
        typesInfo = self.getTypesInfos(typeIDs)
        print "Done."

        print "Fetching solarsystem's info"
        solarSystemsInfo = self.getSSsInfos(solarSystems)
        printByLineD(solarSystemsInfo)
        return result
        

# End Orders =========================================

# Solar Systems ==============================
    def getSSInfo(self,solarSystemID): # (Region, Name, Security)
        sqlQuery = "SELECT `regionName`, `solarSystemName`, `security` \
                    FROM `mapSolarSystems`, `mapRegions`\
                    WHERE ((`solarSystemID` = %d) && (`mapSolarSystems`.`regionID` = `mapRegions`.`regionID`))" % solarSystemID
        data = self.runQueryR(sqlQuery)
        data = arrayOpen(data)
        return data

    def getSSsInfos(self,solarSystemIDs): # {SSID: (Region, Name, Security), ...}
        sqlQuery = "SELECT `solarSystemID`, `regionName`, `solarSystemName`, `security` \
                    FROM `mapSolarSystems`, `mapRegions`\
                    WHERE ((`solarSystemID` IN (%s)) && (`mapSolarSystems`.`regionID` = `mapRegions`.`regionID`))" % solarSystemIDs
        data = self.runQueryR(sqlQuery)
        result = {}
        for x in data:
            result[x[0]] = (x[1],x[2],x[3])

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

        print "Searching for Solar Systems around %s: %s(%s) in %d jumps." % (ssRegion, ssName, ssSecruity, jumps)
        nodes = self.getAllSS()
        gr = graph()
        gr.add_nodes(nodes)
        for edge in self.getAllSSEdges():
            gr.add_edge(edge)
        ssinrad = breadth_first_search(gr,solarSystemID,radius(jumps))
        ssinrad = ssinrad[1]
        
        text = "Found %d systems" % len(ssinrad)
        text = colored(text, 'cyan')
        print "Done. %s, including current one." % text

        return ssinrad

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

    def getTypeInfo(self,typeID):
        sqlQuery = "SELECT `typeName`,`volume` FROM `invTypes` WHERE `typeID` = %d" % typeID
        result = self.runQueryR(sqlQuery)
        result = arrayOpen(result)
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

        