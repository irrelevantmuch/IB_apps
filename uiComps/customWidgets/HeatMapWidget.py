import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSlider
from PyQt5.QtCore import Qt

class RotatedAxisItem(pg.AxisItem):
    def drawPicture(self, p, axisSpec, tickSpecs, textSpecs):
        p.setRenderHint(p.Antialiasing, False)
        p.setRenderHint(p.TextAntialiasing, True)
        
            # Set pen color
        p.setPen(pg.mkPen('k'))  # 'k' stands for black color


        # Draw all text and tick marks directly to the picture.
        for rect, flags, text in textSpecs:
            p.save()  # Save painter state
            #p.translate(x, y)  # Move painter to start of text
            p.translate(rect.center())
            p.rotate(-45)  # Rotate painter (this is the rotation)
            p.drawText(-rect.width() / 2, rect.height() / 2, text)  # Draw text at new position
            p.restore()  # Restore painter state

        for pen, p1, p2 in tickSpecs:
            p.setPen(pen)
            p.drawLine(p1, p2)


class HeatMapWidget(QWidget):
    def __init__(self, parent=None):
        super(HeatMapWidget, self).__init__(parent)

        # Initialize pyqtgraph configuration
        pg.setConfigOptions(antialias=True)

        # Create layout
        self.layout = QVBoxLayout(self)
        self.h_layout = QHBoxLayout()  # New horizontal layout for the plot and the vertical slider
        

        # Create GraphicsLayoutWidget
        self.win = pg.GraphicsLayoutWidget()

        # Add GraphicsLayoutWidget to the layout
        self.h_layout.addWidget(self.win)

        # # Generate some example data
        # self.data = np.array([np.random.random(10) for i in range(5_000)])

        # Create a sequential heatmap
        self.heatmap = pg.ImageItem()

        # ## Create a color map
        # colors = [(255, 255, 255), (0, 0, 255), (0, 255, 0), (255, 255, 0), (255, 0, 0)]
        # cmap = pg.ColorMap(pos=np.arange(0, 5), color=colors)
        # self.heatmap.setLookupTable(cmap.getLookupTable())



        # Define the color map
        colors = [(0, QtGui.QColor('white')),
                  (1, QtGui.QColor('red')),
                  (2, QtGui.QColor('green'))] #,
                  # (3, QtGui.QColor('orange')),
                  # (4, QtGui.QColor('blue'))]
        cmap = pg.ColorMap(pos=[c[0] for c in colors], color=[c[1] for c in colors])
        lut = cmap.getLookupTable(start=0, stop=2, nPts=3, mode='byte')
        self.heatmap.setLookupTable(lut)
        
        # Create and add AxisItems
        self.x_axis = RotatedAxisItem(orientation="bottom")
        self.y_axis = pg.AxisItem(orientation="left")

        # Rotate X axis labels for better visibility
        self.x_axis.setStyle(tickFont=QtGui.QFont("Arial", 8), tickTextOffset=30)

        self.plot = self.win.addPlot(axisItems={'bottom': self.x_axis, 'left': self.y_axis})
        self.plot.addItem(self.heatmap)
        
        # Set initial view bounds
        self.plot.setRange(QtCore.QRectF(0, 0, 20, 10))

        # Make the x axis scrollable
        self.plot.setMouseEnabled(x=True, y=False)

        # Add QSlider
        self.h_slider = QSlider(Qt.Horizontal)
        self.h_slider.setMinimum(0)
        self.h_slider.valueChanged.connect(self.hSliderChanged)

        # Add QSlider
        self.v_slider = QSlider(Qt.Vertical)
        self.v_slider.setMinimum(0)
        self.v_slider.valueChanged.connect(self.vSliderChanged)
        self.h_layout.addWidget(self.v_slider)

        self.layout.addLayout(self.h_layout)
        self.layout.addWidget(self.h_slider)

    def setLabels(self, symbol_names, date_labels):
        self.y_labels = {(i + 0.5): symbol for i, symbol in enumerate(symbol_names)}
        self.y_axis.setTicks([self.y_labels.items()])
        
        self.x_axis.setTicks([date_labels.items()])


    def hSliderChanged(self, value):
        x_range = self.plot.viewRange()[0]
        x_width = x_range[1] - x_range[0]  # Calculate the current x-range width
        self.plot.setRange(xRange=(value, value + x_width), padding=0)


    def vSliderChanged(self, value):
        y_range = self.plot.viewRange()[1]
        y_height = y_range[1] - y_range[0]  # Calculate the current y-range height
        self.plot.setRange(yRange=(value, value - y_height), padding=0)


    def updateData(self, heatmap_data, all_indices, symbols):

        self.heatmap.setImage(heatmap_data)
        x_dim, y_dim = heatmap_data.shape
        self.plot.setLimits(xMin=0, xMax=x_dim, yMin=0, yMax=y_dim)
        self.plot.setRange(QtCore.QRectF(0, 0, 20, y_dim))
        self.h_slider.setMaximum(x_dim) # Subtract the visible window size from the maximum
        self.v_slider.setMaximum(y_dim)  # Subtract the visible window size from the maximum

        #date_labels = {i: date.strftime("%Y-%m-%d") for i, date in enumerate(all_indices)}
        date_labels = {i: date.strftime("%Y-%m-%d") for i, date in enumerate(all_indices) if i % 10 == 0}
        self.setLabels(symbols, date_labels)

