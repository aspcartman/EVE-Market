class Order:
    typeID = 0
    price = 0
    volRemaining = 0
    orderRange = 0
    orderID = 0
    volEntered = 0
    minVolume = 0
    bid = 0
    issueDate = 0
    duration = 0
    stationID = 0
    solarSystemID = 0
    dateAdded = 0
    generatedAt = 0
    regionID = 0

    def __init__(self,init_array):
        self.typeID = init_array[0]
        self.price = init_array[1]
        self.volRemaining = init_array[2]
        self.orderRange = init_array[3]
        self.orderID = init_array[4]
        self.volEntered = init_array[5]
        self.minVolume = init_array[6]
        self.bid = init_array[7]
        self.issueDate = init_array[8]
        self.duration = init_array[9]
        self.stationID = init_array[10]
        self.solarSystemID = init_array[11]
        self.dateAdded = init_array[12]
        self.generatedAt = init_array[13]
        self.regionID = init_array[14]
    def __str__(self):
        orderType = 'Sell'
        if (self.bid):
            orderType = 'Buy'
        return '%s order %d for %d item in %d system: %d ISK' % (orderType,self.orderID,self.typeID,self.solarSystemID,self.price)