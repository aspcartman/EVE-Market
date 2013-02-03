import eve
import sys
from termcolor import colored, cprint
# import graphviz
# import networkx as nx
# import matplotlib.pyplot as plt

# Import pygraph
from pygraph.classes.graph import graph
from pygraph.classes.digraph import digraph
from pygraph.algorithms.searching import breadth_first_search
from pygraph.readwrite.dot import write

def main():
    db = eve.DatabaseDelegate()

    solarSystemID = 30000142
    money = 17020291.76
    volume = 5280.0
    typeID = 25603

    # solarSystemInfo = db.getSSInfo(solarSystemID)
    # print "Getting a list of urgent items for %s: %s (%.1f)" % (solarSystemInfo[0], solarSystemInfo[1], solarSystemInfo[2])
    # urgentTypesWithSS = db.getUrgentItemsWithSS(solarSystemID,10) # Urgent Items to buy in `solarSystemID` and sell somewhere in 10 jumps
    # urgentTypes = urgentTypesWithSS[0]
    # print "Got %d urgent items." % len(urgentTypes)
    # print "Now getting a sell orders in %s for all those items. It may take a while..." %  solarSystemInfo[1]
    # sellOrders = []
    # for urgent in urgentTypes:
    #     sellOrders += db.getSellOrdersInSSForItem(urgent,solarSystemID)
    # print len(db.getSSAroundSS(solarSystemID,10))
    # 
    
    db.getAllOrdersInRadius(solarSystemID,10)

    # G = nx.Graph()
    # G.add_nodes_from(db.getAllSS())
    # G.add_edges_from(db.getAllSSEdges())
    # print G.number_of_nodes()

    # nx.draw(G)
    # plt.savefig("path.png")

    # g = graph()
    # g.add_nodes_from(db.getAllSS)
    # g.add_edges_from(db.getAllSSEdges)

    # shortest_path(graph, solarSystemID)

    

    # text = colored('Hello, World!', 'red')
    # print(text)
    # cprint('Hello, World!', 'green', 'on_red')
    
    
if __name__ == '__main__':
    main()
  
   
  
  

