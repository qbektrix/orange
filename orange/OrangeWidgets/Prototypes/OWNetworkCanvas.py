CIRCLE=0
SQUARE=1
ROUND_RECT=2

NOTHING = 0
ZOOMING = 1
SELECT_RECTANGLE = 2
SELECT_POLYGON = 3
MOVE_SELECTION = 100

import copy

from OWGraph import *
from Numeric import *
from orngScaleScatterPlotData import *
from OWGraphTools import UnconnectedLinesCurve

class NetworkVertex():
  def __init__(self):
    self.index = -1
    self.marked = False
    self.show = True
    self.selected = False
    self.lebel = []
    self.tooltip = []
    
    self.pen = QPen(Qt.blue, 1)
    self.nocolor = Qt.white
    self.markColor = Qt.blue
    self.size = 5
    
class NetworkEdge():
  def __init__(self):
    self.u = None
    self.v = None
    self.arrowu = 0
    self.arrowv = 0
    
    self.pen = QPen(Qt.gray, 1)

class NetworkCurve(QwtPlotCurve):
  def __init__(self, parent, pen = QPen(Qt.black), xData = None, yData = None):
      QwtPlotCurve.__init__(self, "NetworkCurve")

      if xData != None and yData != None:
          self.setRawData(xData, yData)

      self.coors = None
      self.vertices = []
      self.edges = []
      self.setItemAttribute(QwtPlotItem.Legend, 0)

  def toPolar(self, x, y):
      if x > 0 and y >= 0:
          return math.atan(y/x)
      elif x > 0 and y < 0:
          return math.atan(y/x) + 2 * math.pi
      elif x < 0:
          return math.atan(y/x) + math.pi
      elif x == 0 and y > 0:
          return math.pi / 2
      elif x == 0 and y < 0:
          return math.pi * 3 / 2
      else:
          return None
      
  def moveSelectedVertices(self, dx, dy):
    for vertex in self.vertices:
      if vertex.selected:
        self.coors[0][vertex.index] = self.coors[0][vertex.index] + dx
        self.coors[1][vertex.index] = self.coors[1][vertex.index] + dy  
      
    self.setData(self.coors[0], self.coors[1])
  
  def getSelectedVertices(self):
    selection = []
    for vertex in self.vertices:  
      if vertex.selected:
        selection.append(vertex.index)
        
    return selection
  
  def draw(self, painter, xMap, yMap, rect):
    for edge in self.edges:
      if edge.u.show and edge.v.show:
        painter.setPen(edge.pen)

        px1 = xMap.transform(self.coors[0][edge.u.index])   #ali pa tudi self.x1, itd
        py1 = yMap.transform(self.coors[1][edge.u.index])
        px2 = xMap.transform(self.coors[0][edge.v.index])
        py2 = yMap.transform(self.coors[1][edge.v.index])
        
        painter.drawLine(px1, py1, px2, py2)
    
    for vertex in self.vertices:
      if vertex.show:
        pX = xMap.transform(self.coors[0][vertex.index])   #dobimo koordinati v pikslih (tipa integer)
        pY = yMap.transform(self.coors[1][vertex.index])   #ki se stejeta od zgornjega levega kota canvasa
        
        if vertex.selected:    
          painter.setPen(QPen(Qt.yellow, 3))
          painter.setBrush(vertex.markColor)
          painter.drawEllipse(pX - (vertex.size + 4) / 2, pY - (vertex.size + 4) / 2, vertex.size + 4, vertex.size + 4)
        elif vertex.marked:
          painter.setPen(vertex.pen)
          painter.setBrush(vertex.markColor)
          painter.drawEllipse(pX - vertex.size / 2, pY - vertex.size / 2, vertex.size, vertex.size)
        else:
          painter.setPen(vertex.pen)
          painter.setBrush(vertex.nocolor)
          painter.drawEllipse(pX - vertex.size / 2, pY - vertex.size / 2, vertex.size, vertex.size)
        
class OWNetworkCanvas(OWGraph):
  def __init__(self, master, parent = None, name = "None"):
      OWGraph.__init__(self, parent, name)
      self.master = master
      self.parent = parent
      self.labelText = []
      self.tooltipText = []
      self.vertices_old = {}         # distionary of nodes (orngIndex: vertex_objekt)
      self.edges_old = {}            # distionary of edges (curveKey: edge_objekt)
      self.vertices = []
      self.edges = []
      self.indexPairs = {}       # distionary of type CurveKey: orngIndex   (for nodes)
      #self.selection = []        # list of selected nodes (indices)
      self.selectionStyles = {}  # dictionary of styles of selected nodes
      self.markerKeys = {}       # dictionary of type NodeNdx : markerCurveKey
      self.tooltipKeys = {}      # dictionary of type NodeNdx : tooltipCurveKey
      self.colorIndex = -1
      self.visualizer = None
      self.selectedCurve = None
      self.selectedVertex = None
      self.vertexDegree = []     # seznam vozlisc oblike (vozlisce, stevilo povezav), sortiran po stevilu povezav
      self.edgesKey = -1
      #self.vertexSize = 6
      self.nVertices = 0
      self.enableXaxis(0)
      self.enableYLaxis(0)
      self.state = NOTHING  #default je rocno premikanje
      self.hiddenNodes = []
      self.markedNodes = set()
      self.markWithRed = False
      self.circles = []
      self.tooltipNeighbours = 2
      self.selectionNeighbours = 2
      self.freezeNeighbours = False
      self.labelsOnMarkedOnly = 0
      self.enableWheelZoom = 1
      self.smoothOptimization = 0
      self.optimizing = 0
      self.stopOptimizing = 0
      self.insideview = 0
      self.insideviewNeighbours = 2
      self.enableGridXB(False)
      self.enableGridYL(False)
    
      self.networkCurve = NetworkCurve(self)
      
  def getSelection(self):
    return self.networkCurve.getSelectedVertices()
      
  def getVertexSize(self, index):
      return 6
      
  def setHiddenNodes(self, nodes):
      self.hiddenNodes = nodes
      self.updateData()
      self.updateCanvas()
      
  def optimize(self, frSteps):
      qApp.processEvents()
      tolerance = 5
      initTemp = 100
      breakpoints = 20
      k = int(frSteps / breakpoints)
      o = frSteps % breakpoints
      iteration = 0
      coolFactor = exp(log(10.0/10000.0) / frSteps)
      #print coolFactor
      if k > 0:
          while iteration < breakpoints:
              initTemp = self.visualizer.fruchtermanReingold(k, initTemp, coolFactor, self.hiddenNodes)
              iteration += 1
              qApp.processEvents()
              self.updateCanvas()

          initTemp = self.visualizer.fruchtermanReingold(o, initTemp, coolFactor, self.hiddenNodes)
          qApp.processEvents()
          self.updateCanvas()
      else:
          while iteration < o:
              initTemp = self.visualizer.fruchtermanReingold(1, initTemp, coolFactor, self.hiddenNodes)
              iteration += 1
              qApp.processEvents()
              self.updateCanvas()
     
  def addSelection(self, ndx, replot = True):
      #print("add selection")
      change = False
      if hasattr(ndx, "__iter__"):
          for v in ndx:
              if not v in self.selection and not v in self.hiddenNodes:
                  (key, neighbours) = self.vertices_old[int(v)]
                  color = self.curve(key).symbol().pen().color().name()
                  self.selectionStyles[int(v)] = color
                  newSymbol = QwtSymbol(QwtSymbol.Ellipse, QBrush(QColor(self.selectionStyles[v])), QPen(Qt.yellow, 3), QSize(self.getVertexSize(v) + 4, self.vertexSize + 4))
                  self.setCurveSymbol(key, newSymbol)
                  self.selection.append(v);
                  change = True
      else:
          if not ndx in self.selection and not ndx in self.hiddenNodes:
              if self.insideview == 1:
                  self.removeSelection(None, False)
                  
              (key, neighbours) = self.vertices_old[ndx]
              color = self.curve(key).symbol().pen().color().name()
              self.selectionStyles[int(ndx)] = color
              newSymbol = QwtSymbol(QwtSymbol.Ellipse, QBrush(QColor(self.selectionStyles[ndx])), QPen(Qt.yellow, 3), QSize(self.getVertexSize(ndx) + 4, self.getVertexSize(ndx) + 4))
              self.setCurveSymbol(key, newSymbol)
              self.selection.append(ndx);
              #self.visualizer.filter[ndx] = True
              change = True
      if change:
          if replot:
              self.replot()
              
          self.markSelectionNeighbours()
      
      self.master.nSelected = len(self.selection)
      if self.insideview == 1:
          self.optimize(100)
          self.updateCanvas()
      return change
      
  def removeVertex(self, v):
      if v in self.selection:
          (key, neighbours) = self.vertices_old[v]
          newSymbol = QwtSymbol(QwtSymbol.Ellipse, QBrush(), QPen(QColor(self.selectionStyles[v])), QSize(self.getVertexSize(v), self.getVertexSize(v)))
          self.setCurveSymbol(key, newSymbol)
          selection.remove(v)
          del self.selectionStyles[v]
          return True
      return False
      
  def removeSelection(self, replot = True):
      print "remove selection"
      for vertex in self.vertices:
        vertex.selected = False
      
      if replot:
        self.replot()
      
  def selectConnectedNodes(self, distance):
      if distance <= 0:
          return
      
      #print "distance: " + str(distance)
      sel = set(self.selection)
      for v in self.selection:
          neighbours = set(self.visualizer.graph.getNeighbours(v))
          #print neighbours
          self.selectNeighbours(sel, neighbours - sel, 1, distance);
          
      self.removeSelection()
      for ndx in sel:
          (key, neighbours) = self.vertices_old[ndx]
          self.selectionStyles[ndx] = self.curve(key).symbol().brush().color().name()
          newSymbol = QwtSymbol(QwtSymbol.Ellipse, QBrush(QColor(self.selectionStyles[ndx])), QPen(Qt.yellow, 3), QSize(self.getVertexSize(ndx) + 4, self.getVertexSize(ndx) + 4))
          self.setCurveSymbol(key, newSymbol)
          self.selection.append(ndx);
      
      self.master.nSelected = len(self.selection)
      self.replot()
  
  def selectNeighbours(self, sel, nodes, depth, maxdepth):
      #print "list: " + str(sel)
      #print "nodes: " + str(nodes)
      sel.update(nodes)
      if depth < maxdepth:
          for i in nodes:
              neighbours = set(self.visualizer.graph.getNeighbours(i))
              #print "neighbours: " + str(neighbours)
              self.selectNeighbours(sel, neighbours - sel, depth+1, maxdepth)
      
  def getSelectedExamples(self):
      if len(self.selection) == 0:
          return None
      
      indeces = self.visualizer.nVertices() * [0]
      
      for v in self.selection:
          indeces[v] = v + 1

      if self.visualizer.graph.items != None:
          return self.visualizer.graph.items.select(indeces)
      else:
          return None

  def getSelectedGraph(self):
    if len(self.selection) == 0:
        return None
    
    graph = orange.GraphAsList(len(self.selection), 0)
    
    for e in range(self.nEdges):
        (key, i, j) = self.edges_old[e]
        
        if (i in self.selection) and (j in self.selection):
            graph[self.selection.index(i), self.selection.index(j)] = 1
    
    indeces = self.visualizer.nVertices() * [0]
    
    for v in self.selection:
        indeces[v] = v + 1

    if self.visualizer.graph.items != None:
        graph.setattr("items", self.visualizer.graph.items.select(indeces))
          
    return graph
 
  def moveVertex(self, pos):
        # ce ni nic izbrano
      if self.selectedCurve == None:
          return
      #curve = self.curve(self.vertices[self.selectedVertex])  #self.selectedCurve je key
      #newX = self.invTransform(curve.xAxis(), pos.x())
      #newY = self.invTransform(curve.yAxis(), pos.y())

      newX = self.invTransform(2, pos.x())
      newY = self.invTransform(0, pos.y())

      oldX = self.visualizer.coors[0][self.selectedVertex]
      oldY = self.visualizer.coors[1][self.selectedVertex]
      
      self.visualizer.coors[0][self.selectedVertex] = newX
      self.visualizer.coors[1][self.selectedVertex] = newY
      
      (key, neighbours) = self.vertices_old[self.selectedVertex]
      self.setCurveData(key, [newX], [newY])
      
      edgesCurve = self.curve(self.edgesKey)

      for e in neighbours:
          if (oldX == edgesCurve.xData[e*2]) and (oldY == edgesCurve.yData[e*2]):
              edgesCurve.xData[e*2] = newX
              edgesCurve.yData[e*2] = newY
          elif (oldX == edgesCurve.xData[e*2 + 1]) and (oldY == edgesCurve.yData[e*2 + 1]):
              edgesCurve.xData[e*2 + 1] = newX
              edgesCurve.yData[e*2 + 1] = newY
 
      self.setCurveData(self.edgesKey, edgesCurve.xData, edgesCurve.yData)
      
      if self.selectedVertex in self.markerKeys:
          mkey = self.markerKeys[self.selectedVertex]
          self.marker(mkey).setXValue(float(newX))
          self.marker(mkey).setYValue(float(newY))
          self.marker(mkey).setLabelAlignment(Qt.AlignCenter + Qt.AlignBottom)
      
      if self.selectedVertex in self.tooltipKeys:
          tkey = self.tooltipKeys[self.selectedVertex]
          self.tips.positions[tkey] = (newX, newY, 0, 0)
  
  def getNeighboursUpTo(self, ndx, dist):
      newNeighbours = neighbours = set([ndx])
      for d in range(dist):
          tNewNeighbours = set()
          for v in newNeighbours:
              tNewNeighbours |= set(self.visualizer.graph.getNeighbours(v))
          newNeighbours = tNewNeighbours - neighbours
          neighbours |= newNeighbours
      return neighbours
   
  def markSelectionNeighbours(self):
      if not self.freezeNeighbours and self.selectionNeighbours:
          toMark = set()
          for ndx in self.selection:
              toMark |= self.getNeighboursUpTo(ndx, self.selectionNeighbours)
          toMark -= set(self.selection)
          self.setMarkedNodes(toMark)
      
  def setMarkedNodes(self, marked):
      print "marking"
      if not isinstance(marked, set):
          marked = set(marked)
      if marked == self.markedNodes:
          return

      redColor = self.markWithRed and Qt.red
      # mark 
      for m in marked - self.markedNodes:
          (key, neighbours) = self.vertices_old[m]
          markedSize = self.markWithRed and self.getVertexSize(m) + 3 or self.getVertexSize(m)
          newSymbol = QwtSymbol(QwtSymbol.Ellipse, QBrush(redColor or self.nodeColor[m]), QPen(self.nodeColor[m]), QSize(markedSize, markedSize))
          self.setCurveSymbol(key, newSymbol)
#            self.curve(key).setBrush(QBrush(redColor or self.nodeColor[m]))
      # unmark
      for m in self.markedNodes - marked - set(self.selection):
          (key, neighbours) = self.vertices[m]
          newSymbol = QwtSymbol(QwtSymbol.Ellipse, QBrush(), QPen(self.nodeColor[m]), QSize(self.getVertexSize(m), self.getVertexSize(m)))
          self.setCurveSymbol(key, newSymbol)
  
      self.markedNodes = marked
      self.master.nMarked = len(self.markedNodes)
      self.drawLabels()
      self.replot()
      
  def activateMoveSelection(self):
      self.state = MOVE_SELECTION

  def mouseMoveEvent(self, event):
      if self.mouseCurrentlyPressed and self.state == MOVE_SELECTION:
          #if len(self.selection) > 0:
#              border = 6 / 2
#              maxx = max(take(self.visualizer.coors[0, :], self.selection))
#              maxy = max(take(self.visualizer.coors[1, :], self.selection))
#              minx = min(take(self.visualizer.coors[0, :], self.selection))
#              miny = min(take(self.visualizer.coors[1, :], self.selection))
#              #relativni premik v pikslih
#              dx = event.pos().x() - self.GMmouseStartEvent.x()
#              dy = event.pos().y() - self.GMmouseStartEvent.y()
#
#              maxx = self.transform(self.xBottom, maxx) + border + dx
#              maxy = self.transform(self.yLeft, maxy) + border + dy
#              minx = self.transform(self.xBottom, minx) - border + dx
#              miny = self.transform(self.yLeft, miny) - border + dy
#              maxx = self.invTransform(self.xBottom, maxx)
#              maxy = self.invTransform(self.yLeft, maxy)
#              minx = self.invTransform(self.xBottom, minx)
#              miny = self.invTransform(self.yLeft, miny)
#
#              if maxx >= self.axisScale(self.xBottom).hBound():
#                  return
#              if minx <= self.axisScale(self.xBottom).lBound():
#                  return
#              if maxy >= self.axisScale(self.yLeft).hBound():
#                  return
#              if miny <=self.axisScale(self.yLeft).lBound():
#                  return

#              for ind in self.selection:
#                  self.selectedVertex = ind
#                  (key, neighbours) = self.vertices_old[ind]
#                  self.selectedCurve = key
#
#                  vObj = self.curve(self.selectedCurve)
#                  tx = self.transform(vObj.xAxis(), vObj.x(0)) + dx
#                  ty = self.transform(vObj.yAxis(), vObj.y(0)) + dy
#                  
#                  tempPoint = QPoint(tx, ty)
#                  self.moveVertex(tempPoint)

              dx = self.invTransform(2, event.pos().x()) - self.invTransform(2, self.GMmouseStartEvent.x())
              dy = self.invTransform(0, event.pos().y()) - self.invTransform(0, self.GMmouseStartEvent.y())
              self.networkCurve.moveSelectedVertices(dx, dy)

              self.GMmouseStartEvent.setX(event.pos().x())  #zacetni dogodek postane trenutni
              self.GMmouseStartEvent.setY(event.pos().y())
              self.replot()
      else:
          OWGraph.mouseMoveEvent(self, event)
              
      if not self.freezeNeighbours and self.tooltipNeighbours:
          print "moving"
          px = self.invTransform(2, event.x())
          py = self.invTransform(0, event.y())   
          ndx, mind = self.visualizer.closestVertex(px, py)
          if ndx != -1 and mind < 50:
              toMark = set(self.getNeighboursUpTo(ndx, self.tooltipNeighbours))
              toMark -= set(self.selection)
              self.setMarkedNodes(toMark)
          else:
              self.setMarkedNodes([])
                     
      if self.smoothOptimization:
          px = self.invTransform(2, event.x())
          py = self.invTransform(0, event.y())   
          ndx, mind = self.visualizer.closestVertex(px, py)
          if ndx != -1 and mind < 30:
              if not self.optimizing:
                  self.optimizing = 1
                  initTemp = 1000
                  coolFactor = exp(log(10.0/10000.0) / 500)
                  from qt import qApp
                  for i in range(10):
                      if self.stopOptimizing:
                          self.stopOptimizing = 0
                          break
                      initTemp = self.visualizer.smoothFruchtermanReingold(ndx, 50, initTemp, coolFactor)
                      qApp.processEvents()
                      self.updateData()
                      self.replot()
                  
                  self.optimizing = 0
          else:
              self.stopOptimizing = 1

  def mousePressEvent(self, event):
    if self.state == MOVE_SELECTION:
      self.mouseCurrentlyPressed = 1
      if self.isPointSelected(self.invTransform(self.xBottom, event.pos().x()), self.invTransform(self.yLeft, event.pos().y())) and self.selection != []:
        self.GMmouseStartEvent = QPoint(event.pos().x(), event.pos().y())
      else:
        #pritisk na gumb izven izbranega podrocja ali pa ni izbranega podrocja
        self.selectVertex(event.pos())
        self.GMmouseStartEvent = QPoint(event.pos().x(), event.pos().y())
        self.replot()

    else:
        OWGraph.mousePressEvent(self, event)     

  def mouseReleaseEvent(self, event):  
      if self.state == MOVE_SELECTION:
          self.mouseCurrentlyPressed = 0
          
          self.selectedCurve= None
          self.selectedVertex=None
          self.moveGroup=False
          #self.selectedVertices=[]
          self.GMmouseStartEvent=None
          
      elif self.state == SELECT_RECTANGLE:
          self.selectVertices()
          OWGraph.mouseReleaseEvent(self, event)
          self.removeAllSelections()

      elif self.state == SELECT_POLYGON:
              OWGraph.mouseReleaseEvent(self, event)
              if self.tempSelectionCurve == None:   #ce je OWVisGraph zakljucil poligon
                  self.selectVertices()
      else:
          OWGraph.mouseReleaseEvent(self, event)
      
  def selectVertices(self):
      #print "selecting vertices.."
      for vertexKey in self.indexPairs.keys():
          vObj = self.curve(vertexKey)
          
          if self.isPointSelected(vObj.x(0), vObj.y(0)):
              self.addSelection(self.indexPairs[vertexKey], False)
              
      self.replot()
              
  def selectVertex(self, pos):
      min = 1000000
      ndx = -1

      px = self.invTransform(2, pos.x())
      py = self.invTransform(0, pos.y())   

      ndx, min = self.visualizer.closestVertex(px, py)

      if min < 50 and ndx != -1:
          self.vertices[ndx].selected = True
      else:
          self.removeSelection()
              
  def dist(self, s1, s2):
      return math.sqrt((s1[0]-s2[0])**2 + (s1[1]-s2[1])**2)
  
  def updateData(self):
      #print "OWGraphDrawerCanvas/updateData..."
      self.removeDrawingCurves(removeLegendItems = 0)
      self.tips.removeAll()
      
      self.networkCurve.setData(self.visualizer.coors[0], self.visualizer.coors[1])
      
      if self.insideview and len(self.selection) == 1:
          visible = set()
          visible |= set(self.selection)
          visible |= self.getNeighboursUpTo(self.selection[0], self.insideviewNeighbours)
          self.hiddenNodes = set(range(self.nVertices)) - visible

      edgesCount = 0
      
      for r in self.circles:
          print "r: " + str(r)
          step = 2 * pi / 64;
          fi = 0
          x = []
          y = []
          for i in range(65):
              x.append(r * cos(fi) + 5000)
              y.append(r * sin(fi) + 5000)
              fi += step
              
          self.addCurve("radius", Qt.white, Qt.green, 1, style = QwtPlotCurve.Lines, xData = x, yData = y, showFilledSymbols = False)
      
      self.networkCurve.attach(self)
      self.drawLabels()
      self.drawToolTips()
      
#      xData = []
#      yData = []
      # draw edges
#      for e in range(self.nEdges):
#          (key, i, j) = self.edges[e]
#          
#          if i in self.hiddenNodes or j in self.hiddenNodes:
#              continue  
#          
#          x1 = self.visualizer.coors[0][i]
#          x2 = self.visualizer.coors[0][j]
#          y1 = self.visualizer.coors[1][i]
#          y2 = self.visualizer.coors[1][j]
#
#          #key = self.addCurve(str(e), fillColor, edgeColor, 0, style = QwtCurve.Lines, xData = [x1, x2], yData = [y1, y2])
#          #self.edges[e] = (key,i,j)
#          xData.append(x1)
#          xData.append(x2)
#          yData.append(y1)
#          yData.append(y2)
#          # append edges to vertex descriptions
#          self.edges[e] = (edgesCount, i, j)
#          (key, neighbours) = self.vertices[i]
#          if edgesCount not in neighbours:
#              neighbours.append(edgesCount)
#          self.vertices[i] = (key, neighbours)
#          (key, neighbours) = self.vertices[j]
#          if edgesCount not in neighbours:
#              neighbours.append(edgesCount)
#          self.vertices[j] = (key, neighbours)
#          
#          edgesCount += 1
#      
#      edgesCurveObject = UnconnectedLinesCurve(self, QPen(QColor(192, 192, 192)), xData, yData)
#      edgesCurveObject.xData = xData
#      edgesCurveObject.yData = yData
#      self.edgesKey = self.insertCurve(edgesCurveObject)
#      
#      selectionX = []
#      selectionY = []
#      self.nodeColor = []
#
#      # draw vertices
#      for v in range(self.nVertices):
#          if self.colorIndex > -1:
#              if self.visualizer.graph.items.domain[self.colorIndex].varType == orange.VarTypes.Continuous:
#                  newColor = self.contPalette[self.noJitteringScaledData[self.colorIndex][v]]
#                  fillColor = newColor
#              elif self.visualizer.graph.items.domain[self.colorIndex].varType == orange.VarTypes.Discrete:
#                  newColor = self.discPalette[self.colorIndices[self.visualizer.graph.items[v][self.colorIndex].value]]
#                  fillColor = newColor
#                  edgeColor = newColor
#          else: 
#              newcolor = Qt.blue
#              fillColor = newcolor
#              
#          if self.insideview and len(self.selection) == 1:
#                  if not (v in self.visualizer.graph.getNeighbours(self.selection[0]) or v == self.selection[0]):
#                      fillColor = fillColor.light(155)
#          
#          # This works only if there are no hidden vertices!    
#          self.nodeColor.append(fillColor)
#          
#          if v in self.hiddenNodes:
#              continue
#                  
#          x1 = self.visualizer.coors[0][v]
#          y1 = self.visualizer.coors[1][v]
#          
#          selectionX.append(x1)
#          selectionY.append(y1)
#          key = self.addCurve(str(v), fillColor, edgeColor, self.getVertexSize(v), xData = [x1], yData = [y1], showFilledSymbols = False)
#          
#          if v in self.selection:
#              if self.insideview and len(self.selection) == 1:
#                  self.selectionStyles[v] = str(newcolor.name())
#                  
#              selColor = QColor(self.selectionStyles[v])
#              newSymbol = QwtSymbol(QwtSymbol.Ellipse, QBrush(selColor), QPen(Qt.yellow, 3), QSize(self.getVertexSize(v) + 4, self.getVertexSize(v) + 4))
#              self.setCurveSymbol(key, newSymbol)
#          
#          (tmp, neighbours) = self.vertices[v]
#          self.vertices[v] = (key, neighbours)
#          self.indexPairs[key] = v
#      
#      #self.addCurve('vertices', fillColor, edgeColor, 6, xData=selectionX, yData=selectionY)
#      
#      # mark nodes
#      redColor = self.markWithRed and Qt.red
#      
#      for m in self.markedNodes:
#          (key, neighbours) = self.vertices[m]
#          markedSize = self.markWithRed and self.getVertexSize(v) + 3 or self.getVertexSize(v)
#          newSymbol = QwtSymbol(QwtSymbol.Ellipse, QBrush(redColor or self.nodeColor[m]), QPen(self.nodeColor[m]), QSize(markedSize, markedSize))
#          self.setCurveSymbol(key, newSymbol)        
#      

  def drawToolTips(self):
    # add ToolTips
    self.tooltipData = []
    self.tooltipKeys = {}
    self.tips.removeAll()
    if len(self.tooltipText) > 0:
      for vertex in self.vertices:
        if not vertex.show:
          continue
        
        x1 = self.visualizer.coors[0][vertex.index]
        y1 = self.visualizer.coors[1][vertex.index]
        lbl = ""
        for ndx in self.tooltipText:
          values = self.visualizer.graph.items[vertex.index]
          lbl = lbl + str(values[ndx]) + "\n"
  
        if lbl != '':
          lbl = lbl[:-1]
          self.tips.addToolTip(x1, y1, lbl)
          self.tooltipKeys[vertex.index] = len(self.tips.texts) - 1
                 
  def drawLabels(self):
      self.removeMarkers()
      self.markerKeys = {}
      if len(self.labelText) > 0:
          for vertex in self.vertices:
              if not vertex.show:
                  continue
              
              if self.labelsOnMarkedOnly and not (vertex.marked):
                  continue
                                
              x1 = self.visualizer.coors[0][vertex.index]
              y1 = self.visualizer.coors[1][vertex.index]
              lbl = ""
              values = self.visualizer.graph.items[vertex.index]
              lbl = " ".join([str(values[ndx]) for ndx in self.labelText])
              if lbl:
                  mkey = self.addMarker(lbl, float(x1), float(y1), alignment = Qt.AlignBottom)
                  self.markerKeys[vertex.index] = mkey     
          
  def setVertexColor(self, attribute):
      if attribute == "(one color)":
          self.colorIndex = -1
      else:
          i = 0
          for var in self.visualizer.graph.items.domain.variables:
              if var.name == attribute:
                  self.colorIndex = i
                  if var.varType == orange.VarTypes.Discrete: 
                      self.colorIndices = getVariableValueIndices(self.visualizer.graph.items, self.colorIndex)
              i += 1
      pass
      
  def setLabelText(self, attributes):
      self.labelText = []
      if isinstance(self.visualizer.graph.items, orange.ExampleTable):
          data = self.visualizer.graph.items
          for att in attributes:
              for i in range(len(data.domain)):
                  if data.domain[i].name == att:
                      self.labelText.append(i)
                      
              if self.visualizer.graph.items.domain.hasmeta(att):
                      self.labelText.append(self.visualizer.graph.items.domain.metaid(att))
  
  def setTooltipText(self, attributes):
      self.tooltipText = []
      if isinstance(self.visualizer.graph.items, orange.ExampleTable):
          data = self.visualizer.graph.items
          for att in attributes:
              for i in range(len(data.domain)):
                  if data.domain[i].name == att:
                      self.tooltipText.append(i)
                      
              if self.visualizer.graph.items.domain.hasmeta(att):
                      self.tooltipText.append(self.visualizer.graph.items.domain.metaid(att))
      
  def edgesContainsEdge(self, i, j):
      for e in range(self.nEdges):
          (key, iTmp, jTmp) = self.edges_old[e]
          
          if (iTmp == i and jTmp == j) or (iTmp == j and jTmp == i):
              return True
      return False
      
  def addVisualizer(self, visualizer):
      self.visualizer = visualizer
      self.clear()
      
      self.nVertices = visualizer.graph.nVertices
      self.nEdges = 0
      self.vertexDegree = []
      
      #dodajanje vozlisc
      #print "OWNeteorkCanvas/addVisualizer: adding vertices..."
      self.vertices_old = {}
      self.vertices = []
      for v in range(0, self.nVertices):
          self.vertices_old[v] = (None, [])
          vertex = NetworkVertex()
          vertex.index = v
          self.vertices.append(vertex)
      #print "done."
      
      #dodajanje povezav
      #print "OWNeteorkCanvas/addVisualizer: adding edges..."
      self.edges_old = {}
      self.nEdges = 0
      
      self.edges = []
      for (i, j) in visualizer.graph.getEdges():
          self.edges_old[self.nEdges] = (None, i, j)
          edge = NetworkEdge()
          edge.u = self.vertices[i]
          edge.v = self.vertices[j]
          self.edges.append(edge)
          self.nEdges += 1
          
      self.networkCurve.setData(visualizer.coors[0], visualizer.coors[1])
      self.networkCurve.coors = visualizer.coors
      self.networkCurve.vertices = self.vertices
      self.networkCurve.edges = self.edges
  
  def updateCanvas(self):
      self.setAxisAutoScaled()
      self.updateData()
      self.replot()
      # preprecimo avtomatsko primikanje plota (kadar smo odmaknili neko skrajno tocko)
      self.setAxisFixedScale()    
  
  def setAxisAutoScaled(self):
      self.setAxisAutoScale(self.xBottom)
      self.setAxisAutoScale(self.yLeft)

  def setAxisFixedScale(self):
      #self.setAxisScale(self.xBottom, self.axisScale(self.xBottom).lBound(), self.axisScale(self.xBottom).hBound())
      #self.setAxisScale(self.yLeft, self.axisScale(self.yLeft).lBound(), self.axisScale(self.yLeft).hBound())
      pass
      
  def sendData(self):
      try:
          getattr(self.master, "sendData")()
      except AttributeError:
          print "Attribute not foud in self.master"
  
  def zoomExtent(self):
      self.setAxisAutoScaled()
      self.replot()
      self.setAxisFixedScale()
      
  def zoomSelection(self):       
      selection = self.networkCurve.getSelectedVertices()
      if len(selection) > 0: 
          x = [self.visualizer.coors[0][v] for v in selection]
          y = [self.visualizer.coors[1][v] for v in selection]

          oldXMin = self.axisScaleDiv(QwtPlot.xBottom).lBound()
          oldXMax = self.axisScaleDiv(QwtPlot.xBottom).hBound()
          oldYMin = self.axisScaleDiv(QwtPlot.yLeft).lBound()
          oldYMax = self.axisScaleDiv(QwtPlot.yLeft).hBound()
          newXMin = min(x)
          newXMax = max(x)
          newYMin = min(y)
          newYMax = max(y)
          self.zoomStack.append((oldXMin, oldXMax, oldYMin, oldYMax))
          self.setAxisScale(QwtPlot.xBottom, newXMin - 100, newXMax + 100)
          self.setAxisScale(QwtPlot.yLeft, newYMin - 100, newYMax + 100)
          self.replot()
                  